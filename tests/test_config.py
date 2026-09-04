import pytest

import app.config as config


def _clear_llm_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: False)
    for variable in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_load_settings_builds_openai_litellm_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    settings = config.load_settings()

    assert settings.llm_provider.value == "openai"
    assert settings.llm_model == "gpt-5.6-luna"
    assert settings.agents_model == "litellm/openai/gpt-5.6-luna"


def test_load_settings_builds_gemini_litellm_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "GEMINI")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = config.load_settings()

    assert settings.llm_provider.value == "gemini"
    assert settings.agents_model == "litellm/gemini/gemini-3.8-flash"


def test_load_settings_rejects_unsupported_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-example")

    with pytest.raises(ValueError, match="openai or gemini"):
        config.load_settings()


def test_load_settings_requires_model(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    with pytest.raises(ValueError, match="LLM_MODEL"):
        config.load_settings()


def test_load_settings_requires_active_provider_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("OPENAI_API_KEY", "inactive-openai-key")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        config.load_settings()
