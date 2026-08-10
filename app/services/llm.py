import os
import logging
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.1-8b-instant"


def _allowed_models() -> set[str]:
    """Chat models clients may select via AgentRequest.model.

    Only plain chat models without built-in server-side tooling are allowed.
    Agentic models (e.g. groq/compound*) can execute server-side `visit`/search
    tool calls against client-supplied URLs (provider-side SSRF, billed to our
    key), so they are excluded. Override via GROQ_ALLOWED_MODELS (comma-sep).
    """
    raw = os.getenv("GROQ_ALLOWED_MODELS")
    if raw:
        return {m.strip() for m in raw.split(",") if m.strip()}
    return {DEFAULT_MODEL, "llama-3.3-70b-versatile"}


def validate_model(model: str) -> str:
    if model not in _allowed_models():
        raise ValueError(
            f"Model '{model}' is not allowed. Allowed models: {sorted(_allowed_models())}"
        )
    return model


class LLMService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.client = None

    def get_client(self):
        if self.client is None:
            api_key = os.getenv("GROQ_API_KEY") or self.api_key
            if not api_key:
                logger.error("GROQ_API_KEY missing at runtime")
                raise Exception("GROQ_API_KEY missing at runtime")
            try:
                self.client = Groq(api_key=api_key)
                logger.info(f"Groq client initialized with model: {DEFAULT_MODEL}")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                raise
        return self.client

    def is_connected(self) -> bool:
        logger.info(f"GROQ_API_KEY present: {'YES' if os.getenv('GROQ_API_KEY') else 'NO'}")
        
        try:
            client = self.get_client()
            client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"Groq connection check failed: {e}")
            return False

    def generate(
        self,
        prompt: str,
        model: str = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> dict:
        model = validate_model(model) if model else DEFAULT_MODEL
        client = self.get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            response_text = completion.choices[0].message.content or ""

            return {
                "response": response_text,
                "model": model,
                "done": True,
                "usage": {
                    "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
                    "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
                    "total_tokens": completion.usage.total_tokens if completion.usage else 0
                }
            }

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise Exception(f"Groq API error: {str(e)}")


llm_service = LLMService()
