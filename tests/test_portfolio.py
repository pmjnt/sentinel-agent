from app.tools.portfolio import get_portfolio


def test_get_portfolio_returns_expected_mock_allocation() -> None:
    portfolio = get_portfolio()
    values = {asset.symbol: asset.value_usd for asset in portfolio.assets}

    assert values == {"BTC": 6000.0, "ETH": 2500.0, "USDT": 1500.0}
    assert portfolio.total_value_usd == 10000.0
