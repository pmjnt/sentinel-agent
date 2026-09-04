from agents import function_tool

from app.models import Portfolio, PortfolioAsset


def get_portfolio() -> Portfolio:
    """Return the user's mocked crypto portfolio.

    Use this tool whenever a request needs the user's holdings, asset values,
    total portfolio value, or portfolio concentration.
    """
    return Portfolio(
        assets=[
            PortfolioAsset(symbol="BTC", value_usd=6000.0),
            PortfolioAsset(symbol="ETH", value_usd=2500.0),
            PortfolioAsset(symbol="USDT", value_usd=1500.0),
        ],
        total_value_usd=10000.0,
    )


# Keep the plain function above easy to unit test, and expose this wrapper to the LLM.
get_portfolio_tool = function_tool(
    get_portfolio,
    name_override="get_portfolio",
)
