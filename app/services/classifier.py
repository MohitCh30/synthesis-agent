import hashlib
import logging
import random
import re
import threading
from pathlib import Path
from typing import Any

import joblib
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)


MODEL_PATH = Path(__file__).parent / "classifier_model.joblib"
BASE64_PATTERN = re.compile(r"(?:^|[^A-Za-z0-9+/=])([A-Za-z0-9+/]{24,}={0,2})(?=$|[^A-Za-z0-9+/=])")
PERSONA_PATTERNS = [
    re.compile(r"\bdan\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"developer\s*mode", re.IGNORECASE),
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+are", re.IGNORECASE),
    re.compile(r"act\s+as\s+if", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"simulation\s+mode", re.IGNORECASE),
    re.compile(r"hypothetically", re.IGNORECASE),
    re.compile(r"without\s+restrictions", re.IGNORECASE),
    re.compile(r"no\s+limitations", re.IGNORECASE),
    re.compile(r"override\s+safety", re.IGNORECASE),
    re.compile(r"bypass\s+filters", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"as\s+a\s+character\s+who", re.IGNORECASE),
    re.compile(r"for\s+educational\s+purposes", re.IGNORECASE),
    re.compile(r"in\s+this\s+fictional\s+world", re.IGNORECASE),
    re.compile(r"ignore\s+all\s+previous", re.IGNORECASE),
]


class JailbreakClassifierService:
    """
    Lazy-loading prompt classifier:
    - Loads JailbreakBench/JBB-Behaviors from HuggingFace
    - Embeds text with sentence-transformers/all-MiniLM-L6-v2
    - Trains LogisticRegression classifier
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._ready = False
        self._embedder = None
        self._classifier = None

    def _extract_text(self, row: dict[str, Any]) -> str:
        for key in ("Behavior", "Goal", "prompt", "goal", "Target", "target_response"):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _try_decode_base64(prompt: str) -> str:
        import base64, re
        pattern = re.compile(r'^[A-Za-z0-9+/]{24,}={0,2}$')
        stripped = prompt.strip()
        if pattern.match(stripped):
            try:
                return base64.b64decode(stripped).decode('utf-8')
            except Exception:
                return prompt
        return prompt

    @staticmethod
    def _base64_signal(prompt: str) -> float:
        matches = BASE64_PATTERN.findall(prompt)
        if not matches:
            return 0.0
        return 1.0

    @staticmethod
    def _persona_signal(prompt: str) -> float:
        hits = sum(1 for pattern in PERSONA_PATTERNS if pattern.search(prompt))
        return 1.0 if hits >= 1 else 0.0

    @staticmethod
    def _length_signal(prompt: str) -> float:
        return 1.0 if len(prompt) > 1500 else 0.0

    def _prepare_model(self) -> None:
        if self._ready:
            return

        with self._lock:
            if self._ready:
                return

            logger.info("Loading adversarial and benign datasets from HuggingFace...")

            # Local imports keep startup lightweight and avoid impacting existing endpoints.
            from datasets import load_dataset
            from sentence_transformers import SentenceTransformer

            if MODEL_PATH.exists():
                loaded = joblib.load(MODEL_PATH)
                self._classifier = loaded["model"]
                self._embedder = SentenceTransformer("MohitML10/jailbreak-detector-finetuned")
                self._ready = True
                logger.info("Loaded classifier model from disk")
                return

            def _iter_rows(ds_obj: Any) -> list[dict[str, Any]]:
                if isinstance(ds_obj, dict):
                    rows: list[dict[str, Any]] = []
                    for split_name in ds_obj:
                        rows.extend(list(ds_obj[split_name]))
                    return rows
                return list(ds_obj)

            adversarial_texts: list[str] = []

            jb_ds = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors")
            jb_rows: list[dict[str, Any]] = []
            if isinstance(jb_ds, dict) and "harmful" in jb_ds:
                jb_rows = list(jb_ds["harmful"])
            else:
                jb_rows = _iter_rows(jb_ds)
            for row in jb_rows:
                goal = row.get("Goal")
                behavior = row.get("Behavior")
                text_value = goal if isinstance(goal, str) and goal.strip() else behavior
                if isinstance(text_value, str):
                    text = text_value.strip()
                    if text:
                        adversarial_texts.append(text)

            jackhhao_ds = load_dataset("jackhhao/jailbreak-classification")
            for row in _iter_rows(jackhhao_ds):
                if str(row.get("type", "")).strip().lower() != "jailbreak":
                    continue
                prompt = row.get("prompt")
                if isinstance(prompt, str):
                    text = prompt.strip()
                    if text:
                        adversarial_texts.append(text)

            deepset_ds = load_dataset("deepset/prompt-injections")
            for row in _iter_rows(deepset_ds):
                if row.get("label") != 1:
                    continue
                text_value = row.get("text")
                if isinstance(text_value, str):
                    text = text_value.strip()
                    if text:
                        adversarial_texts.append(text)

            neuralchemy_ds = load_dataset("neuralchemy/Prompt-injection-dataset", "core")
            for row in _iter_rows(neuralchemy_ds):
                if row.get("label") != 1:
                    continue
                text_value = row.get("text")
                if isinstance(text_value, str):
                    text = text_value.strip()
                    if text:
                        adversarial_texts.append(text)

            simsonsun_ds = load_dataset("Simsonsun/JailbreakPrompts")
            if isinstance(simsonsun_ds, dict):
                for split_name in ("Dataset_1", "Dataset_2"):
                    if split_name not in simsonsun_ds:
                        continue
                    for row in simsonsun_ds[split_name]:
                        prompt = row.get("Prompt")
                        if isinstance(prompt, str):
                            text = prompt.strip()
                            if text:
                                adversarial_texts.append(text)

            trustair_ds = load_dataset("TrustAIRLab/in-the-wild-jailbreak-prompts", "jailbreak_2023_12_25")
            for row in _iter_rows(trustair_ds):
                if row.get("jailbreak") is not True:
                    continue
                prompt = row.get("prompt")
                if isinstance(prompt, str):
                    text = prompt.strip()
                    if text:
                        adversarial_texts.append(text)

            adversarial_texts = list(dict.fromkeys(adversarial_texts))

            benign_texts: list[str] = []

            oasst_ds = load_dataset("OpenAssistant/oasst1")
            for row in _iter_rows(oasst_ds):
                if str(row.get("role", "")).strip().lower() != "prompter":
                    continue
                text_value = row.get("text")
                if isinstance(text_value, str):
                    text = text_value.strip()
                    if text:
                        benign_texts.append(text)

            alpaca_ds = load_dataset("yahma/alpaca-cleaned")
            for row in _iter_rows(alpaca_ds):
                instruction = row.get("instruction")
                if isinstance(instruction, str):
                    text = instruction.strip()
                    if text:
                        benign_texts.append(text)

            benign_texts = list(dict.fromkeys(benign_texts))
            benign_count = min(45000, len(benign_texts))
            benign_sample = random.Random(42).sample(benign_texts, benign_count)

            if not adversarial_texts:
                raise RuntimeError("No adversarial texts found in configured datasets")
            if not benign_sample:
                raise RuntimeError("No benign texts found in configured datasets")

            texts = adversarial_texts + benign_sample
            labels = [1] * len(adversarial_texts) + [0] * len(benign_sample)

            logger.info("Loading embedding model sentence-transformers/all-MiniLM-L6-v2...")
            self._embedder = SentenceTransformer("MohitML10/jailbreak-detector-finetuned")

            logger.info("Embedding training dataset...")
            X = self._embedder.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                labels,
                test_size=0.2,
                random_state=42,
                stratify=labels,
            )

            logger.info("Training XGBoost classifier...")
            self._classifier = XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.1,
                eval_metric="logloss",
                random_state=42,
            )
            self._classifier.fit(X_train, y_train)

            y_pred = self._classifier.predict(X_test)
            f1 = f1_score(y_test, y_pred)
            cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()
            tpr = tp / (tp + fn) if (tp + fn) else 0.0
            fpr = fp / (fp + tn) if (fp + tn) else 0.0

            logger.info("F1 score: %.6f", f1)
            logger.info("True Positive Rate (TPR): %.6f", tpr)
            logger.info("False Positive Rate (FPR): %.6f", fpr)

            joblib.dump({"model": self._classifier}, MODEL_PATH)

            self._ready = True
            logger.info("Jailbreak prompt classifier is ready")

    def classify(self, prompt: str) -> dict[str, Any]:
        original_prompt = prompt
        clean_prompt = original_prompt.strip()
        clean_prompt = self._try_decode_base64(clean_prompt)
        if not clean_prompt:
            raise ValueError("Prompt cannot be empty")

        self._prepare_model()

        vector = self._embedder.encode(
            [clean_prompt],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        probabilities = self._classifier.predict_proba(vector)[0]
        class_to_prob = {
            int(cls): float(prob)
            for cls, prob in zip(self._classifier.classes_, probabilities)
        }

        embedding_signal = class_to_prob.get(1, 0.0)
        base64_signal = self._base64_signal(original_prompt)
        persona_signal = self._persona_signal(original_prompt)
        length_signal = self._length_signal(original_prompt)

        ensemble_score = (
            0.4 * embedding_signal
            + 0.3 * persona_signal
            + 0.2 * base64_signal
            + 0.1 * length_signal
        )
        ensemble_score = max(0.0, min(1.0, ensemble_score))
        if ensemble_score >= 0.29:
            verdict = "ADVERSARIAL"
            confidence = ensemble_score
        else:
            verdict = "SAFE"
            confidence = 1.0 - ensemble_score

        prompt_hash = hashlib.sha256(original_prompt.encode("utf-8")).hexdigest()

        return {
            "verdict": verdict,
            "confidence": float(confidence),
            "prompt_hash": prompt_hash,
        }


classifier_service = JailbreakClassifierService()
