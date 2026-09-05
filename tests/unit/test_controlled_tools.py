import asyncio
from decimal import Decimal

import pytest

from app.agent.controlled_tools import (
    CONTROLLED_TOOLS,
    MissingObservations,
    PolicyToolChange,
    ToolDataError,
    evaluate_cached_portfolio,
    parse_policy_tool_changes,
    read_market_data,
    read_portfolio,
    stage_policy_update,
    view_working_policy,
)
from app.agent.run_context import (
    AnalysisCompletedEvent,
    PolicyUpdatedEvent,
    PolicyViewedEvent,
    SentinelRunContext,
)
from app.models.market import MarketData, MarketDataError, Volatility
from app.models.policy import PolicyChange, PolicyField, PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.models.risk import RiskStatus
from app.services.portfolio_service import calculate_portfolio


def _portfolio():
    return calculate_portfolio(
        [
            PortfolioAsset(
                symbol="BTC", amount=Decimal("0.05"), usd_value=Decimal("5500")
            ),
            PortfolioAsset(
                symbol="ETH", amount=Decimal("0.8"), usd_value=Decimal("2500")
            ),
            PortfolioAsset(
                symbol="USDT", amount=Decimal("2000"), usd_value=Decimal("2000")
            ),
        ]
    )


def _market() -> MarketData:
    return MarketData(
        symbol="BTCUSDT",
        price=Decimal("110000"),
        change_24h_percent=Decimal("-4.2"),
        volatility=Volatility.HIGH,
        estimated_slippage_percent=Decimal("0.05"),
    )


class FakeGateway:
    def __init__(self) -> None:
        self.portfolio = _portfolio()
        self.market_result: MarketData | MarketDataError = _market()

    async def get_portfolio(self):
        return self.portfolio

    async def get_market_data(self, symbol: str):
        assert symbol == "BTCUSDT"
        return self.market_result


def _context(policy: PortfolioPolicy | None = None) -> SentinelRunContext:
    return SentinelRunContext.create(FakeGateway(), policy or PortfolioPolicy())


def test_read_portfolio_stores_the_exact_gateway_observation() -> None:
    context = _context()

    result = asyncio.run(read_portfolio(context))

    assert result is context.gateway.portfolio
    assert context.portfolio is result


def test_market_reader_stores_only_successful_normalized_observation() -> None:
    context = _context()

    result = asyncio.run(read_market_data(context, " btcusdt "))

    assert isinstance(result, MarketData)
    assert context.market_by_symbol == {"BTCUSDT": result}


def test_market_reader_sanitizes_gateway_error() -> None:
    context = _context()
    context.gateway.market_result = MarketDataError(
        symbol="BTCUSDT",
        error="private CLI output",
    )

    result = asyncio.run(read_market_data(context, "BTCUSDT"))

    assert isinstance(result, ToolDataError)
    assert "private CLI output" not in result.message
    assert context.market_by_symbol == {}


def test_policy_update_is_staged_without_external_store() -> None:
    context = _context(PortfolioPolicy(block_high_volatility=True))

    result = stage_policy_update(
        context,
        [
            PolicyChange(
                field=PolicyField.MAX_ASSET_WEIGHT,
                value="0.40",
            ),
            PolicyChange(
                field=PolicyField.BLOCK_HIGH_VOLATILITY,
                value=False,
            ),
        ],
    )

    assert result.max_asset_weight == Decimal("0.40")
    assert result.block_high_volatility is False
    assert len(context.policy_patches) == 1
    assert isinstance(context.ordered_events[0], PolicyUpdatedEvent)


def test_duplicate_policy_fields_are_rejected() -> None:
    context = _context()
    changes = [
        PolicyChange(field=PolicyField.MAX_ASSET_WEIGHT, value="0.40"),
        PolicyChange(field=PolicyField.MAX_ASSET_WEIGHT, value="0.50"),
    ]

    with pytest.raises(ValueError, match="Duplicate policy field"):
        stage_policy_update(context, changes)


def test_simple_policy_tool_values_are_parsed_by_python() -> None:
    changes = parse_policy_tool_changes(
        [
            PolicyToolChange(
                field=PolicyField.MAX_ASSET_WEIGHT,
                value="0.40",
            ),
            PolicyToolChange(
                field=PolicyField.BLOCK_HIGH_VOLATILITY,
                value="true",
            ),
        ]
    )

    assert changes == [
        PolicyChange(
            field=PolicyField.MAX_ASSET_WEIGHT,
            value=Decimal("0.40"),
        ),
        PolicyChange(
            field=PolicyField.BLOCK_HIGH_VOLATILITY,
            value=True,
        ),
    ]


def test_update_policy_tool_schema_avoids_mixed_type_union() -> None:
    update_tool = next(
        tool for tool in CONTROLLED_TOOLS if tool.name == "update_policy"
    )

    assert "anyOf" not in str(update_tool.params_json_schema)


def test_view_policy_records_the_working_policy_snapshot() -> None:
    context = _context(PortfolioPolicy(max_asset_weight=Decimal("0.40")))

    result = view_working_policy(context)

    assert result == context.working_policy
    assert isinstance(context.ordered_events[0], PolicyViewedEvent)


def test_evaluation_requests_portfolio_when_missing() -> None:
    result = evaluate_cached_portfolio(_context(), ["BTC"])

    assert isinstance(result, MissingObservations)
    assert result.required_tools == ["get_portfolio"]


def test_evaluation_lists_required_missing_market_symbols() -> None:
    context = _context(
        PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    )
    context.portfolio = _portfolio()

    result = evaluate_cached_portfolio(context, [])

    assert isinstance(result, MissingObservations)
    assert result.required_tools == ["get_market_data"]
    assert result.missing_symbols == ["BTCUSDT"]


def test_evaluation_stores_deterministic_analysis() -> None:
    context = _context(
        PortfolioPolicy(
            max_asset_weight=Decimal("0.40"),
            block_high_volatility=True,
        )
    )
    context.portfolio = _portfolio()
    context.market_by_symbol["BTCUSDT"] = _market()

    result = evaluate_cached_portfolio(context, [])

    assert result.risk_decision.status is RiskStatus.BLOCKED
    assert context.analyses == [result]
    assert isinstance(context.ordered_events[0], AnalysisCompletedEvent)


def test_controlled_tool_allowlist_contains_no_execution_capability() -> None:
    names = [tool.name for tool in CONTROLLED_TOOLS]

    assert names == [
        "get_portfolio",
        "get_market_data",
        "update_policy",
        "view_policy",
        "evaluate_portfolio_risk",
    ]
    assert not any(
        forbidden in name
        for name in names
        for forbidden in ("order", "trade", "transfer", "withdraw", "cli")
    )
