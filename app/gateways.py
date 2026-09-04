from typing import Protocol

from app.models.market import MarketDataResult
from app.models.portfolio import Portfolio


class PortfolioMarketGateway(Protocol):
    async def get_portfolio(self) -> Portfolio: ...

    async def get_market_data(self, symbol: str) -> MarketDataResult: ...
