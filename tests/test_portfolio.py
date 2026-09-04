import asyncio
from decimal import Decimal

from app.models.market import MarketDataError, MarketDataResult
from app.models.portfolio import Portfolio, PortfolioAsset
from app.models.source import DataSource
from app.tools.portfolio import create_portfolio_tool, read_portfolio


class FakeGateway:
    def __init__(self) -> None:
        self.portfolio_calls = 0

    async def get_portfolio(self) -> Portfolio:
        self.portfolio_calls += 1
        return Portfolio(
            assets=[
                PortfolioAsset(
                    symbol="BTC",
                    amount=Decimal("0.05"),
                    usd_value=Decimal("5500"),
                    weight=Decimal("1"),
                )
            ],
            total_usd_value=Decimal("5500"),
            data_source=DataSource.BINANCE_DEMO,
        )

    async def get_market_data(self, symbol: str) -> MarketDataResult:
        return MarketDataError(symbol=symbol, error="Not used.")


def test_read_portfolio_delegates_to_injected_gateway() -> None:
    gateway = FakeGateway()

    portfolio = asyncio.run(read_portfolio(gateway))

    assert portfolio.data_source is DataSource.BINANCE_DEMO
    assert gateway.portfolio_calls == 1


def test_portfolio_tool_keeps_stable_ai_visible_name() -> None:
    tool = create_portfolio_tool(FakeGateway())

    assert tool.name == "get_portfolio"
    assert "Binance Demo" in tool.description
