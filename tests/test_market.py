import asyncio
from decimal import Decimal

from app.models.market import MarketData, MarketDataResult, Volatility
from app.models.portfolio import Portfolio
from app.models.source import DataSource
from app.tools.market import create_market_data_tool, read_market_data


class FakeGateway:
    def __init__(self) -> None:
        self.requested_symbols: list[str] = []

    async def get_portfolio(self) -> Portfolio:
        raise AssertionError("Not used.")

    async def get_market_data(self, symbol: str) -> MarketDataResult:
        self.requested_symbols.append(symbol)
        return MarketData(
            symbol=symbol,
            price=Decimal("110000"),
            change_24h_percent=Decimal("-4.2"),
            volatility=Volatility.HIGH,
            estimated_slippage_percent=Decimal("0.05"),
            data_source=DataSource.BINANCE_DEMO,
        )


def test_read_market_data_delegates_symbol_to_injected_gateway() -> None:
    gateway = FakeGateway()

    market_data = asyncio.run(read_market_data(gateway, "BTCUSDT"))

    assert isinstance(market_data, MarketData)
    assert market_data.data_source is DataSource.BINANCE_DEMO
    assert gateway.requested_symbols == ["BTCUSDT"]


def test_market_tool_keeps_stable_ai_visible_name() -> None:
    tool = create_market_data_tool(FakeGateway())

    assert tool.name == "get_market_data"
    assert "Binance Demo" in tool.description
