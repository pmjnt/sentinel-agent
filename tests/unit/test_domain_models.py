from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy
from app.models.portfolio import PortfolioAsset


def test_asset_symbol_is_normalized() -> None:
    asset = PortfolioAsset(
        symbol=" btc ",
        amount=Decimal("0.05"),
        usd_value=Decimal("5500"),
    )

    assert asset.symbol == "BTC"


def test_negative_asset_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PortfolioAsset(
            symbol="BTC",
            amount=Decimal("0.05"),
            usd_value=Decimal("-1"),
        )


def test_policy_weight_outside_zero_to_one_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PortfolioPolicy(max_asset_weight=Decimal("1.1"))


def test_market_data_requires_supported_fields() -> None:
    market = MarketData(
        symbol="btcusdt",
        price=Decimal("110000"),
        change_24h_percent=Decimal("-4.2"),
        volatility=Volatility.HIGH,
        estimated_slippage_percent=Decimal("0.05"),
    )

    assert market.symbol == "BTCUSDT"
