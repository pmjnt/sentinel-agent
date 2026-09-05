import asyncio

from app.gateways import PortfolioMarketGateway
from app.models.analysis import PortfolioAnalysis
from app.models.market import MarketData, MarketDataError
from app.models.policy import PolicyViolation, PortfolioPolicy, ViolationType
from app.models.portfolio import Portfolio
from app.models.trade import PlanStatus
from app.services.policy_service import find_policy_violations
from app.services.rebalance_service import build_rebalance_plan
from app.services.risk_service import evaluate_rebalance_risk


class AnalysisDataError(RuntimeError):
    """Raised when required external data cannot be safely verified."""


class PortfolioAnalysisService:
    """Run the authoritative, deterministic portfolio-analysis workflow."""

    def __init__(self, gateway: PortfolioMarketGateway) -> None:
        self._gateway = gateway

    async def analyze(
        self,
        policy: PortfolioPolicy,
        focus_symbols: list[str],
    ) -> PortfolioAnalysis:
        try:
            portfolio = await self._gateway.get_portfolio()
        except (RuntimeError, ValueError) as error:
            raise AnalysisDataError(
                "Portfolio data could not be verified."
            ) from error

        market_symbols = required_market_symbols(portfolio, policy, focus_symbols)
        market_results = await asyncio.gather(
            *(self._gateway.get_market_data(symbol) for symbol in market_symbols),
            return_exceptions=True,
        )

        for result in market_results:
            if isinstance(result, asyncio.CancelledError):
                raise result

        if any(
            isinstance(result, (MarketDataError, Exception))
            for result in market_results
        ):
            raise AnalysisDataError(
                "Required market data could not be verified."
            )

        market_by_symbol = {
            result.symbol: result
            for result in market_results
            if isinstance(result, MarketData)
        }
        return evaluate_portfolio_observations(
            policy,
            portfolio,
            market_by_symbol,
        )


def required_market_symbols(
    portfolio: Portfolio,
    policy: PortfolioPolicy,
    focus_symbols: list[str],
) -> list[str]:
    """Return normalized markets required by focus and policy violations."""
    violations = find_policy_violations(portfolio, policy)
    return _required_market_symbols(focus_symbols, violations)


def evaluate_portfolio_observations(
    policy: PortfolioPolicy,
    portfolio: Portfolio,
    market_by_symbol: dict[str, MarketData],
) -> PortfolioAnalysis:
    """Evaluate only trusted observations already retrieved from a gateway."""
    normalized_market = {
        symbol.strip().upper(): market
        for symbol, market in market_by_symbol.items()
    }
    violations = find_policy_violations(portfolio, policy)
    required_symbols = _required_market_symbols([], violations)
    if any(symbol not in normalized_market for symbol in required_symbols):
        raise AnalysisDataError("Required market data could not be verified.")

    plan = build_rebalance_plan(portfolio, violations, normalized_market)
    risk_decision = evaluate_rebalance_risk(policy, plan, normalized_market)
    plan = plan.model_copy(
        update={"status": PlanStatus(risk_decision.status.value)}
    )
    return PortfolioAnalysis(
        policy=policy,
        portfolio=portfolio,
        violations=violations,
        market_data=list(normalized_market.values()),
        plan=plan,
        risk_decision=risk_decision,
    )


def _required_market_symbols(
    focus_symbols: list[str],
    violations: list[PolicyViolation],
) -> list[str]:
    requested: dict[str, None] = {}

    for symbol in focus_symbols:
        market_symbol = _to_usdt_market(symbol)
        if market_symbol is not None:
            requested[market_symbol] = None

    for violation in violations:
        if (
            violation.type is ViolationType.MAX_ASSET_WEIGHT
            and violation.asset is not None
        ):
            market_symbol = _to_usdt_market(violation.asset)
            if market_symbol is not None:
                requested[market_symbol] = None

    return list(requested)


def _to_usdt_market(symbol: str) -> str | None:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Market focus symbol must not be empty.")
    if normalized == "USDT":
        return None
    if normalized.endswith("USDT"):
        return normalized
    return f"{normalized}USDT"
