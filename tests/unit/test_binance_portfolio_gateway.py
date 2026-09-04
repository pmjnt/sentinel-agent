import asyncio
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import pytest

from app.binance.gateway import BinanceCliGateway, BinanceDataError
from app.config import BinanceEnvironment
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
        return next(self._responses)


ACCOUNT_FIXTURE = {
    "balances": [
        {"asset": "BTC", "free": "0.03", "locked": "0.02"},
        {"asset": "ETH", "free": "0.4", "locked": "0.1"},
        {"asset": "USDT", "free": "1800", "locked": "200"},
        {"asset": "BNB", "free": "0", "locked": "0"},
    ]
}

PRICE_FIXTURE = [
    {"symbol": "BTCUSDT", "price": "110000"},
    {"symbol": "ETHUSDT", "price": "5000"},
]


def test_maps_demo_account_to_authoritative_portfolio() -> None:
    runner = FakeRunner([ACCOUNT_FIXTURE, PRICE_FIXTURE])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    portfolio = asyncio.run(gateway.get_portfolio())

    assert runner.calls == [
        (("spot", "get-account", "--omit-zero-balances", "true"), True),
        (("spot", "ticker-price"), False),
    ]
    assert portfolio.data_source is DataSource.BINANCE_DEMO
    assert portfolio.total_usd_value == Decimal("10000")
    assert [asset.symbol for asset in portfolio.assets] == ["BTC", "ETH", "USDT"]
    assert portfolio.assets[0].amount == Decimal("0.05")
    assert portfolio.assets[0].usd_value == Decimal("5500.00")
    assert portfolio.assets[0].weight == Decimal("0.55")
    assert portfolio.assets[1].amount == Decimal("0.5")
    assert portfolio.assets[1].usd_value == Decimal("2500.0")
    assert portfolio.assets[2].usd_value == Decimal("2000")


def test_missing_asset_price_fails_instead_of_dropping_holding() -> None:
    runner = FakeRunner([ACCOUNT_FIXTURE, PRICE_FIXTURE[:1]])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    with pytest.raises(BinanceDataError, match="could not be valued"):
        asyncio.run(gateway.get_portfolio())


@pytest.mark.parametrize(
    "invalid_account",
    [
        {},
        {"balances": "not-a-list"},
        {"balances": [{"asset": "BTC", "free": "invalid", "locked": "0"}]},
    ],
)
def test_invalid_account_schema_returns_safe_error(invalid_account: Any) -> None:
    runner = FakeRunner([invalid_account, PRICE_FIXTURE])
    gateway = BinanceCliGateway(runner, BinanceEnvironment.DEMO)

    with pytest.raises(BinanceDataError, match="invalid account data"):
        asyncio.run(gateway.get_portfolio())
