import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.agent.controlled_tools import (
    CONTROLLED_TOOLS,
    MissingObservations,
    PolicyToolChange,
    ProfileToolChange,
    ToolDataError,
    evaluate_cached_portfolio,
    parse_policy_tool_changes,
    parse_profile_tool_changes,
    propose_trade_plan,
    read_market_data,
    read_portfolio,
    stage_policy_update,
    stage_profile_update,
    stage_market_research_plan,
    scan_market_candidates,
    analyze_market_candidate,
    finalize_market_research,
    view_working_profile,
    view_working_policy,
)
from app.agent.run_context import (
    AnalysisCompletedEvent,
    PolicyUpdatedEvent,
    PolicyViewedEvent,
    ProfileUpdatedEvent,
    ProfileViewedEvent,
    SentinelRunContext,
)
from app.models.market import MarketData, MarketDataError, Volatility
from app.models.execution import ExecutionPlan
from app.models.profile import (
    InvestmentObjective,
    InvestorProfile,
    InvestorProfileField,
    RiskTolerance,
)
from app.models.policy import PolicyChange, PolicyField, PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.models.risk import RiskStatus
from app.models.symbol import TradingSymbolInfo, TradingSymbolInfoError
from app.models.research import (
    CandidateResearch,
    MarketCandle,
    MarketResearchPlan,
    MarketResearchResult,
    MarketTicker,
    ResearchPriority,
    ResearchTimeframe,
)
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
        self.symbol_info_result: TradingSymbolInfo | TradingSymbolInfoError = (
            TradingSymbolInfo(
                symbol="BTCUSDT",
                status="TRADING",
                base_asset="BTC",
                quote_asset="USDT",
                order_types=("MARKET",),
                is_spot_trading_allowed=True,
                quote_order_qty_market_allowed=True,
            )
        )
        self.market_universe = tuple(
            MarketTicker(
                symbol=symbol,
                price="100",
                change_24h_percent="1",
                quote_volume=str(1000 - index),
                observed_at=datetime(2026, 9, 7, tzinfo=UTC),
            )
            for index, symbol in enumerate(
                [
                    "BTCUSDT",
                    "ETHUSDT",
                    "SOLUSDT",
                    "BNBUSDT",
                    "XRPUSDT",
                    "ADAUSDT",
                ]
            )
        )

    async def get_portfolio(self):
        return self.portfolio

    async def get_market_data(self, symbol: str):
        assert symbol == "BTCUSDT"
        return self.market_result

    async def get_symbol_info(self, symbol: str):
        return self.symbol_info_result

    async def get_market_universe(self):
        return self.market_universe

    async def get_market_candles(self, symbol, timeframe, limit):
        start = datetime(2026, 9, 1, tzinfo=UTC)
        return tuple(
            MarketCandle(
                open_time=start + timedelta(hours=index),
                close_time=start + timedelta(hours=index + 1),
                open=str(100 + index),
                high=str(101 + index),
                low=str(99 + index),
                close=str(100 + index),
                volume="10",
                quote_volume="1000",
            )
            for index in range(limit)
        )


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


def test_market_reader_converts_asset_to_usdt_pair() -> None:
    context = _context()

    result = asyncio.run(read_market_data(context, "BTC"))

    assert isinstance(result, MarketData)
    assert result.symbol == "BTCUSDT"
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


def test_market_reader_sanitizes_gateway_exception() -> None:
    class RaisingGateway(FakeGateway):
        async def get_market_data(self, symbol: str):
            raise RuntimeError("private CLI output")

    context = SentinelRunContext.create(RaisingGateway(), PortfolioPolicy())

    result = asyncio.run(read_market_data(context, "BTCUSDT"))

    assert isinstance(result, ToolDataError)
    assert result.code == "MARKET_UNAVAILABLE"
    assert "private CLI output" not in result.message


def test_market_reader_skips_usdt_self_pair_without_failing_the_run() -> None:
    context = _context()

    result = asyncio.run(read_market_data(context, "USDTUSDT"))

    assert result.status == "NOT_REQUIRED"
    assert context.market_by_symbol == {}
    assert context.data_errors == []


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


