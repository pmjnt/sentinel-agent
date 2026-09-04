from app.agent import create_sentinel_agent
from app.config import LLMProvider, Settings


def test_create_sentinel_agent_uses_configured_litellm_model() -> None:
    settings = Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        gemini_api_key="test-gemini-key",
    )

    agent = create_sentinel_agent(settings)

    assert agent.model == "litellm/gemini/gemini-3.5-flash-lite"
    assert [tool.name for tool in agent.tools] == [
        "get_portfolio",
        "get_market_data",
    ]
