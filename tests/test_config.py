import pytest

import app.config as config


def _clear_llm_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: False)
    for variable in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_ALLOWED_MODELS",
        "LLM_MAX_TOKENS",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "LITELLM_DEBUG",
        "BINANCE_API_ENV",
        "BINANCE_CLI_PATH",
        "BINANCE_API_KEY",
        "BINANCE_SECRET_KEY",
        "SENTINEL_DEMO_EXECUTION_ENABLED",
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
    assert settings.llm_max_tokens == 4096
    assert settings.litellm_debug is False


def test_load_settings_parses_model_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv(
        "LLM_ALLOWED_MODELS",
        "gemini/gemini-3.5-flash-lite, openai/gpt-5.4-mini",
    )

    assert config.load_settings().llm_allowed_models == (
        "gemini/gemini-3.5-flash-lite",
        "openai/gpt-5.4-mini",
    )


def test_default_model_is_allowed_when_allowlist_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert config.load_settings().llm_allowed_models == (
        "openai/gpt-5.4-mini",
    )


def test_default_model_must_be_in_explicit_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv(
        "LLM_ALLOWED_MODELS",
        "gemini/gemini-3.5-flash-lite",
    )

    with pytest.raises(ValueError, match="default model"):
        config.load_settings()


def test_load_settings_enables_litellm_debug_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("LITELLM_DEBUG", "true")

    settings = config.load_settings()

    assert settings.litellm_debug is True


def test_load_settings_accepts_custom_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("LLM_MAX_TOKENS", "8192")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    assert config.load_settings().llm_max_tokens == 8192


def test_load_settings_rejects_invalid_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("LLM_MAX_TOKENS", "zero")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    with pytest.raises(ValueError, match="LLM_MAX_TOKENS"):
        config.load_settings()


def test_load_settings_rejects_invalid_litellm_debug_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("LITELLM_DEBUG", "sometimes")

    with pytest.raises(ValueError, match="valid boolean"):
        config.load_settings()


def test_load_settings_builds_gemini_litellm_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "GEMINI")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = config.load_settings()

    assert settings.llm_provider.value == "gemini"
    assert settings.agents_model == "litellm/gemini/gemini-3.5-flash-lite"


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
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("OPENAI_API_KEY", "inactive-openai-key")

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        config.load_settings()


def test_binance_settings_default_to_demo_and_standard_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = config.load_settings()

    assert settings.binance_environment is config.BinanceEnvironment.DEMO
    assert settings.binance_cli_path == "binance-cli"
    assert settings.binance_api_key is None
    assert settings.binance_secret_key is None
    assert settings.demo_execution_enabled is False


def test_demo_execution_requires_explicit_valid_boolean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("SENTINEL_DEMO_EXECUTION_ENABLED", "true")

    assert config.load_settings().demo_execution_enabled is True

    monkeypatch.setenv("SENTINEL_DEMO_EXECUTION_ENABLED", "sometimes")
    with pytest.raises(ValueError, match="valid boolean"):
        config.load_settings()


def test_load_settings_accepts_binance_demo_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("BINANCE_API_KEY", "demo-api-key")
    monkeypatch.setenv("BINANCE_SECRET_KEY", "demo-secret-key")

    credentials = config.require_binance_credentials(config.load_settings())

    assert credentials.api_key == "demo-api-key"
    assert credentials.secret_key == "demo-secret-key"


def test_load_settings_rejects_unsupported_binance_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("BINANCE_API_ENV", "prod")

    with pytest.raises(ValueError, match="must be demo"):
        config.load_settings()


def test_missing_binance_credentials_error_contains_no_secret_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("BINANCE_API_KEY", "present-api-key")

    with pytest.raises(ValueError) as error:
        config.require_binance_credentials(config.load_settings())

    message = str(error.value)
    assert "BINANCE_SECRET_KEY" in message
    assert "present-api-key" not in message
