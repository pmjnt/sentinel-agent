import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
import json
from typing import Any

import pytest

from app.binance.gateway import (
    BinanceCliGateway,
    BinanceDataError,
    classify_volatility,
    estimate_sell_slippage,
)
from app.binance.runner import BinanceCliError
from app.config import BinanceEnvironment
from app.models.market import MarketData, MarketDataError, Volatility
from app.models.source import DataSource
from app.models.symbol import TradingSymbolInfo, TradingSymbolInfoError
from app.models.research import ResearchTimeframe


class FakeRunner:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = iter(responses)
        self.calls: list[tuple[tuple[str, ...], bool]] = []

    async def run(
        self,
        arguments: Sequence[str],
        *,
        authenticated: bool = False,
    ) -> Any:
        self.calls.append((tuple(arguments), authenticated))
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        return response


TICKER_FIXTURE = {
    "symbol": "BTCUSDT",
    "lastPrice": "110000",
    "priceChangePercent": "-4.2",
}

DEPTH_FIXTURE = {
    "lastUpdateId": 123,
    "bids": [["109900", "0.005"], ["109800", "0.01"]],
    "asks": [["110100", "0.01"]],
}

EXCHANGE_INFO_FIXTURE = {
    "symbols": [
        {
            "symbol": "SOLUSDT",
            "status": "TRADING",
            "baseAsset": "SOL",
            "quoteAsset": "USDT",
            "orderTypes": ["LIMIT", "MARKET"],
            "isSpotTradingAllowed": True,
            "quoteOrderQtyMarketAllowed": True,
        }
    ]
}


def _exchange_symbol(symbol: str, *, quote: str = "USDT", status: str = "TRADING"):
    base = symbol.removesuffix(quote)
    return {
        "symbol": symbol,
        "status": status,
        "baseAsset": base,
        "quoteAsset": quote,
        "orderTypes": ["LIMIT", "MARKET"],
        "isSpotTradingAllowed": True,
        "quoteOrderQtyMarketAllowed": True,
    }


def _bulk_ticker(symbol: str, volume: str, close_time: int = 1788778799999):
    return {
        "symbol": symbol,
        "lastPrice": "100",
        "priceChangePercent": "2.5",
        "quoteVolume": volume,
        "closeTime": close_time,
    }


def test_market_universe_uses_verified_spot_usdt_symbols_and_bulk_tickers() -> None:
    exchange = {
        "symbols": [
            _exchange_symbol("BTCUSDT"),
            _exchange_symbol("ETHUSDT"),
            _exchange_symbol("BNBBTC", quote="BTC"),
            _exchange_symbol("SOLUSDT", status="BREAK"),
        ]
    }
    runner = FakeRunner(
        [exchange, [_bulk_ticker("BTCUSDT", "500"), _bulk_ticker("ETHUSDT", "300")]]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_universe())

    assert [ticker.symbol for ticker in result] == ["BTCUSDT", "ETHUSDT"]
    assert result[0].quote_volume == Decimal("500")
    assert result[0].observed_at == datetime.fromtimestamp(
        1788778799999 / 1000, tz=UTC
    )
    assert runner.calls[0] == (
        (
            "spot",
            "exchange-info",
            "--symbol-status",
            "TRADING",
            "--show-permission-sets",
            "false",
        ),
        False,
    )
    assert runner.calls[1][0] == (
        "spot",
        "ticker24hr",
        "--symbols",
        json.dumps(["BTCUSDT", "ETHUSDT"], separators=(",", ":")),
        "--type",
        "FULL",
    )


def test_market_universe_batches_at_most_one_hundred_symbols() -> None:
    symbols = [f"A{index:03}USDT" for index in range(101)]
    exchange = {"symbols": [_exchange_symbol(symbol) for symbol in symbols]}
    runner = FakeRunner(
        [
            exchange,
            [_bulk_ticker(symbol, "1") for symbol in symbols[:100]],
            [_bulk_ticker(symbols[100], "1")],
        ]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_universe())

    ticker_calls = [call for call in runner.calls if call[0][1] == "ticker24hr"]
    assert len(result) == 101
    assert len(ticker_calls) == 2
    assert len(json.loads(ticker_calls[0][0][3])) == 100
    assert len(json.loads(ticker_calls[1][0][3])) == 1


