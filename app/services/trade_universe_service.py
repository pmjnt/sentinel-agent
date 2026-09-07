from app.models.symbol import TradingSymbolInfo


DEFAULT_TRADE_SYMBOLS = frozenset(
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


class TradeUniverseError(ValueError):
    pass


def require_trade_eligibility(info: TradingSymbolInfo) -> None:
    if info.status != "TRADING":
        raise TradeUniverseError("Binance symbol is not currently trading.")
    if info.quote_asset != "USDT":
        raise TradeUniverseError("Only USDT quote markets are supported.")
    if info.symbol != f"{info.base_asset}{info.quote_asset}":
        raise TradeUniverseError("Binance symbol identity is inconsistent.")
    if not info.is_spot_trading_allowed:
        raise TradeUniverseError("Binance symbol is not enabled for Spot trading.")
    if "MARKET" not in info.order_types:
        raise TradeUniverseError("Binance symbol does not support market orders.")
    if not info.quote_order_qty_market_allowed:
        raise TradeUniverseError(
            "Binance symbol does not support quote-value market orders."
        )


def requires_symbol_override(info: TradingSymbolInfo) -> bool:
    require_trade_eligibility(info)
    return info.symbol not in DEFAULT_TRADE_SYMBOLS
