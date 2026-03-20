import httpx
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"


class LLMService:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=120.0)

    def is_connected(self) -> bool:
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        model: str = "mistral",
        system_prompt: Optional[str] = None
    ) -> dict:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 100,
                "temperature": 0.7
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = self.client.post(
            f"{self.base_url}/api/generate",
            json=payload
        )

        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

        result = response.json()
        return {
            "response": result.get("response", ""),
            "model": model,
            "done": result.get("done", True)
        }

    def close(self):
        self.client.close()


llm_service = LLMService()
