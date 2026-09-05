from app.agent.sentinel import create_sentinel_agent
from app.config import LLMProvider, Settings
from app.models.market import MarketDataResult
from app.models.portfolio import Portfolio
from app.application import SentinelApplication
from main import configure_litellm_debug, create_application


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
