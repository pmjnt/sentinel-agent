import asyncio
from decimal import Decimal, InvalidOperation
from typing import Literal

from agents import FunctionTool, RunContextWrapper, function_tool
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.run_context import (
    AnalysisCompletedEvent,
    PolicyUpdatedEvent,
    PolicyViewedEvent,
    SentinelRunContext,
)
from app.models.analysis import PortfolioAnalysis
from app.models.market import MarketData, MarketDataError
from app.models.policy import PolicyChange, PolicyField, PolicyPatch, PortfolioPolicy
from app.models.portfolio import Portfolio
from app.services.policy_service import apply_policy_patch
from app.services.portfolio_analysis_service import (
    AnalysisDataError,
    evaluate_portfolio_observations,
    required_market_symbols,
)


class ToolDataError(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ERROR"] = "ERROR"
    code: str
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


async def read_market_data(
    context: SentinelRunContext,
    symbol: str,
) -> MarketData | ToolDataError:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Market symbol must not be empty.")

    try:
        result = await context.gateway.get_market_data(normalized)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, ValueError):
        result = MarketDataError(symbol=normalized, error="gateway failure")

    if isinstance(result, MarketDataError):
        message = f"Market data could not be verified for {normalized}."
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


def evaluate_cached_portfolio(
    context: SentinelRunContext,
    focus_symbols: list[str],
) -> PortfolioAnalysis | MissingObservations:
    if context.portfolio is None:
        return MissingObservations(required_tools=["get_portfolio"])

    required_symbols = required_market_symbols(
        context.portfolio,
        context.working_policy,
        focus_symbols,
    )
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
) -> MarketData | ToolDataError:
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
async def evaluate_portfolio_risk(
    ctx: RunContextWrapper[SentinelRunContext],
    focus_symbols: list[str],
) -> PortfolioAnalysis | MissingObservations:
    """Run deterministic policy, planning, and risk checks on cached observations."""
    return evaluate_cached_portfolio(ctx.context, focus_symbols)


CONTROLLED_TOOLS: list[FunctionTool] = [
    get_portfolio,
    get_market_data,
    update_policy,
    view_policy,
    evaluate_portfolio_risk,
]
