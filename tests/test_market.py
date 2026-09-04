from decimal import Decimal

from app.models.market import MarketData, MarketDataError, Volatility
from app.tools.market import get_market_data


def test_get_market_data_returns_btc_mock_data() -> None:
    market_data = get_market_data("BTCUSDT")

    assert isinstance(market_data, MarketData)
    assert market_data.price == Decimal("110000")
    assert market_data.change_24h_percent == Decimal("-4.2")
    assert market_data.volatility is Volatility.HIGH
    assert market_data.estimated_slippage_percent == Decimal("0.05")


def test_get_market_data_returns_error_for_unsupported_symbol() -> None:
    market_data = get_market_data("SOLUSDT")

    assert isinstance(market_data, MarketDataError)
    assert market_data.error == "Unsupported symbol: SOLUSDT"
