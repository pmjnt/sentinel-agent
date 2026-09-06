from dataclasses import dataclass

from app.config import LLMProvider, Settings


@dataclass(frozen=True)
class ModelRoute:
    provider: LLMProvider
    model: str

    @property
    def key(self) -> str:
        return f"{self.provider.value}/{self.model}"

    def apply(self, settings: Settings) -> Settings:
        """Create route-specific settings without changing secrets."""
        return settings.model_copy(
            update={
                "llm_provider": self.provider,
                "llm_model": self.model,
            }
        )


class ModelCatalog:
    """Expose and validate only explicitly allowed, configured LLM routes."""

    def __init__(
        self,
        routes: tuple[ModelRoute, ...],
        default: ModelRoute,
    ) -> None:
        self.routes = routes
        self.default = default
        self._by_key = {route.key: route for route in routes}

    @classmethod
    def from_settings(cls, settings: Settings) -> "ModelCatalog":
        configured = settings.llm_allowed_models or (
            f"{settings.llm_provider.value}/{settings.llm_model}",
        )
        routes: list[ModelRoute] = []
        for value in configured:
            provider_text, separator, model = value.partition("/")
            if not separator or not model.strip():
                raise ValueError(f"Invalid allowed model route: {value}.")
            try:
                provider = LLMProvider(provider_text.strip().lower())
            except ValueError as error:
                raise ValueError(
                    f"Invalid allowed model route: {value}."
                ) from error
            if cls._provider_key(settings, provider):
                routes.append(ModelRoute(provider, model.strip()))

        default_key = f"{settings.llm_provider.value}/{settings.llm_model}"
        by_key = {route.key: route for route in routes}
        if default_key not in by_key:
            raise ValueError("The default model route is not enabled.")
        return cls(tuple(by_key.values()), by_key[default_key])

    def resolve(self, provider: str, model: str) -> ModelRoute:
        key = f"{provider.strip().lower()}/{model.strip()}"
        try:
            return self._by_key[key]
        except KeyError as error:
            raise ValueError(
                "The selected model route is not enabled."
            ) from error

    @staticmethod
    def _provider_key(
        settings: Settings,
        provider: LLMProvider,
    ) -> str | None:
        return {
            LLMProvider.OPENAI: settings.openai_api_key,
            LLMProvider.GEMINI: settings.gemini_api_key,
        }[provider]
