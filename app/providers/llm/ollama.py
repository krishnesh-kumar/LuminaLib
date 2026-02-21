import httpx
import json
from typing import Any
from app.core.config import settings
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self.client = httpx.Client(base_url=settings.OLLAMA_BASE_URL, timeout=120.0)
        self.model = settings.OLLAMA_MODEL

    def generate(self, prompt: str, params: dict[str, Any] | None = None) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if params:
            payload.update(params)
        resp = self.client.post("/api/generate", json=payload)
        resp.raise_for_status()
        try:
            data = resp.json()
            return data.get("response", "")
        except json.JSONDecodeError:
            # Fallback for newline-delimited responses
            lines = [line for line in resp.text.splitlines() if line.strip()]
            if lines:
                last = json.loads(lines[-1])
                return last.get("response", "")
            raise
