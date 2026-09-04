from app.models import Volatility
from app.tools.market import get_market_data


def test_get_market_data_returns_btc_mock_data() -> None:
    market_data = get_market_data("BTCUSDT")

    assert market_data.supported is True
    assert market_data.price == 110000.0
    assert market_data.change_24h_percent == -4.2
    assert market_data.volatility is Volatility.HIGH
    assert market_data.error is None


def test_get_market_data_returns_error_for_unsupported_symbol() -> None:
    market_data = get_market_data("SOLUSDT")

    assert market_data.supported is False
    assert market_data.price is None
    assert market_data.error == "Unsupported symbol: SOLUSDT"
