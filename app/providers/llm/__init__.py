from app.core.config import settings
from .ollama import OllamaProvider
from .base import LLMProvider


def get_llm_provider() -> LLMProvider:
    # Only Ollama (mistral) is supported per requirements
    return OllamaProvider()