def test_profile_tool_values_are_parsed_and_staged() -> None:
    context = _context()
    patch = parse_profile_tool_changes(
        [
            ProfileToolChange(
                field=InvestorProfileField.OBJECTIVE,
                value="growth",
            ),
            ProfileToolChange(
                field=InvestorProfileField.TIME_HORIZON_MONTHS,
                value="36",
            ),
            ProfileToolChange(
                field=InvestorProfileField.RISK_TOLERANCE,
                value="medium",
            ),
        ]
    )

    result = stage_profile_update(context, patch)

    assert result.objective is InvestmentObjective.GROWTH
    assert result.time_horizon_months == 36
    assert result.risk_tolerance is RiskTolerance.MEDIUM
    assert isinstance(context.ordered_events[0], ProfileUpdatedEvent)


def test_view_profile_records_the_working_profile_snapshot() -> None:
    context = SentinelRunContext.create(
        FakeGateway(),
        PortfolioPolicy(),
        InvestorProfile(objective=InvestmentObjective.BALANCED),
    )

    result = view_working_profile(context)

    assert result == context.working_profile
    assert isinstance(context.ordered_events[0], ProfileViewedEvent)


def test_update_profile_tool_schema_avoids_mixed_type_union() -> None:
    update_tool = next(
        tool
        for tool in CONTROLLED_TOOLS
        if tool.name == "update_investor_profile"
    )

    assert "anyOf" not in str(update_tool.params_json_schema)


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
        "update_investor_profile",
        "view_investor_profile",
        "evaluate_portfolio_risk",
        "propose_trade",
        "set_market_research_plan",
        "scan_top_markets",
        "analyze_market_history",
        "finalize_market_research",
    ]
    assert not any(
        forbidden in name
        for name in names
        for forbidden in ("order", "execute", "transfer", "withdraw", "cli")
    )


def _research_plan(candidate_limit: int = 5) -> MarketResearchPlan:
    return MarketResearchPlan(
        candidate_limit=candidate_limit,
        timeframes=[ResearchTimeframe.H1],
        lookback_days=1,
        priorities=[ResearchPriority.MOMENTUM],
    )


def test_market_scan_requires_a_validated_research_plan() -> None:
    result = asyncio.run(scan_market_candidates(_context()))

    assert isinstance(result, ToolDataError)
    assert result.code == "RESEARCH_PLAN_REQUIRED"


def test_research_flow_only_analyzes_scanned_candidates_and_finalizes_two() -> None:
    context = _context()
    stage_market_research_plan(context, _research_plan())
    scan = asyncio.run(scan_market_candidates(context))

    assert [candidate.symbol for candidate in scan.candidates] == [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
    ]
    rejected = asyncio.run(analyze_market_candidate(context, "LINKUSDT"))
    assert isinstance(rejected, ToolDataError)
    assert rejected.code == "CANDIDATE_NOT_SCANNED"

    first = asyncio.run(analyze_market_candidate(context, "BTCUSDT"))
    assert isinstance(first, CandidateResearch)

    second = asyncio.run(analyze_market_candidate(context, "ETHUSDT"))
    result = finalize_market_research(context)

    assert isinstance(second, CandidateResearch)
    assert isinstance(result, MarketResearchResult)
    assert [item.candidate.symbol for item in result.analyzed_candidates] == [
        "BTCUSDT",
        "ETHUSDT",
    ]


def test_research_deep_analysis_is_limited_to_five_candidates() -> None:
    context = _context()
    stage_market_research_plan(context, _research_plan(candidate_limit=6))
    asyncio.run(scan_market_candidates(context))
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]:
        assert isinstance(
            asyncio.run(analyze_market_candidate(context, symbol)),
            CandidateResearch,
        )

    result = asyncio.run(analyze_market_candidate(context, "ADAUSDT"))

    assert isinstance(result, ToolDataError)
    assert result.code == "RESEARCH_SCOPE_EXCEEDED"


