import pytest

from app.config import LLMProvider, Settings
from app.model_catalog import ModelCatalog


def _settings() -> Settings:
    return Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        llm_allowed_models=(
            "gemini/gemini-3.5-flash-lite",
            "openai/gpt-5.4-mini",
        ),
        gemini_api_key="gemini-key",
    )


def test_catalog_exposes_only_routes_whose_provider_key_exists() -> None:
    catalog = ModelCatalog.from_settings(_settings())

    assert [route.key for route in catalog.routes] == [
        "gemini/gemini-3.5-flash-lite"
    ]


def test_catalog_resolves_enabled_route_and_builds_agent_settings() -> None:
    catalog = ModelCatalog.from_settings(_settings())

    route = catalog.resolve("gemini", "gemini-3.5-flash-lite")
    routed_settings = route.apply(_settings())

    assert routed_settings.agents_model == (
        "litellm/gemini/gemini-3.5-flash-lite"
    )


def test_catalog_rejects_unlisted_route() -> None:
    with pytest.raises(ValueError, match="not enabled"):
        ModelCatalog.from_settings(_settings()).resolve(
            "openai",
            "gpt-5.4-mini",
        )


def test_catalog_uses_default_route_for_programmatic_settings() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="openai-key",
    )

    catalog = ModelCatalog.from_settings(settings)

    assert catalog.routes == (catalog.default,)
    assert catalog.default.key == "openai/gpt-5.4-mini"


def test_catalog_rejects_invalid_route_format() -> None:
    settings = _settings().model_copy(
        update={"llm_allowed_models": ("invalid-route",)}
    )

    with pytest.raises(ValueError, match="Invalid allowed model route"):
        ModelCatalog.from_settings(settings)
