import asyncio
from decimal import Decimal

import pytest

from app.binance.gateway import BinanceCliGateway, BinanceDataError
from app.config import BinanceEnvironment
from app.models.trade import TradeSide


def _symbol_info(symbol: str = "BTCUSDT", status: str = "TRADING"):
    return {
        "symbols": [
            {
                "symbol": symbol,
                "status": status,
                "baseAsset": symbol.removesuffix("USDT"),
                "quoteAsset": "USDT",
                "orderTypes": ["LIMIT", "MARKET"],
                "isSpotTradingAllowed": True,
                "quoteOrderQtyMarketAllowed": True,
            }
        ]
    }


class RecordingRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def run(self, arguments, *, authenticated=False):
        self.calls.append((list(arguments), authenticated))
        return self.responses.pop(0)


def test_market_order_uses_fixed_authenticated_cli_arguments() -> None:
    runner = RecordingRunner(
        [
            _symbol_info(),
            {"symbol": "BTCUSDT", "orderId": 42, "clientOrderId": "SNTL-ABC", "status": "FILLED"},
        ]
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
            "spot", "exchange-info", "--symbol", "BTCUSDT",
            "--show-permission-sets", "false",
        ], False),
        ([
            "spot", "new-order", "--symbol", "BTCUSDT", "--side", "BUY",
            "--type", "MARKET", "--quote-order-qty", "50",
            "--new-client-order-id", "SNTL-ABC", "--new-order-resp-type", "RESULT",
        ], True)
    ]


def test_order_lookup_uses_original_client_order_id() -> None:
    runner = RecordingRunner(
        [
            {"symbol": "BTCUSDT", "orderId": 42, "clientOrderId": "SNTL-ABC", "status": "FILLED"},
        ]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_order("BTCUSDT", "SNTL-ABC"))

    assert result.status == "FILLED"
    assert runner.calls == [
        (["spot", "get-order", "--symbol", "BTCUSDT", "--orig-client-order-id", "SNTL-ABC"], True)
    ]


def test_order_lookup_remains_available_after_symbol_becomes_inactive() -> None:
    runner = RecordingRunner(
        [
            {"symbol": "LINKUSDT", "orderId": 43, "clientOrderId": "SNTL-DEF", "status": "FILLED"},
        ]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(gateway.get_order("LINKUSDT", "SNTL-DEF"))

    assert result.status == "FILLED"
    assert [call[0][1] for call in runner.calls] == ["get-order"]


def test_execution_accepts_binance_verified_non_default_symbol() -> None:
    runner = RecordingRunner(
        [
            _symbol_info("LINKUSDT"),
            {"symbol": "LINKUSDT", "orderId": 42, "clientOrderId": "SNTL-ABC", "status": "FILLED"},
        ]
    )
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    result = asyncio.run(
        gateway.submit_market_order(
            symbol="LINKUSDT",
            side=TradeSide.BUY,
            quote_usd=Decimal("50"),
            client_order_id="SNTL-ABC",
        )
    )

    assert result.symbol == "LINKUSDT"
    assert runner.calls[-1][0][1] == "new-order"


def test_execution_rejects_inactive_symbol_before_order_submission() -> None:
    runner = RecordingRunner([_symbol_info("LINKUSDT", status="BREAK")])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    with pytest.raises(BinanceDataError, match="not currently trading"):
        asyncio.run(
            gateway.submit_market_order(
                symbol="LINKUSDT",
                side=TradeSide.BUY,
                quote_usd=Decimal("50"),
                client_order_id="SNTL-ABC",
            )
        )

    assert [call[0][1] for call in runner.calls] == ["exchange-info"]


def test_execution_rejects_invalid_binance_order_payload() -> None:
    runner = RecordingRunner([_symbol_info(), {"symbol": "BTCUSDT", "status": "FILLED"}])
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
        [
            _symbol_info(),
            {"symbol": "ETHUSDT", "orderId": 42, "clientOrderId": "OTHER", "status": "FILLED"},
        ]
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
