from app.agent.sentinel import create_sentinel_agent
from app.config import LLMProvider, Settings
from app.models.market import MarketDataResult
from app.models.portfolio import Portfolio
from app.application import SentinelApplication
from main import create_application


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
