from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.models.execution import ExecutionPlan
from app.models.market import MarketData
from app.models.policy import PortfolioPolicy
from app.models.portfolio import Portfolio, PortfolioAsset
from app.models.risk import RiskStatus
from app.models.trade import RebalancePlan, TradeAction, TradeSide
from app.services.policy_service import find_policy_violations
from app.services.portfolio_service import calculate_portfolio
from app.services.risk_service import evaluate_rebalance_risk


HARD_ALLOWED_SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT"})
HARD_MIN_TRADE_USD = Decimal("10")
HARD_MAX_TRADE_USD = Decimal("100")
PLAN_LIFETIME = timedelta(minutes=5)


class TradeProposalError(ValueError):
    pass


def create_trade_plan(
    *,
    session_id: str,
    symbol: str,
    side: TradeSide,
    quote_usd: Decimal,
    reason: str,
    policy: PortfolioPolicy,
    portfolio: Portfolio,
    market: MarketData,
) -> ExecutionPlan:
    normalized = symbol.strip().upper()
    if normalized not in HARD_ALLOWED_SYMBOLS:
        raise TradeProposalError("Trading symbol is outside the hard allowlist.")
    if market.symbol != normalized:
        raise TradeProposalError("Fresh market data does not match the proposal.")
    if quote_usd < HARD_MIN_TRADE_USD or quote_usd > HARD_MAX_TRADE_USD:
        raise TradeProposalError("Trade value is outside the hard Demo limits.")
    if quote_usd != quote_usd.quantize(Decimal("0.01")):
        raise TradeProposalError("Trade value supports at most two decimal places.")
    if policy.max_trade_usd is not None and quote_usd > policy.max_trade_usd:
        raise TradeProposalError("Trade value exceeds the policy maximum.")
    if (
        policy.allowed_trade_symbols is not None
        and normalized not in policy.allowed_trade_symbols
    ):
        raise TradeProposalError("Trading symbol is not allowed by policy.")
    if (
        policy.max_slippage_percent is not None
        and market.estimated_slippage_percent > policy.max_slippage_percent
    ):
        raise TradeProposalError("Estimated slippage exceeds policy maximum.")

    base_symbol = normalized.removesuffix("USDT")
    balances = {asset.symbol: asset.amount for asset in portfolio.assets}
    estimated_quantity = quote_usd / market.price
    if side is TradeSide.BUY and balances.get("USDT", Decimal("0")) < quote_usd:
        raise TradeProposalError("Insufficient USDT balance.")
    if side is TradeSide.SELL and balances.get(base_symbol, Decimal("0")) < estimated_quantity:
        raise TradeProposalError(f"Insufficient {base_symbol} balance.")

    projected = _project_portfolio(
        portfolio,
        base_symbol=base_symbol,
        side=side,
        quote_usd=quote_usd,
        quantity=estimated_quantity,
    )
    if _introduces_or_worsens_violation(portfolio, projected, policy):
        raise TradeProposalError(
            "Proposed trade would create or worsen a portfolio policy violation."
        )

    risk_decision = evaluate_rebalance_risk(
        policy,
        RebalancePlan(
            actions=[
                TradeAction(
                    symbol=normalized,
                    side=side,
                    amount=estimated_quantity,
                    estimated_usd_value=quote_usd,
                    reason=reason,
                )
            ],
            explanation="User-requested Binance Demo Spot proposal.",
        ),
        {normalized: market},
    )
    if risk_decision.status is RiskStatus.BLOCKED:
        raise TradeProposalError(
            "Policy blocks Demo trading during HIGH volatility."
        )

    now = datetime.now(UTC)
    return ExecutionPlan(
        plan_id=f"PLAN-{uuid4().hex[:10].upper()}",
        session_id=session_id,
        symbol=normalized,
        side=side,
        quote_usd=quote_usd,
        estimated_quantity=estimated_quantity,
        estimated_price=market.price,
        reason=reason.strip(),
        created_at=now,
        expires_at=now + PLAN_LIFETIME,
    )


def _project_portfolio(
    portfolio: Portfolio,
    *,
    base_symbol: str,
    side: TradeSide,
    quote_usd: Decimal,
    quantity: Decimal,
) -> Portfolio:
    direction = Decimal("1") if side is TradeSide.BUY else Decimal("-1")
    assets = {asset.symbol: asset for asset in portfolio.assets}
    base = assets.get(
        base_symbol,
        PortfolioAsset(symbol=base_symbol, amount=Decimal("0"), usd_value=Decimal("0")),
    )
    usdt = assets.get(
        "USDT",
        PortfolioAsset(symbol="USDT", amount=Decimal("0"), usd_value=Decimal("0")),
    )
    assets[base_symbol] = base.model_copy(
        update={
            "amount": base.amount + direction * quantity,
            "usd_value": base.usd_value + direction * quote_usd,
        }
    )
    assets["USDT"] = usdt.model_copy(
        update={
            "amount": usdt.amount - direction * quote_usd,
            "usd_value": usdt.usd_value - direction * quote_usd,
        }
    )
    return calculate_portfolio(list(assets.values()), portfolio.data_source)


def _introduces_or_worsens_violation(
    before: Portfolio,
    after: Portfolio,
    policy: PortfolioPolicy,
) -> bool:
    existing = {
        (violation.type, violation.asset): abs(
            violation.current_value - violation.allowed_value
        )
        for violation in find_policy_violations(before, policy)
    }
    return any(
        abs(violation.current_value - violation.allowed_value)
        > existing.get((violation.type, violation.asset), Decimal("0"))
        for violation in find_policy_violations(after, policy)
    )
