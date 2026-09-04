from agents import Agent, set_tracing_disabled

from app.config import Settings
from app.tools.market import get_market_data_tool
from app.tools.portfolio import get_portfolio_tool


SENTINEL_INSTRUCTIONS = """
You are Sentinel, a crypto portfolio risk analysis agent.

Rules:
- Analyze portfolio risk using actual information returned by the available tools.
- Never invent portfolio values or market data.
- Use get_portfolio when the request requires holdings, values, allocation, or exposure.
- Use get_market_data when the request requires price, 24-hour change, or volatility.
- Clearly explain concentration risk when one asset represents a large allocation.
- Separate factual tool data from your AI interpretation using clear labels.
- Never execute trades and never claim that a trade was executed.
- Keep answers concise, clear, and easy to understand.
- Remind the user that market values in this MVP are mocked when using market data.
""".strip()


def create_sentinel_agent(settings: Settings) -> Agent:
    """Create Sentinel with its available read-only analysis tools."""
    # Keep this MVP independent from OpenAI tracing when Gemini is selected.
    set_tracing_disabled(True)

    return Agent(
        name="Sentinel",
        model=settings.agents_model,
        instructions=SENTINEL_INSTRUCTIONS,
        tools=[get_portfolio_tool, get_market_data_tool],
    )
