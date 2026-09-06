import os
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"


class BinanceEnvironment(str, Enum):
    DEMO = "demo"


class BinanceCredentials(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str = Field(repr=False)
    secret_key: str = Field(repr=False)


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    llm_provider: LLMProvider
    llm_model: str
    llm_allowed_models: tuple[str, ...] = ()
    llm_max_tokens: int = Field(default=4096, gt=0)
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    litellm_debug: bool = False
    binance_environment: BinanceEnvironment = BinanceEnvironment.DEMO
    binance_cli_path: str = "binance-cli"
    binance_api_key: str | None = Field(default=None, repr=False)
    binance_secret_key: str | None = Field(default=None, repr=False)

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

    max_tokens_value = os.getenv("LLM_MAX_TOKENS", "4096").strip()
    try:
        max_tokens = int(max_tokens_value)
    except ValueError as error:
        raise ValueError("LLM_MAX_TOKENS must be a positive integer.") from error
    if max_tokens <= 0:
        raise ValueError("LLM_MAX_TOKENS must be a positive integer.")

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip() or None

    active_key = {
        LLMProvider.OPENAI: ("OPENAI_API_KEY", openai_api_key),
        LLMProvider.GEMINI: ("GEMINI_API_KEY", gemini_api_key),
    }
    key_name, key_value = active_key[provider]

    if key_value is None:
        raise ValueError(f"{key_name} is required when LLM_PROVIDER={provider.value}.")

    default_route = f"{provider.value}/{model}"
    configured_routes = os.getenv(
        "LLM_ALLOWED_MODELS",
        default_route,
    ).split(",")
    allowed_models = tuple(
        dict.fromkeys(
            route.strip()
            for route in configured_routes
            if route.strip()
        )
    )
    if default_route not in allowed_models:
        raise ValueError(
            "The configured default model must be in LLM_ALLOWED_MODELS."
        )

    binance_environment_value = os.getenv("BINANCE_API_ENV", "demo").strip().lower()
    try:
        binance_environment = BinanceEnvironment(binance_environment_value)
    except ValueError as error:
        raise ValueError("BINANCE_API_ENV must be demo for this version.") from error

    binance_cli_path = os.getenv("BINANCE_CLI_PATH", "binance-cli").strip()
    if not binance_cli_path:
        raise ValueError("BINANCE_CLI_PATH must not be empty.")

    return Settings(
        llm_provider=provider,
        llm_model=model,
        llm_allowed_models=allowed_models,
        llm_max_tokens=max_tokens,
        openai_api_key=openai_api_key,
        gemini_api_key=gemini_api_key,
        litellm_debug=os.getenv("LITELLM_DEBUG", "false"),
        binance_environment=binance_environment,
        binance_cli_path=binance_cli_path,
        binance_api_key=os.getenv("BINANCE_API_KEY", "").strip() or None,
        binance_secret_key=os.getenv("BINANCE_SECRET_KEY", "").strip() or None,
    )


def require_binance_credentials(settings: Settings) -> BinanceCredentials:
    """Return configured credentials without ever including their values in errors."""
    missing = []
    if settings.binance_api_key is None:
        missing.append("BINANCE_API_KEY")
    if settings.binance_secret_key is None:
        missing.append("BINANCE_SECRET_KEY")
    if missing:
        raise ValueError(f"Missing Binance credentials: {', '.join(missing)}.")

    return BinanceCredentials(
        api_key=settings.binance_api_key,
        secret_key=settings.binance_secret_key,
    )
