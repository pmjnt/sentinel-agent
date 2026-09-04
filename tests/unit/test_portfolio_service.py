from decimal import Decimal

import pytest

from app.models.portfolio import PortfolioAsset
from app.services.portfolio_service import calculate_portfolio


def test_calculates_total_and_asset_weights() -> None:
    portfolio = calculate_portfolio(
        [
            PortfolioAsset(
                symbol="BTC",
                amount=Decimal("0.05"),
                usd_value=Decimal("5500"),
            ),
            PortfolioAsset(
                symbol="ETH",
                amount=Decimal("0.58"),
                usd_value=Decimal("2500"),
            ),
            PortfolioAsset(
                symbol="USDT",
                amount=Decimal("2000"),
                usd_value=Decimal("2000"),
            ),
        ]
    )

    assert portfolio.total_usd_value == Decimal("10000")
    assert {asset.symbol: asset.weight for asset in portfolio.assets} == {
        "BTC": Decimal("0.55"),
        "ETH": Decimal("0.25"),
        "USDT": Decimal("0.20"),
    }


def test_rejects_portfolio_with_zero_total() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_portfolio([])
