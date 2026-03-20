import os
import logging
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL = "mistral-7b-instruct-v0.1"


class LLMService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def is_connected(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.chat.completions.create(
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
        if not self.client:
            raise Exception("GROQ_API_KEY not configured")

        model = model or DEFAULT_MODEL

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            completion = self.client.chat.completions.create(
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
