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
            entities: list[dict[str, Any]] = []
            pii_types: list[str] = []

            for item in raw_entities:
                if isinstance(item, dict):
                    entities.append(dict(item))

            redacted = original_text
            spans: list[tuple[int, int, str]] = []
            idx = 0
            while idx < len(entities):
                entity = entities[idx]
                tag = entity.get("entity")
                if not isinstance(tag, str):
                    idx += 1
                    continue

                base_label = entity["entity"].split("-", 1)[-1].upper() if entity["entity"].startswith(("B-", "S-")) else None
                if base_label is not None and base_label not in pii_types:
                    pii_types.append(base_label)

                if not tag.startswith(("B-", "S-")):
                    idx += 1
                    continue

                start = entity.get("start")
                end = entity.get("end")
                if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(original_text)):
                    idx += 1
                    continue

                if tag.startswith("S-"):
                    spans.append((start, end, base_label or "PII"))
                    idx += 1
                    continue

                span_end = end
                j = idx + 1
                while j < len(entities):
                    next_entity = entities[j]
                    next_tag = next_entity.get("entity")
                    if not isinstance(next_tag, str):
                        break
                    next_base = next_tag.split("-", 1)[-1].upper() if "-" in next_tag else next_tag.upper()
                    if next_base != (base_label or ""):
                        break
                    if next_tag.startswith(("I-", "E-")):
                        next_end = next_entity.get("end")
                        if isinstance(next_end, int) and next_end > span_end and next_end <= len(original_text):
                            span_end = next_end
                        if next_tag.startswith("E-"):
                            j += 1
                            break
                        j += 1
                        continue
                    break

                spans.append((start, span_end, base_label or "PII"))
                idx = j

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
