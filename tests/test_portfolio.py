from decimal import Decimal

from app.tools.portfolio import get_portfolio


def test_get_portfolio_returns_expected_mock_allocation() -> None:
    portfolio = get_portfolio()
    values = {asset.symbol: asset.usd_value for asset in portfolio.assets}

    assert values == {
        "BTC": Decimal("5500"),
        "ETH": Decimal("2500"),
        "USDT": Decimal("2000"),
    }
    assert portfolio.total_usd_value == Decimal("10000")
