from agents import FunctionTool, function_tool

from app.gateways import PortfolioMarketGateway
from app.models.market import MarketDataResult


async def read_market_data(
    gateway: PortfolioMarketGateway,
    symbol: str,
) -> MarketDataResult:
    """Application boundary kept separate from the Agents SDK wrapper."""
    return await gateway.get_market_data(symbol)


def create_market_data_tool(gateway: PortfolioMarketGateway) -> FunctionTool:
    async def get_market_data(symbol: str) -> MarketDataResult:
        """Read price, 24-hour change, volatility, and reference slippage from Binance Demo.

        Use this tool when a request needs current simulated market context. Pass
        a compact pair such as BTCUSDT. Never invent values when an error is returned.
        """
        return await read_market_data(gateway, symbol)

    return function_tool(get_market_data, name_override="get_market_data")
