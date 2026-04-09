import hashlib
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


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

    def _prepare_model(self) -> None:
        if self._ready:
            return

        with self._lock:
            if self._ready:
                return

            logger.info("Loading JailbreakBench/JBB-Behaviors dataset from HuggingFace...")

            # Local imports keep startup lightweight and avoid impacting existing endpoints.
            from datasets import load_dataset
            from sentence_transformers import SentenceTransformer
            from sklearn.linear_model import LogisticRegression

            dataset = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors")
            if "harmful" not in dataset or "benign" not in dataset:
                raise RuntimeError("Expected harmful and benign splits in JailbreakBench/JBB-Behaviors")

            harmful_rows = dataset["harmful"]
            benign_rows = dataset["benign"]

            texts: list[str] = []
            labels: list[int] = []

            for row in harmful_rows:
                text = self._extract_text(row)
                if text:
                    texts.append(text)
                    labels.append(1)  # ADVERSARIAL

            for row in benign_rows:
                text = self._extract_text(row)
                if text:
                    texts.append(text)
                    labels.append(0)  # SAFE

            if not texts:
                raise RuntimeError("No training texts found in JailbreakBench/JBB-Behaviors")

            logger.info("Loading embedding model sentence-transformers/all-MiniLM-L6-v2...")
            self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

            logger.info("Embedding training dataset...")
            X = self._embedder.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

            logger.info("Training logistic regression classifier...")
            self._classifier = LogisticRegression(max_iter=2000, solver="liblinear")
            self._classifier.fit(X, labels)

            self._ready = True
            logger.info("Jailbreak prompt classifier is ready")

    def classify(self, prompt: str) -> dict[str, Any]:
        original_prompt = prompt
        clean_prompt = original_prompt.strip()
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

        adversarial_probability = class_to_prob.get(1, 0.0)

        if adversarial_probability >= 0.5:
            verdict = "ADVERSARIAL"
            confidence = adversarial_probability
        else:
            verdict = "SAFE"
            confidence = 1.0 - adversarial_probability

        prompt_hash = hashlib.sha256(original_prompt.encode("utf-8")).hexdigest()

        return {
            "verdict": verdict,
            "confidence": float(confidence),
            "prompt_hash": prompt_hash,
        }


classifier_service = JailbreakClassifierService()
