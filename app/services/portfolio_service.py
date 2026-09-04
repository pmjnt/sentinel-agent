from decimal import Decimal

from app.models.portfolio import Portfolio, PortfolioAsset
from app.models.source import DataSource


def calculate_portfolio(
    assets: list[PortfolioAsset],
    data_source: DataSource = DataSource.UNKNOWN,
) -> Portfolio:
    """Calculate the authoritative portfolio total and asset weights."""
    total_usd_value = sum(
        (asset.usd_value for asset in assets),
        start=Decimal("0"),
    )
    if total_usd_value <= 0:
        raise ValueError("Portfolio total must be greater than zero.")

    weighted_assets = [
        asset.model_copy(update={"weight": asset.usd_value / total_usd_value})
        for asset in assets
    ]
    return Portfolio(
        assets=weighted_assets,
        total_usd_value=total_usd_value,
        data_source=data_source,
    )