def test_maps_binance_kline_array_to_market_candle() -> None:
    runner = FakeRunner(
        [
            [
                [
                    1788771600000,
                    "100",
                    "110",
                    "90",
                    "105",
                    "12",
                    1788775199999,
                    "1250",
                    100,
                    "6",
                    "625",
                    "0",
                ]
            ]
        ]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(
        gateway.get_market_candles("BTCUSDT", ResearchTimeframe.H4, 180)
    )

    assert len(result) == 1
    assert result[0].close == Decimal("105")
    assert result[0].quote_volume == Decimal("1250")
    assert runner.calls == [
        (
            (
                "spot",
                "klines",
                "--symbol",
                "BTCUSDT",
                "--interval",
                "4h",
                "--limit",
                "180",
            ),
            False,
        )
    ]


@pytest.mark.parametrize("limit", [0, 1001])
def test_kline_limit_is_rejected_before_cli(limit: int) -> None:
    runner = FakeRunner([])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    with pytest.raises(BinanceDataError, match="limit"):
        asyncio.run(
            gateway.get_market_candles("BTCUSDT", ResearchTimeframe.H1, limit)
        )

    assert runner.calls == []


def test_maps_verified_spot_symbol_info() -> None:
    runner = FakeRunner([EXCHANGE_INFO_FIXTURE])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_symbol_info(" solusdt "))

    assert runner.calls == [
        (
            (
                "spot",
                "exchange-info",
                "--symbol",
                "SOLUSDT",
                "--show-permission-sets",
                "false",
            ),
            False,
        )
    ]
    assert isinstance(result, TradingSymbolInfo)
    assert result.symbol == "SOLUSDT"
    assert result.order_types == ("LIMIT", "MARKET")
    assert result.is_spot_trading_allowed is True


def test_empty_exchange_info_returns_safe_error() -> None:
    gateway = BinanceCliGateway(FakeRunner([{"symbols": []}]), BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_symbol_info("LINKUSDT"))

    assert isinstance(result, TradingSymbolInfoError)
    assert result.symbol == "LINKUSDT"


def test_maps_demo_market_data_and_uses_only_fixed_read_commands() -> None:
    runner = FakeRunner([TICKER_FIXTURE, DEPTH_FIXTURE])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_data(" btcusdt "))

    assert runner.calls == [
        (("spot", "ticker24hr", "--symbol", "BTCUSDT"), False),
        (("spot", "depth", "--symbol", "BTCUSDT", "--limit", "100"), False),
    ]
    assert isinstance(result, MarketData)
    assert result.symbol == "BTCUSDT"
    assert result.price == Decimal("110000")
    assert result.change_24h_percent == Decimal("-4.2")
    assert result.volatility is Volatility.HIGH
    assert result.estimated_slippage_percent > 0
    assert result.data_source is DataSource.BINANCE_DEMO


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (Decimal("1.99"), Volatility.LOW),
        (Decimal("2"), Volatility.MEDIUM),
        (Decimal("-3.99"), Volatility.MEDIUM),
        (Decimal("-4"), Volatility.HIGH),
    ],
)
def test_volatility_thresholds_are_deterministic(
    change: Decimal,
    expected: Volatility,
) -> None:
    assert classify_volatility(change) is expected


def test_slippage_uses_a_fixed_one_thousand_usdt_reference_sale() -> None:
    slippage = estimate_sell_slippage(
        bids=[(Decimal("99"), Decimal("5")), (Decimal("98"), Decimal("10"))],
        reference_price=Decimal("100"),
    )

    assert slippage == Decimal("1.5")


@pytest.mark.parametrize("symbol", ["", "BTC/USDT", "BTC USDT", "../../bin/sh"])
def test_invalid_symbol_returns_error_without_calling_cli(symbol: str) -> None:
    runner = FakeRunner([])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_data(symbol))

    assert isinstance(result, MarketDataError)
    assert "Invalid market symbol" in result.error
    assert runner.calls == []


def test_cli_failure_returns_market_error_without_fabricated_values() -> None:
    runner = FakeRunner(
        [
            BinanceCliError("unsafe provider details"),
            BinanceCliError("unsafe provider details"),
        ]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_data("BTCUSDT"))

    assert isinstance(result, MarketDataError)
    assert result.error == "Binance market data could not be retrieved."
    assert "unsafe" not in result.error


def test_transient_public_market_failure_is_retried_once() -> None:
    runner = FakeRunner(
        [
            BinanceCliError("temporary failure"),
            TICKER_FIXTURE,
            DEPTH_FIXTURE,
        ]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_data("BTCUSDT"))

    assert isinstance(result, MarketData)
    assert [call[0][1] for call in runner.calls] == [
        "ticker24hr",
        "ticker24hr",
        "depth",
    ]


def test_invalid_market_schema_returns_clear_error() -> None:
    runner = FakeRunner([{"symbol": "BTCUSDT"}, DEPTH_FIXTURE])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_data("BTCUSDT"))

    assert isinstance(result, MarketDataError)
    assert result.error == "Binance returned invalid market data."


def test_insufficient_depth_returns_error() -> None:
    shallow_depth = {"bids": [["109900", "0.001"]], "asks": []}
    runner = FakeRunner([TICKER_FIXTURE, shallow_depth])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_market_data("BTCUSDT"))

    assert isinstance(result, MarketDataError)
    assert result.error == "Binance order book depth is insufficient."
