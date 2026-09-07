import asyncio
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import pytest

from app.binance.gateway import (
    BinanceCliGateway,
    classify_volatility,
    estimate_sell_slippage,
)
from app.binance.runner import BinanceCliError
from app.config import BinanceEnvironment
from app.models.market import MarketData, MarketDataError, Volatility
from app.models.source import DataSource


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
