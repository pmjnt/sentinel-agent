from agents import function_tool

from app.models import MarketData, Volatility


_MOCK_MARKET_DATA = {
    "BTCUSDT": MarketData(
        symbol="BTCUSDT",
        supported=True,
        price=110000.0,
        change_24h_percent=-4.2,
        volatility=Volatility.HIGH,
    ),
    "ETHUSDT": MarketData(
        symbol="ETHUSDT",
        supported=True,
        price=4300.0,
        change_24h_percent=-2.1,
        volatility=Volatility.MEDIUM,
    ),
}


def get_market_data(symbol: str) -> MarketData:
    """Return mocked market data for a crypto trading pair.

    Use this tool when a request needs a mocked current price, 24-hour price
    change, or volatility. Pass a pair such as BTCUSDT or ETHUSDT.

    Args:
        symbol: Crypto trading pair to look up.
    """
    normalized_symbol = symbol.strip().upper()
    market_data = _MOCK_MARKET_DATA.get(normalized_symbol)

    if market_data is None:
        return MarketData(
            symbol=normalized_symbol,
            supported=False,
            error=f"Unsupported symbol: {normalized_symbol}",
        )

    return market_data.model_copy()


# The Agent receives this SDK wrapper; regular tests call get_market_data directly.
get_market_data_tool = function_tool(
    get_market_data,
    name_override="get_market_data",
)
