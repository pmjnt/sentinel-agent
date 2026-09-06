from decimal import Decimal
from typing import Protocol

from app.models.market import MarketDataResult
from app.models.portfolio import Portfolio
from app.models.execution import OrderExecutionResult
from app.models.trade import TradeSide


class PortfolioMarketGateway(Protocol):
    async def get_portfolio(self) -> Portfolio: ...

    async def get_market_data(self, symbol: str) -> MarketDataResult: ...


class DemoExecutionGateway(PortfolioMarketGateway, Protocol):
    async def submit_market_order(
        self,
        *,
        symbol: str,
        side: TradeSide,
        quote_usd: Decimal,
        client_order_id: str,
    ) -> OrderExecutionResult: ...

    async def get_order(
        self, symbol: str, client_order_id: str
    ) -> OrderExecutionResult: ...
