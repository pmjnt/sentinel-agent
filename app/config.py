import os
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    llm_provider: LLMProvider
    llm_model: str
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    @property
    def agents_model(self) -> str:
        """Return the model ID understood by the Agents SDK LiteLLM provider."""
        return f"litellm/{self.llm_provider.value}/{self.llm_model}"


def load_settings() -> Settings:
    """Load local environment variables and validate required configuration."""
    load_dotenv()

    provider_value = os.getenv("LLM_PROVIDER", "").strip().lower()
    try:
        provider = LLMProvider(provider_value)
    except ValueError as error:
        raise ValueError("LLM_PROVIDER must be openai or gemini.") from error

    model = os.getenv("LLM_MODEL", "").strip()
    if not model:
        raise ValueError("LLM_MODEL is missing. Add the provider's model ID to .env.")

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip() or None

    active_key = {
        LLMProvider.OPENAI: ("OPENAI_API_KEY", openai_api_key),
        LLMProvider.GEMINI: ("GEMINI_API_KEY", gemini_api_key),
    }
    key_name, key_value = active_key[provider]

    if key_value is None:
        raise ValueError(f"{key_name} is required when LLM_PROVIDER={provider.value}.")

    return Settings(
        llm_provider=provider,
        llm_model=model,
        openai_api_key=openai_api_key,
        gemini_api_key=gemini_api_key,
    )
