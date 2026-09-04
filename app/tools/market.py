from agents import function_tool

from decimal import Decimal

from app.models.market import (
    MarketData,
    MarketDataError,
    MarketDataResult,
    Volatility,
)


_MOCK_MARKET_DATA = {
    "BTCUSDT": MarketData(
        symbol="BTCUSDT",
        price=Decimal("110000"),
        change_24h_percent=Decimal("-4.2"),
        volatility=Volatility.HIGH,
        estimated_slippage_percent=Decimal("0.05"),
    ),
    "ETHUSDT": MarketData(
        symbol="ETHUSDT",
        price=Decimal("4300"),
        change_24h_percent=Decimal("-2.1"),
        volatility=Volatility.MEDIUM,
        estimated_slippage_percent=Decimal("0.08"),
    ),
}


def get_market_data(symbol: str) -> MarketDataResult:
    """Return mocked market data for a crypto trading pair.

    Use this tool when a request needs a mocked current price, 24-hour price
    change, or volatility. Pass a pair such as BTCUSDT or ETHUSDT.

    Args:
        symbol: Crypto trading pair to look up.
    """
    normalized_symbol = symbol.strip().upper()
    market_data = _MOCK_MARKET_DATA.get(normalized_symbol)

    if market_data is None:
        return MarketDataError(
            symbol=normalized_symbol,
            error=f"Unsupported symbol: {normalized_symbol}",
        )

    return market_data.model_copy()


# The Agent receives this SDK wrapper; regular tests call get_market_data directly.
get_market_data_tool = function_tool(
    get_market_data,
    name_override="get_market_data",
)
