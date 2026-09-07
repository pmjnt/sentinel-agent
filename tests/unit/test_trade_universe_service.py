import pytest

from app.models.symbol import TradingSymbolInfo
from app.services.trade_universe_service import (
    DEFAULT_TRADE_SYMBOLS,
    TradeUniverseError,
    requires_symbol_override,
)


def _info(**changes) -> TradingSymbolInfo:
    values = {
        "symbol": "SOLUSDT",
        "status": "TRADING",
        "base_asset": "SOL",
        "quote_asset": "USDT",
        "order_types": ("LIMIT", "MARKET"),
        "is_spot_trading_allowed": True,
        "quote_order_qty_market_allowed": True,
    }
    values.update(changes)
    return TradingSymbolInfo(**values)


def test_default_universe_contains_popular_spot_pairs() -> None:
    assert DEFAULT_TRADE_SYMBOLS == frozenset(
        {
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "ADAUSDT",
            "DOGEUSDT",
        }
    )
    assert requires_symbol_override(_info()) is False


def test_valid_non_default_pair_requires_override() -> None:
    assert requires_symbol_override(
        _info(symbol="LINKUSDT", base_asset="LINK")
    ) is True


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "BREAK"},
        {"quote_asset": "BTC"},
        {"is_spot_trading_allowed": False},
        {"order_types": ("LIMIT",)},
        {"quote_order_qty_market_allowed": False},
    ],
)
def test_ineligible_pair_is_always_blocked(changes: dict[str, object]) -> None:
    with pytest.raises(TradeUniverseError):
        requires_symbol_override(_info(**changes))
