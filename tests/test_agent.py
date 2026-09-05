from app.agent.sentinel import create_sentinel_agent
from app.config import LLMProvider, Settings
from app.models.market import MarketDataResult
from app.models.portfolio import Portfolio
from app.application import SentinelApplication
from main import (
    configure_litellm_debug,
    create_application,
    format_debug_error,
    read_console_input,
)


class UnusedGateway:
    async def get_portfolio(self) -> Portfolio:
        raise AssertionError("Agent construction must not read portfolio data.")

    async def get_market_data(self, symbol: str) -> MarketDataResult:
        raise AssertionError("Agent construction must not read market data.")


def test_create_sentinel_agent_uses_configured_litellm_model() -> None:
    settings = Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        gemini_api_key="test-gemini-key",
    )

    agent = create_sentinel_agent(settings, UnusedGateway())

    assert agent.model == "litellm/gemini/gemini-3.5-flash-lite"
    assert [tool.name for tool in agent.tools] == [
        "get_portfolio",
        "get_market_data",
    ]
    assert agent.model_settings.max_tokens == 4096
    assert agent.model_settings.reasoning is None
    assert "Binance Demo" in agent.instructions
    assert "real portfolio" in agent.instructions
    assert "Never execute trades" in agent.instructions


def test_create_application_wires_policy_analysis_without_external_calls() -> None:
    settings = Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        gemini_api_key="test-gemini-key",
    )

    application = create_application(settings, UnusedGateway())

    assert isinstance(application, SentinelApplication)


def test_litellm_debug_stays_off_by_default(capsys) -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="test-openai-key",
    )
    calls = 0

    def fake_enable_debug() -> None:
        nonlocal calls
        calls += 1

    configure_litellm_debug(settings, fake_enable_debug)

    assert calls == 0
    assert capsys.readouterr().out == ""


def test_litellm_debug_opt_in_enables_logging_and_warns(capsys) -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="test-openai-key",
        litellm_debug=True,
    )
    calls = 0

    def fake_enable_debug() -> None:
        nonlocal calls
        calls += 1

    configure_litellm_debug(settings, fake_enable_debug)

    warning = capsys.readouterr().out
    assert calls == 1
    assert "request body" in warning
    assert "không chia sẻ log" in warning


def test_console_prompt_is_printed_once_outside_input(capsys) -> None:
    calls = 0

    def fake_reader() -> str:
        nonlocal calls
        calls += 1
        return "  xin chào  "

    result = read_console_input(fake_reader)

    assert result == "xin chào"
    assert calls == 1
    assert capsys.readouterr().out == "Sentinel > "


def test_debug_error_redacts_all_configured_credentials() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="openai-secret",
        gemini_api_key="gemini-secret",
        binance_api_key="binance-key",
        binance_secret_key="binance-secret",
        litellm_debug=True,
    )
    error = RuntimeError(
        "failed with openai-secret gemini-secret binance-key binance-secret"
    )

    diagnostic = format_debug_error(error, settings)

    assert diagnostic == (
        "RuntimeError: failed with [REDACTED] [REDACTED] "
        "[REDACTED] [REDACTED]"
    )


def test_debug_error_is_hidden_when_debug_is_disabled() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="openai-secret",
    )

    assert format_debug_error(RuntimeError("provider failed"), settings) is None
