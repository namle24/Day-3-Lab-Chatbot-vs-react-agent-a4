import os
from typing import Optional

from src.core.llm_provider import LLMProvider


def create_llm_provider() -> Optional[LLMProvider]:
    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    model = os.getenv("DEFAULT_MODEL", "gpt-4o")

    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key or key.startswith("your_"):
            return None
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(model_name=model, api_key=key)

    if provider in ("google", "gemini"):
        key = os.getenv("GEMINI_API_KEY")
        if not key or key.startswith("your_"):
            return None
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(model_name=model, api_key=key)

    if provider == "local":
        path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        from src.core.local_provider import LocalProvider

        return LocalProvider(model_path=path)

    return None
