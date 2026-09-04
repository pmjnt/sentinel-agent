from agents import Agent, set_tracing_disabled

from app.agent.prompts import SENTINEL_INSTRUCTIONS
from app.config import Settings
from app.tools.market import get_market_data_tool
from app.tools.portfolio import get_portfolio_tool


def create_sentinel_agent(settings: Settings) -> Agent:
    """Create Sentinel with its temporary read-only analysis tools."""
    set_tracing_disabled(True)

    return Agent(
        name="Sentinel",
        model=settings.agents_model,
        instructions=SENTINEL_INSTRUCTIONS,
        tools=[get_portfolio_tool, get_market_data_tool],
    )
