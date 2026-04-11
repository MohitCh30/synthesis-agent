import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import base64
import logging
import random
import re
import threading
from pathlib import Path
from typing import Any

import joblib
from datasets import Dataset, DatasetDict, IterableDataset, IterableDatasetDict, load_dataset
from sentence_transformers import SentenceTransformer
from sklearn.metrics import f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

import os
os.environ["HF_HUB_OFFLINE"] = "1"


MODEL_PATH = Path(__file__).parent / "classifier_model.joblib"
FINETUNED_MODEL = "/home/mohitchaudhary/synthesis-agent/models/finetuned-jailbreak-detector/final"


logger = logging.getLogger(__name__)


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
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trained = False
        self._embedder: SentenceTransformer | None = None
        self._model: XGBClassifier | None = None

    @staticmethod
    def _extract_text(row: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = row.get(key)
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _iter_rows(ds_obj: Any) -> list[dict[str, Any]]:
        if isinstance(ds_obj, (DatasetDict, IterableDatasetDict)):
            rows: list[dict[str, Any]] = []
            for split in ds_obj.keys():
                rows.extend(list(ds_obj[split]))
            return rows
        if isinstance(ds_obj, (Dataset, IterableDataset)):
            return list(ds_obj)
        return []

    def _load_adversarial_examples(self) -> list[str]:
        logger.info("Loading adversarial dataset JailbreakBench/JBB-Behaviors")
        try:
            ds = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors")
        except Exception:
            ds = load_dataset("JailbreakBench/JBB-Behaviors")

        rows: list[dict[str, Any]] = []
        if isinstance(ds, (DatasetDict, IterableDatasetDict)) and "harmful" in ds:
            rows = list(ds["harmful"])
        else:
            rows = self._iter_rows(ds)

        texts: list[str] = []
        for row in rows:
            text = self._extract_text(
                row,
                (
                    "Behavior",
                    "Goal",
                    "goal",
                    "prompt",
                    "Prompt",
                    "query",
                    "instruction",
                    "text",
                ),
            )
            if text:
                texts.append(text)

        logger.info("Loading adversarial dataset jackhhao/jailbreak-classification")
        jb_ds = load_dataset("jackhhao/jailbreak-classification")
        jb_rows = self._iter_rows(jb_ds)

        for row in jb_rows:
            prompt_value = row.get("prompt")
            if not isinstance(prompt_value, str):
                continue

            prompt_text = prompt_value.strip()
            if not prompt_text:
                continue

            is_adversarial = (
                str(row.get("type", "")).strip().lower() == "jailbreak"
            )

            if is_adversarial:
                texts.append(prompt_text)

        logger.info("Loading adversarial dataset deepset/prompt-injections")
        deepset_ds = load_dataset("deepset/prompt-injections")
        deepset_rows = self._iter_rows(deepset_ds)

        for row in deepset_rows:
            text_value = row.get("text")
            if not isinstance(text_value, str):
                continue

            prompt_text = text_value.strip()
            if not prompt_text:
                continue

            if row.get("label") == 1:
                texts.append(prompt_text)

        logger.info("Loading adversarial dataset neuralchemy/Prompt-injection-dataset (core)")
        neuralchemy_ds = load_dataset("neuralchemy/Prompt-injection-dataset", "core")
        neuralchemy_rows = self._iter_rows(neuralchemy_ds)

        for row in neuralchemy_rows:
            text_value = row.get("text")
            if not isinstance(text_value, str):
                continue

            prompt_text = text_value.strip()
            if not prompt_text:
                continue

            if row.get("label") == 1:
                texts.append(prompt_text)

        logger.info("Loading adversarial dataset Simsonsun/JailbreakPrompts")
        simsonsun_ds = load_dataset("Simsonsun/JailbreakPrompts")

        for split_name in ("Dataset_1", "Dataset_2"):
            if isinstance(simsonsun_ds, (DatasetDict, IterableDatasetDict)) and split_name in simsonsun_ds:
                for row in simsonsun_ds[split_name]:
                    prompt_value = row.get("Prompt")
                    if isinstance(prompt_value, str):
                        prompt_text = prompt_value.strip()
                        if prompt_text:
                            texts.append(prompt_text)

        logger.info("Loading adversarial dataset TrustAIRLab/in-the-wild-jailbreak-prompts (jailbreak_2023_12_25)")
        trustair_ds = load_dataset("TrustAIRLab/in-the-wild-jailbreak-prompts", "jailbreak_2023_12_25")
        trustair_rows = self._iter_rows(trustair_ds)

        for row in trustair_rows:
            prompt_value = row.get("prompt")
            if not isinstance(prompt_value, str):
                continue

            prompt_text = prompt_value.strip()
            if not prompt_text:
                continue

            if row.get("jailbreak") == True:
                texts.append(prompt_text)

        return list(dict.fromkeys(texts))

    def _load_benign_examples(self) -> list[str]:
        logger.info("Loading benign dataset OpenAssistant/oasst1")
        ds = load_dataset("OpenAssistant/oasst1")

        rows = self._iter_rows(ds)
        texts: list[str] = []
        for row in rows:
            lang = row.get("lang")
            if isinstance(lang, str) and lang and not lang.lower().startswith("en"):
                continue

            role = row.get("role")
            if isinstance(role, str) and role.lower() not in {"prompter", "user", "human"}:
                continue

            text = self._extract_text(
                row,
                (
                    "text",
                    "prompt",
                    "instruction",
                    "message",
                    "content",
                ),
            )
            if text:
                texts.append(text)

        logger.info("Loading benign dataset yahma/alpaca-cleaned")
        alpaca_ds = load_dataset("yahma/alpaca-cleaned")
        alpaca_rows = self._iter_rows(alpaca_ds)
        for row in alpaca_rows:
            instruction = row.get("instruction", "")
            input_text = row.get("input", "")
            if instruction and isinstance(instruction, str):
                combined = instruction.strip()
                if input_text and isinstance(input_text, str):
                    combined = combined + " " + input_text.strip()
                if combined:
                    texts.append(combined)

        return list(dict.fromkeys(texts))

    @staticmethod
    def _sample_to_count(items: list[str], count: int, seed: int) -> list[str]:
        if len(items) <= count:
            return items
        rng = random.Random(seed)
        return rng.sample(items, count)

    def _prepare_model(self) -> None:
        if MODEL_PATH.exists():
            loaded = joblib.load(MODEL_PATH)
            self._model = loaded["model"]
            self._embedder = SentenceTransformer(FINETUNED_MODEL)
            self._trained = True
            logger.info("Loaded pre-trained classifier from disk — skipping retraining")
            return

        if self._trained:
            return

        with self._lock:
            if self._trained:
                return

            adversarial = self._load_adversarial_examples()
            benign_pool = self._load_benign_examples()

            if not adversarial:
                raise RuntimeError("No adversarial examples loaded from JailbreakBench/JBB-Behaviors")
            if not benign_pool:
                raise RuntimeError("No benign examples loaded from OpenAssistant/oasst1")

            adversarial_sample = adversarial  # use all adversarial examples
            texts = benign_pool
            benign_sample = self._sample_to_count(benign_pool, min(45000, len(texts)), seed=42)
            target_count = len(adversarial_sample)

            texts = adversarial_sample + benign_sample
            labels = [1] * len(adversarial_sample) + [0] * len(benign_sample)

            logger.info(
                "Training jailbreak classifier with %d adversarial and %d benign examples",
                len(adversarial_sample),
                len(benign_sample),
            )

            self._embedder = SentenceTransformer(FINETUNED_MODEL)
            X = self._embedder.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            y = labels

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            self._model = XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.1,
                eval_metric="logloss",
                random_state=42
            )
            self._model.fit(X_train, y_train)

            y_pred = self._model.predict(X_test)
            f1 = f1_score(y_test, y_pred)
            cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()

            tpr = tp / (tp + fn) if (tp + fn) else 0.0
            fpr = fp / (fp + tn) if (fp + tn) else 0.0

            logger.info("F1 score: %.6f", f1)
            logger.info("Confusion matrix: %s", cm.tolist())
            logger.info("True Positive Rate (TPR): %.6f", tpr)
            logger.info("False Positive Rate (FPR): %.6f", fpr)

            joblib.dump({"model": self._model}, MODEL_PATH)
            logger.info("Model saved to %s", MODEL_PATH)
            self._trained = True

    @staticmethod
    def _base64_signal(prompt: str) -> float:
        matches = BASE64_PATTERN.findall(prompt)
        if not matches:
            return 0.0

        valid_count = 0
        for token in matches:
            cleaned = token.strip()
            if len(cleaned) < 24:
                continue
            if len(cleaned) % 4 != 0:
                continue
            if re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", cleaned):
                valid_count += 1

        return 1.0 if valid_count > 0 else 0.0

    @staticmethod
    def _persona_signal(prompt: str) -> float:
        hits = sum(1 for pattern in PERSONA_PATTERNS if pattern.search(prompt))
        if hits <= 0:
            return 0.0
        return 1.0 if hits >= 1 else 0.0

    @staticmethod
    def _length_signal(prompt: str) -> float:
        return 1.0 if len(prompt) > 1500 else 0.0

    def _embedding_signal(self, prompt: str) -> float:
        if self._embedder is None or self._model is None:
            raise RuntimeError("Classifier model is not initialized")

        vector = self._embedder.encode(
            [prompt],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        probability = float(self._model.predict_proba(vector)[0][1])
        return max(0.0, min(1.0, probability))

    def classify(self, prompt: str) -> dict[str, Any]:
        prompt_clean = prompt.strip()
        if not prompt_clean:
            raise ValueError("Prompt cannot be empty")

        def _try_decode_base64(prompt: str) -> str:
            import re
            pattern = re.compile(r'^[A-Za-z0-9+/]{24,}={0,2}$')
            stripped = prompt.strip()
            if pattern.match(stripped):
                try:
                    decoded = base64.b64decode(stripped).decode('utf-8')
                    return decoded
                except Exception:
                    return prompt
            return prompt

        prompt_clean = _try_decode_base64(prompt_clean)

        self._prepare_model()

        embedding_signal = self._embedding_signal(prompt_clean)
        base64_signal = self._base64_signal(prompt)
        persona_signal = self._persona_signal(prompt)
        length_signal = self._length_signal(prompt)

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

        return {
            "verdict": verdict,
            "confidence": float(confidence),
            "signals": {
                "embedding": float(embedding_signal),
                "base64": float(base64_signal),
                "persona": float(persona_signal),
                "length": float(length_signal),
            },
        }


classifier_service = JailbreakClassifierService()
