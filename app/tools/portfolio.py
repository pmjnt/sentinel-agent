from agents import FunctionTool, function_tool

from app.gateways import PortfolioMarketGateway
from app.models.portfolio import Portfolio


async def read_portfolio(gateway: PortfolioMarketGateway) -> Portfolio:
    """Application boundary kept separate from the Agents SDK wrapper."""
    return await gateway.get_portfolio()


def create_portfolio_tool(gateway: PortfolioMarketGateway) -> FunctionTool:
    async def get_portfolio() -> Portfolio:
        """Read current simulated holdings from Binance Demo Trading.

        Use this tool whenever a request needs holdings, USD values, allocation,
        or portfolio concentration. The result is demo data, not a real portfolio.
        """
        return await read_portfolio(gateway)

    return function_tool(get_portfolio, name_override="get_portfolio")
