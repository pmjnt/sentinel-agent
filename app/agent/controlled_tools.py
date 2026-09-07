import asyncio
from decimal import Decimal, InvalidOperation
from typing import Literal

from agents import FunctionTool, RunContextWrapper, function_tool
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.run_context import (
    AnalysisCompletedEvent,
    PolicyUpdatedEvent,
    PolicyViewedEvent,
    ProfileUpdatedEvent,
    ProfileViewedEvent,
    SentinelRunContext,
    TradeProposedEvent,
    ResearchPlanSetEvent,
    MarketScanCompletedEvent,
    MarketCandidateAnalyzedEvent,
    MarketResearchCompletedEvent,
)
from app.models.execution import ExecutionPlan
from app.models.analysis import PortfolioAnalysis
from app.models.market import MarketData, MarketDataError
from app.models.profile import (
    InvestmentObjective,
    InvestorProfile,
    InvestorProfileField,
    InvestorProfilePatch,
    LiquidityNeed,
    RiskTolerance,
)
from app.models.policy import PolicyChange, PolicyField, PolicyPatch, PortfolioPolicy
from app.models.portfolio import Portfolio
from app.models.symbol import TradingSymbolInfoError
from app.models.research import (
    CandidateResearch,
    MarketResearchPlan,
    MarketResearchResult,
    MarketScan,
    ResearchPriority,
    ResearchTimeframe,
)
from app.models.trade import TradeSide
from app.services.policy_service import apply_policy_patch
from app.services.profile_service import apply_profile_patch
from app.services.portfolio_analysis_service import (
    AnalysisDataError,
    evaluate_portfolio_observations,
    required_market_symbols,
)
from app.services.trade_proposal_service import TradeProposalError, create_trade_plan
from app.services.market_research_service import (
    analyze_candles,
    candle_limit,
    rank_market_candidates,
)


MAX_MARKET_OBSERVATIONS = 20
MAX_DEEP_RESEARCH_CANDIDATES = 5


