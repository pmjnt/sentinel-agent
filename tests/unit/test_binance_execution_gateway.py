import asyncio
from decimal import Decimal

import pytest

from app.binance.gateway import BinanceCliGateway, BinanceDataError
from app.config import BinanceEnvironment
from app.models.trade import TradeSide


class RecordingRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def run(self, arguments, *, authenticated=False):
        self.calls.append((list(arguments), authenticated))
        return self.responses.pop(0)


def test_market_order_uses_fixed_authenticated_cli_arguments() -> None:
    runner = RecordingRunner(
        [{"symbol": "BTCUSDT", "orderId": 42, "clientOrderId": "SNTL-ABC", "status": "FILLED"}]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(
        gateway.submit_market_order(
            symbol="BTCUSDT",
            side=TradeSide.BUY,
            quote_usd=Decimal("50"),
            client_order_id="SNTL-ABC",
        )
    )

    assert result.order_id == 42
    assert runner.calls == [
        ([
            "spot", "new-order", "--symbol", "BTCUSDT", "--side", "BUY",
            "--type", "MARKET", "--quote-order-qty", "50",
            "--new-client-order-id", "SNTL-ABC", "--new-order-resp-type", "RESULT",
        ], True)
    ]


def test_order_lookup_uses_original_client_order_id() -> None:
    runner = RecordingRunner(
        [{"symbol": "BTCUSDT", "orderId": 42, "clientOrderId": "SNTL-ABC", "status": "FILLED"}]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_order("BTCUSDT", "SNTL-ABC"))

    assert result.status == "FILLED"
    assert runner.calls == [
        (["spot", "get-order", "--symbol", "BTCUSDT", "--orig-client-order-id", "SNTL-ABC"], True)
    ]


def test_execution_rejects_non_allowlisted_symbol_before_cli() -> None:
    runner = RecordingRunner([])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    with pytest.raises(BinanceDataError, match="not enabled"):
        asyncio.run(
            gateway.submit_market_order(
                symbol="SOLUSDT",
                side=TradeSide.BUY,
                quote_usd=Decimal("50"),
                client_order_id="SNTL-ABC",
            )
        )

    assert runner.calls == []


def test_execution_rejects_invalid_binance_order_payload() -> None:
    runner = RecordingRunner([{"symbol": "BTCUSDT", "status": "FILLED"}])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    with pytest.raises(BinanceDataError, match="invalid order data"):
        asyncio.run(
            gateway.submit_market_order(
                symbol="BTCUSDT",
                side=TradeSide.SELL,
                quote_usd=Decimal("50"),
                client_order_id="SNTL-ABC",
            )
        )


def test_execution_rejects_order_identity_mismatch() -> None:
    runner = RecordingRunner(
        [{"symbol": "ETHUSDT", "orderId": 42, "clientOrderId": "OTHER", "status": "FILLED"}]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    with pytest.raises(BinanceDataError, match="did not match"):
        asyncio.run(
            gateway.submit_market_order(
                symbol="BTCUSDT",
                side=TradeSide.BUY,
                quote_usd=Decimal("50"),
                client_order_id="SNTL-ABC",
            )
        )
