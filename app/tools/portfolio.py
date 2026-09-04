from agents import function_tool

from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioAsset


def get_portfolio() -> Portfolio:
    """Return the user's mocked crypto portfolio.

    Use this tool whenever a request needs the user's holdings, asset values,
    total portfolio value, or portfolio concentration.
    """
    return Portfolio(
        assets=[
            PortfolioAsset(
                symbol="BTC",
                amount=Decimal("0.05"),
                usd_value=Decimal("5500"),
                weight=Decimal("0.55"),
            ),
            PortfolioAsset(
                symbol="ETH",
                amount=Decimal("0.58139535"),
                usd_value=Decimal("2500"),
                weight=Decimal("0.25"),
            ),
            PortfolioAsset(
                symbol="USDT",
                amount=Decimal("2000"),
                usd_value=Decimal("2000"),
                weight=Decimal("0.20"),
            ),
        ],
        total_usd_value=Decimal("10000"),
    )


# Keep the plain function above easy to unit test, and expose this wrapper to the LLM.
get_portfolio_tool = function_tool(
    get_portfolio,
    name_override="get_portfolio",
)