class ToolDataError(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ERROR"] = "ERROR"
    code: str
    message: str


class ToolDataNotRequired(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["NOT_REQUIRED"] = "NOT_REQUIRED"
    message: str


class MissingObservations(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["MISSING_OBSERVATIONS"] = "MISSING_OBSERVATIONS"
    required_tools: list[str]
    missing_symbols: list[str] = Field(default_factory=list)


class PolicyToolChange(BaseModel):
    """Simple LLM-facing policy change; Python parses the field-specific value."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: PolicyField
    value: str = Field(
        description="Decimal, true, false, or null written as text."
    )

    @field_validator("value")
    @classmethod
    def normalize_value(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Policy value must not be empty.")
        return normalized


class ProfileToolChange(BaseModel):
    """Simple LLM-facing investor profile change parsed by trusted Python."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: InvestorProfileField
    value: str = Field(
        description=(
            "Enum, integer, decimal, comma-separated asset symbols, or null as text."
        )
    )

    @field_validator("value")
    @classmethod
    def normalize_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Profile value must not be empty.")
        return normalized


def parse_profile_tool_changes(
    changes: list[ProfileToolChange],
) -> InvestorProfilePatch:
    values: dict[str, object] = {}
    for change in changes:
        field_name = change.field.value
        if field_name in values:
            raise ValueError(f"Duplicate profile field: {field_name}.")
        raw = change.value.strip()
        normalized = raw.upper()
        if normalized == "NULL":
            value: object = None
        elif change.field is InvestorProfileField.OBJECTIVE:
            value = InvestmentObjective(normalized)
        elif change.field is InvestorProfileField.RISK_TOLERANCE:
            value = RiskTolerance(normalized)
        elif change.field is InvestorProfileField.LIQUIDITY_NEED:
            value = LiquidityNeed(normalized)
        elif change.field is InvestorProfileField.TIME_HORIZON_MONTHS:
            value = int(raw)
        elif change.field is InvestorProfileField.ACCEPTABLE_LOSS_PERCENT:
            value = Decimal(raw)
        else:
            value = [symbol.strip() for symbol in raw.split(",")]
        values[field_name] = value

    if not values:
        raise ValueError("At least one profile change is required.")
    return InvestorProfilePatch.model_validate(values)


def parse_policy_tool_changes(
    changes: list[PolicyToolChange],
) -> list[PolicyChange]:
    parsed: list[PolicyChange] = []
    for change in changes:
        if change.value == "null":
            value: Decimal | bool | None = None
        elif change.field is PolicyField.BLOCK_HIGH_VOLATILITY:
            if change.value not in {"true", "false"}:
                raise ValueError(
                    "block_high_volatility must be true, false, or null."
                )
            value = change.value == "true"
        elif change.field is PolicyField.ALLOWED_TRADE_SYMBOLS:
            symbols = tuple(
                symbol.strip().upper()
                for symbol in change.value.split(",")
                if symbol.strip()
            )
            if not symbols:
                raise ValueError("allowed_trade_symbols must list at least one symbol.")
            value = symbols
        else:
            try:
                value = Decimal(change.value)
            except InvalidOperation as error:
                raise ValueError(
                    f"{change.field.value} must be a decimal or null."
                ) from error
        parsed.append(PolicyChange(field=change.field, value=value))
    return parsed


async def read_portfolio(
    context: SentinelRunContext,
) -> Portfolio | ToolDataError:
    try:
        portfolio = await context.gateway.get_portfolio()
    except asyncio.CancelledError:
        raise
    except (RuntimeError, ValueError):
        message = "Portfolio data could not be verified."
        context.data_errors.append(message)
        return ToolDataError(code="PORTFOLIO_UNAVAILABLE", message=message)

    context.portfolio = portfolio
    return portfolio


def normalize_usdt_market(symbol: str) -> str | None:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Market symbol must not be empty.")
    if normalized in {"USDT", "USDTUSDT"}:
        return None
    if normalized.endswith("USDT"):
        return normalized
    return f"{normalized}USDT"


async def read_market_data(
    context: SentinelRunContext,
    symbol: str,
) -> MarketData | ToolDataError | ToolDataNotRequired:
    market_symbol = normalize_usdt_market(symbol)
    if market_symbol is None:
        return ToolDataNotRequired(
            message="USDT is the quote currency; no USDT/USDT market exists or is required."
        )

    try:
        result = await context.gateway.get_market_data(market_symbol)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, ValueError):
        result = MarketDataError(symbol=market_symbol, error="gateway failure")

    if isinstance(result, MarketDataError):
        message = f"Market data could not be verified for {market_symbol}."
        context.data_errors.append(message)
        return ToolDataError(code="MARKET_UNAVAILABLE", message=message)

    context.market_by_symbol[result.symbol] = result
    return result


def stage_policy_update(
    context: SentinelRunContext,
    changes: list[PolicyChange],
) -> PortfolioPolicy:
    values: dict[str, object] = {}
    for change in changes:
        field_name = change.field.value
        if field_name in values:
            raise ValueError(f"Duplicate policy field: {field_name}.")
        if (
            change.field is PolicyField.BLOCK_HIGH_VOLATILITY
            and change.value is not None
            and not isinstance(change.value, bool)
        ):
            raise ValueError("block_high_volatility must be true, false, or null.")
        values[field_name] = change.value

    if not values:
        raise ValueError("At least one policy change is required.")

    patch = PolicyPatch.model_validate(values)
    context.working_policy = apply_policy_patch(context.working_policy, patch)
    context.policy_patches.append(patch)
    context.ordered_events.append(
        PolicyUpdatedEvent(patch=patch, policy=context.working_policy)
    )
    return context.working_policy


def view_working_policy(context: SentinelRunContext) -> PortfolioPolicy:
    context.ordered_events.append(PolicyViewedEvent(context.working_policy))
    return context.working_policy


def stage_profile_update(
    context: SentinelRunContext,
    patch: InvestorProfilePatch,
) -> InvestorProfile:
    context.working_profile = apply_profile_patch(context.working_profile, patch)
    context.profile_patches.append(patch)
    context.ordered_events.append(
        ProfileUpdatedEvent(patch=patch, profile=context.working_profile)
    )
    return context.working_profile


def view_working_profile(context: SentinelRunContext) -> InvestorProfile:
    context.ordered_events.append(ProfileViewedEvent(context.working_profile))
    return context.working_profile


def evaluate_cached_portfolio(
    context: SentinelRunContext,
    focus_symbols: list[str],
) -> PortfolioAnalysis | MissingObservations | ToolDataError:
    if context.portfolio is None:
        return MissingObservations(required_tools=["get_portfolio"])

    required_symbols = required_market_symbols(
        context.portfolio,
        context.working_policy,
        focus_symbols,
    )
    if len(required_symbols) > MAX_MARKET_OBSERVATIONS:
        message = "Market analysis scope exceeds the safe limit."
        if message not in context.data_errors:
            context.data_errors.append(message)
        return ToolDataError(code="MARKET_SCOPE_TOO_LARGE", message=message)

    missing_symbols = [
        symbol
        for symbol in required_symbols
        if symbol not in context.market_by_symbol
    ]
    if missing_symbols:
        return MissingObservations(
            required_tools=["get_market_data"],
            missing_symbols=missing_symbols,
        )

    try:
        analysis = evaluate_portfolio_observations(
            context.working_policy,
            context.portfolio,
            context.market_by_symbol,
        )
    except AnalysisDataError:
        message = "Required market data could not be verified."
        context.data_errors.append(message)
        return MissingObservations(
            required_tools=["get_market_data"],
            missing_symbols=required_symbols,
        )

    context.analyses.append(analysis)
    context.ordered_events.append(AnalysisCompletedEvent(analysis))
    return analysis


async def propose_trade_plan(
    context: SentinelRunContext,
    *,
    symbol: str,
    side: str,
    quote_usd: str,
    reason: str,
) -> ExecutionPlan | MissingObservations | ToolDataError:
    normalized_symbol = symbol.strip().upper()
    missing_tools: list[str] = []
    if context.portfolio is None:
        missing_tools.append("get_portfolio")
    if normalized_symbol not in context.market_by_symbol:
        missing_tools.append("get_market_data")
    if missing_tools:
        return MissingObservations(
            required_tools=missing_tools,
            missing_symbols=(
                [normalized_symbol]
                if "get_market_data" in missing_tools and normalized_symbol
                else []
            ),
        )

    symbol_info = await context.gateway.get_symbol_info(normalized_symbol)
    if isinstance(symbol_info, TradingSymbolInfoError):
        return ToolDataError(
            code="SYMBOL_UNAVAILABLE",
            message=(
                f"Trading eligibility could not be verified for "
                f"{normalized_symbol}."
            ),
        )

    try:
        plan = create_trade_plan(
            session_id=context.session_id,
            symbol=normalized_symbol,
            side=TradeSide(side.strip().upper()),
            quote_usd=Decimal(quote_usd.strip()),
            reason=reason,
            policy=context.working_policy,
            portfolio=context.portfolio,
            market=context.market_by_symbol[normalized_symbol],
            symbol_info=symbol_info,
        )
    except (InvalidOperation, ValueError, TradeProposalError) as error:
        return ToolDataError(code="PROPOSAL_REJECTED", message=str(error))

    context.execution_plans.append(plan)
    context.ordered_events.append(TradeProposedEvent(plan))
    return plan


def stage_market_research_plan(
    context: SentinelRunContext,
    plan: MarketResearchPlan,
) -> MarketResearchPlan:
    context.research_plan = plan
    context.market_scan = None
    context.research_by_symbol.clear()
    context.research_failed_symbols.clear()
    context.market_research_results.clear()
    context.ordered_events.append(ResearchPlanSetEvent(plan))
    return plan


async def scan_market_candidates(
    context: SentinelRunContext,
) -> MarketScan | ToolDataError:
    if context.research_plan is None:
        return ToolDataError(
            code="RESEARCH_PLAN_REQUIRED",
            message="Create a validated market research plan before scanning.",
        )
    try:
        universe = await context.gateway.get_market_universe()
        candidates = rank_market_candidates(
            universe,
            limit=context.research_plan.candidate_limit,
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, ValueError):
        message = "Binance market universe could not be verified."
        context.data_errors.append(message)
        return ToolDataError(code="MARKET_SCAN_UNAVAILABLE", message=message)

    if len(candidates) < 2:
        message = "Fewer than two verified market candidates were available."
        context.data_errors.append(message)
        return ToolDataError(code="INSUFFICIENT_CANDIDATES", message=message)
    scan = MarketScan(
        candidates=candidates,
        observed_at=max(candidate.observed_at for candidate in candidates),
    )
    context.market_scan = scan
    context.ordered_events.append(MarketScanCompletedEvent(scan))
    return scan


async def analyze_market_candidate(
    context: SentinelRunContext,
    symbol: str,
) -> CandidateResearch | ToolDataError:
    normalized = symbol.strip().upper()
    if context.research_plan is None or context.market_scan is None:
        return ToolDataError(
            code="MARKET_SCAN_REQUIRED",
            message="Scan verified Binance markets before analyzing history.",
        )
    candidate = next(
        (
            item
            for item in context.market_scan.candidates
            if item.symbol == normalized
        ),
        None,
    )
    if candidate is None:
        return ToolDataError(
            code="CANDIDATE_NOT_SCANNED",
            message=f"{normalized or 'UNKNOWN'} was not in the verified market scan.",
        )
    if normalized in context.research_by_symbol:
        return context.research_by_symbol[normalized]
    if len(context.research_by_symbol) >= MAX_DEEP_RESEARCH_CANDIDATES:
        return ToolDataError(
            code="RESEARCH_SCOPE_EXCEEDED",
            message="Deep market research is limited to five candidates per run.",
        )

    try:
        candle_sets = await asyncio.gather(
            *(
                context.gateway.get_market_candles(
                    normalized,
                    timeframe,
                    candle_limit(context.research_plan, timeframe),
                )
                for timeframe in context.research_plan.timeframes
            )
        )
        timeframe_results = tuple(
            analyze_candles(candles, timeframe)
            for timeframe, candles in zip(
                context.research_plan.timeframes,
                candle_sets,
            )
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, ValueError):
        if normalized not in context.research_failed_symbols:
            context.research_failed_symbols.append(normalized)
        return ToolDataError(
            code="MARKET_HISTORY_UNAVAILABLE",
            message=f"Market history could not be verified for {normalized}.",
        )

    research = CandidateResearch(
        candidate=candidate,
        timeframes=timeframe_results,
    )
    context.research_by_symbol[normalized] = research
    context.ordered_events.append(MarketCandidateAnalyzedEvent(research))
    return research


def finalize_market_research(
    context: SentinelRunContext,
) -> MarketResearchResult | ToolDataError:
    if context.research_plan is None or context.market_scan is None:
        return ToolDataError(
            code="MARKET_SCAN_REQUIRED",
            message="A verified market scan is required before finalization.",
        )
    if len(context.research_by_symbol) < 2:
        return ToolDataError(
            code="RESEARCH_INCOMPLETE",
            message="Analyze at least two verified candidates before comparing them.",
        )
    result = MarketResearchResult(
        plan=context.research_plan,
        scan=context.market_scan,
        analyzed_candidates=tuple(context.research_by_symbol.values()),
        failed_symbols=tuple(context.research_failed_symbols),
    )
    context.market_research_results.append(result)
    context.ordered_events.append(MarketResearchCompletedEvent(result))
    return result


@function_tool
async def get_portfolio(
    ctx: RunContextWrapper[SentinelRunContext],
) -> Portfolio | ToolDataError:
    """Read trusted Binance Demo holdings before portfolio analysis."""
    return await read_portfolio(ctx.context)


@function_tool
async def get_market_data(
    ctx: RunContextWrapper[SentinelRunContext],
    symbol: str,
) -> MarketData | ToolDataError | ToolDataNotRequired:
    """Read trusted Binance Demo market data for a pair such as BTCUSDT."""
    return await read_market_data(ctx.context, symbol)


@function_tool
async def update_policy(
    ctx: RunContextWrapper[SentinelRunContext],
    changes: list[PolicyToolChange],
) -> PortfolioPolicy:
    """Stage explicit changes; send each value as decimal/true/false/null text."""
    return stage_policy_update(ctx.context, parse_policy_tool_changes(changes))


@function_tool
async def view_policy(
    ctx: RunContextWrapper[SentinelRunContext],
) -> PortfolioPolicy:
    """Read the current validated working portfolio policy."""
    return view_working_policy(ctx.context)


@function_tool
async def update_investor_profile(
    ctx: RunContextWrapper[SentinelRunContext],
    changes: list[ProfileToolChange],
) -> InvestorProfile:
    """Stage explicit investor preferences using simple string values."""
    return stage_profile_update(
        ctx.context,
        parse_profile_tool_changes(changes),
    )


@function_tool
async def view_investor_profile(
    ctx: RunContextWrapper[SentinelRunContext],
) -> InvestorProfile:
    """Read the current validated investor profile."""
    return view_working_profile(ctx.context)


@function_tool
async def evaluate_portfolio_risk(
    ctx: RunContextWrapper[SentinelRunContext],
    focus_symbols: list[str],
) -> PortfolioAnalysis | MissingObservations | ToolDataError:
    """Run deterministic policy, planning, and risk checks on cached observations."""
    return evaluate_cached_portfolio(ctx.context, focus_symbols)


@function_tool
async def propose_trade(
    ctx: RunContextWrapper[SentinelRunContext],
    symbol: str,
    side: Literal["BUY", "SELL"],
    quote_usd: str,
    reason: str,
) -> ExecutionPlan | MissingObservations | ToolDataError:
    """Create a Demo Spot proposal for explicit approval; never executes it."""
    return await propose_trade_plan(
        ctx.context,
        symbol=symbol,
        side=side,
        quote_usd=quote_usd,
        reason=reason,
    )


@function_tool
async def set_market_research_plan(
    ctx: RunContextWrapper[SentinelRunContext],
    candidate_limit: int,
    timeframes: list[ResearchTimeframe],
    lookback_days: int,
    priorities: list[ResearchPriority],
) -> MarketResearchPlan:
    """Set a bounded Binance market-research recipe for this Agent run."""
    return stage_market_research_plan(
        ctx.context,
        MarketResearchPlan(
            candidate_limit=candidate_limit,
            timeframes=timeframes,
            lookback_days=lookback_days,
            priorities=priorities,
        ),
    )


@function_tool
async def scan_top_markets(
    ctx: RunContextWrapper[SentinelRunContext],
) -> MarketScan | ToolDataError:
    """Scan active Binance Spot USDT markets and rank them by quote volume."""
    return await scan_market_candidates(ctx.context)


@function_tool
async def analyze_market_history(
    ctx: RunContextWrapper[SentinelRunContext],
    symbol: str,
) -> CandidateResearch | ToolDataError:
    """Calculate verified indicators for one candidate from the current scan."""
    return await analyze_market_candidate(ctx.context, symbol)


@function_tool(name_override="finalize_market_research")
async def finalize_market_research_tool(
    ctx: RunContextWrapper[SentinelRunContext],
) -> MarketResearchResult | ToolDataError:
    """Finalize at least two verified candidate analyses for LLM comparison."""
    return finalize_market_research(ctx.context)


CONTROLLED_TOOLS: list[FunctionTool] = [
    get_portfolio,
    get_market_data,
    update_policy,
    view_policy,
    update_investor_profile,
    view_investor_profile,
    evaluate_portfolio_risk,
    propose_trade,
    set_market_research_plan,
    scan_top_markets,
    analyze_market_history,
    finalize_market_research_tool,
]
