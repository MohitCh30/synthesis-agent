import logging
import threading
from typing import Any


logger = logging.getLogger(__name__)


class PIIFilterService:
    def __init__(self):
        self._lock = threading.Lock()
        self._ready = False
        self._pipeline = None

    def _prepare_model(self) -> None:
        if self._ready:
            return

        with self._lock:
            if self._ready:
                return

            import os
            from pathlib import Path

            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            model_cached = any(
                "openai" in str(p) and "privacy" in str(p)
                for p in cache_dir.rglob("*.safetensors")
            ) if cache_dir.exists() else False
            if model_cached:
                os.environ["HF_HUB_OFFLINE"] = "1"
                logger.info("PII model found in cache, running offline")
            else:
                os.environ["HF_HUB_OFFLINE"] = "0"
                logger.info("PII model not cached, downloading from HuggingFace")

            try:
                from transformers import pipeline

                self._pipeline = pipeline(
                    "token-classification",
                    model="openai/privacy-filter",
                    device="cpu",
                    # No trust_remote_code: model is a standard architecture and
                    # loads fine without executing code from the model repo.
                )
            except Exception as exc:
                logger.error("Failed to load PII model: %s", exc)
                self._pipeline = None
            finally:
                self._ready = True

    @staticmethod
    def _normalize_entity(entity: dict[str, Any]) -> str:
        value = entity.get("entity_group") or entity.get("entity") or entity.get("label")
        if not isinstance(value, str) or not value:
            return "PII"
        return value.replace("B-", "").replace("I-", "").upper()

    def filter_pii(self, text: str) -> dict[str, Any]:
        original_text = text
        if not isinstance(original_text, str):
            original_text = str(original_text)

        try:
            self._prepare_model()
        except Exception as exc:
            logger.error("Failed preparing PII model: %s", exc)

        if self._pipeline is None:
            return {
                "has_pii": False,
                "pii_types": [],
                "redacted": original_text,
                "entities": [],
            }

        try:
            raw_entities = self._pipeline(original_text)

            # Normalize every detection to (prefix, label, start, end).
            # The privacy-filter model can label credential-like content
            # inconsistently (e.g. B-account_number followed by I-secret), and
            # continuation tokens (I-/E-) or bare labels carrying "secret" must
            # not be dropped — a detected SECRET has to count as a finding.
            normalized: list[tuple[str, str, int, int]] = []
            for item in raw_entities:
                if not isinstance(item, dict):
                    continue
                tag = item.get("entity")
                if not isinstance(tag, str) or not tag:
                    continue
                if tag[:2] in ("B-", "I-", "E-", "S-") and len(tag) > 2:
                    prefix, _, label = tag.partition("-")
                else:
                    prefix, label = "S", tag  # bare label: treat as atomic
                label = label.upper()
                start = item.get("start")
                end = item.get("end")
                if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(original_text)):
                    continue
                normalized.append((prefix, label, start, end))

            pii_types: list[str] = []
            for _, label, _, _ in normalized:
                if label not in pii_types:
                    pii_types.append(label)

            # Merge adjacent entities into spans. Continuation prefixes (I-/E-)
            # extend the open span regardless of the label on the token, so a
            # detection whose label flips mid-span is redacted in full.
            spans: list[tuple[int, int, str]] = []
            current: list | None = None  # [start, end, label]
            for prefix, label, start, end in normalized:
                extends = (
                    current is not None
                    and prefix in ("I", "E")
                    and start <= current[1]
                )
                if extends:
                    current[1] = max(current[1], end)
                else:
                    if current is not None:
                        spans.append((current[0], current[1], current[2]))
                    current = [start, end, label]
                if prefix == "E" and current is not None:
                    spans.append((current[0], current[1], current[2]))
                    current = None
            if current is not None:
                spans.append((current[0], current[1], current[2]))

            redacted = original_text
            for start, end, entity_type in sorted(spans, key=lambda x: (x[0], x[1]), reverse=True):
                replacement = f"[REDACTED_{entity_type}]"
                redacted = redacted[:start] + replacement + redacted[end:]

            entities_serializable = [
                {k: float(v) if hasattr(v, 'item') else v
                 for k, v in entity.items()}
                for entity in raw_entities
            ]

            return {
                "has_pii": len(spans) > 0,
                "pii_types": pii_types,
                "redacted": redacted,
                "entities": entities_serializable,
            }
        except Exception as exc:
            logger.error("PII filtering failed: %s", exc)
            return {
                "has_pii": False,
                "pii_types": [],
                "redacted": original_text,
                "entities": [],
            }


pii_filter_service = PIIFilterService()
