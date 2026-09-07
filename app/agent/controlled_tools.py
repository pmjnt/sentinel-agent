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
from app.models.trade import TradeSide
from app.services.policy_service import apply_policy_patch
from app.services.profile_service import apply_profile_patch
from app.services.portfolio_analysis_service import (
    AnalysisDataError,
    evaluate_portfolio_observations,
    required_market_symbols,
)
from app.services.trade_proposal_service import TradeProposalError, create_trade_plan


MAX_MARKET_OBSERVATIONS = 20


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
        result = MarketDataError(symbol=normalized, error="gateway failure")

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


def propose_trade_plan(
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
        )
    except (InvalidOperation, ValueError, TradeProposalError) as error:
        return ToolDataError(code="PROPOSAL_REJECTED", message=str(error))

    context.execution_plans.append(plan)
    context.ordered_events.append(TradeProposedEvent(plan))
    return plan


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
    return propose_trade_plan(
        ctx.context,
        symbol=symbol,
        side=side,
        quote_usd=quote_usd,
        reason=reason,
    )


CONTROLLED_TOOLS: list[FunctionTool] = [
    get_portfolio,
    get_market_data,
    update_policy,
    view_policy,
    update_investor_profile,
    view_investor_profile,
    evaluate_portfolio_risk,
    propose_trade,
]
