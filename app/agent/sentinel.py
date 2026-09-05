from agents import Agent, set_tracing_disabled

from app.agent.model_settings import build_agent_model_settings
from app.agent.prompts import SENTINEL_INSTRUCTIONS
from app.config import Settings
from app.gateways import PortfolioMarketGateway
from app.tools.market import create_market_data_tool
from app.tools.portfolio import create_portfolio_tool


def create_sentinel_agent(
    settings: Settings,
    gateway: PortfolioMarketGateway,
) -> Agent:
    """Create Sentinel with gateway-backed read-only analysis tools."""
    set_tracing_disabled(True)

    return Agent(
        name="Sentinel",
        model=settings.agents_model,
        model_settings=build_agent_model_settings(settings),
        instructions=SENTINEL_INSTRUCTIONS,
        tools=[create_portfolio_tool(gateway), create_market_data_tool(gateway)],
    )