def test_failed_deep_analysis_attempts_still_count_toward_run_limit() -> None:
    class FailingHistoryGateway(FakeGateway):
        def __init__(self) -> None:
            super().__init__()
            self.history_calls: list[str] = []

        async def get_market_candles(self, symbol, timeframe, limit):
            self.history_calls.append(symbol)
            raise RuntimeError("unavailable")

    gateway = FailingHistoryGateway()
    context = SentinelRunContext.create(gateway, PortfolioPolicy())
    stage_market_research_plan(context, _research_plan(candidate_limit=6))
    asyncio.run(scan_market_candidates(context))
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]:
        result = asyncio.run(analyze_market_candidate(context, symbol))
        assert isinstance(result, ToolDataError)
        assert result.code == "MARKET_HISTORY_UNAVAILABLE"

    sixth = asyncio.run(analyze_market_candidate(context, "ADAUSDT"))
    retry = asyncio.run(analyze_market_candidate(context, "BTCUSDT"))

    assert sixth.code == "RESEARCH_SCOPE_EXCEEDED"
    assert retry.code == "MARKET_HISTORY_UNAVAILABLE"
    assert gateway.history_calls == [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
    ]


def test_research_plan_cannot_be_replaced_during_one_run() -> None:
    context = _context()
    first = stage_market_research_plan(context, _research_plan())
    second = stage_market_research_plan(context, _research_plan(candidate_limit=6))

    assert isinstance(first, MarketResearchPlan)
    assert isinstance(second, ToolDataError)
    assert second.code == "RESEARCH_PLAN_ALREADY_SET"
    assert context.research_plan == first


def test_research_finalization_requires_two_verified_candidates() -> None:
    context = _context()
    stage_market_research_plan(context, _research_plan())
    asyncio.run(scan_market_candidates(context))
    asyncio.run(analyze_market_candidate(context, "BTCUSDT"))

    result = finalize_market_research(context)

    assert isinstance(result, ToolDataError)
    assert result.code == "RESEARCH_INCOMPLETE"


def test_finalized_research_cannot_be_mutated_and_refinalization_is_idempotent() -> None:
    context = _context()
    stage_market_research_plan(context, _research_plan())
    asyncio.run(scan_market_candidates(context))
    asyncio.run(analyze_market_candidate(context, "BTCUSDT"))
    asyncio.run(analyze_market_candidate(context, "ETHUSDT"))
    first = finalize_market_research(context)

    late = asyncio.run(analyze_market_candidate(context, "SOLUSDT"))
    second = finalize_market_research(context)

    assert isinstance(first, MarketResearchResult)
    assert isinstance(late, ToolDataError)
    assert late.code == "RESEARCH_FINALIZED"
    assert second is first
    assert context.market_research_results == [first]


def test_trade_proposal_requires_fresh_observations() -> None:
    context = _context()

    result = asyncio.run(
        propose_trade_plan(
            context,
            symbol="BTCUSDT",
            side="BUY",
            quote_usd="50",
            reason="Limited growth exposure.",
        )
    )

    assert isinstance(result, MissingObservations)
    assert result.required_tools == ["get_portfolio", "get_market_data"]


def test_trade_proposal_is_staged_but_not_executed() -> None:
    context = _context()
    context.portfolio = _portfolio()
    context.market_by_symbol["BTCUSDT"] = _market()

    result = asyncio.run(
        propose_trade_plan(
            context,
            symbol="BTCUSDT",
            side="BUY",
            quote_usd="50",
            reason="Limited growth exposure.",
        )
    )

    assert isinstance(result, ExecutionPlan)
    assert context.execution_plans == [result]
    assert result.order_id is None


def test_trade_proposal_rejects_unverified_symbol_information() -> None:
    context = _context()
    context.portfolio = _portfolio()
    context.market_by_symbol["BTCUSDT"] = _market()
    context.gateway.symbol_info_result = TradingSymbolInfoError(
        symbol="BTCUSDT",
        error="private provider output",
    )

    result = asyncio.run(
        propose_trade_plan(
            context,
            symbol="BTCUSDT",
            side="BUY",
            quote_usd="50",
            reason="Limited growth exposure.",
        )
    )

    assert isinstance(result, ToolDataError)
    assert result.code == "SYMBOL_UNAVAILABLE"
    assert "private provider output" not in result.message
