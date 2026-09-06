from collections.abc import Callable

from app.execution.store import InMemoryExecutionPlanStore, PlanStateError
from app.gateways import DemoExecutionGateway
from app.models.execution import ExecutionPlan, ExecutionPlanStatus
from app.models.market import MarketData, MarketDataError
from app.models.policy import PortfolioPolicy
from app.services.trade_proposal_service import TradeProposalError, create_trade_plan


class ExecutionBlockedError(RuntimeError):
    pass


class DemoExecutionService:
    """Approve, revalidate, execute, and verify one immutable Demo plan."""

    def __init__(
        self,
        *,
        gateway: DemoExecutionGateway,
        plans: InMemoryExecutionPlanStore,
        policy_loader: Callable[[str], PortfolioPolicy],
        enabled: bool,
    ) -> None:
        self._gateway = gateway
        self._plans = plans
        self._policy_loader = policy_loader
        self._enabled = enabled

    async def approve_and_execute(
        self, session_id: str, plan_id: str
    ) -> ExecutionPlan:
        existing = self._plans.get(session_id, plan_id)
        if existing.status is ExecutionPlanStatus.EXECUTED:
            return existing
        if not self._enabled:
            raise ExecutionBlockedError("Binance Demo execution is disabled.")

        try:
            approved = self._plans.approve(session_id, plan_id)
        except PlanStateError as error:
            raise ExecutionBlockedError(str(error)) from error

        client_order_id = _client_order_id(approved.plan_id)
        try:
            portfolio = await self._gateway.get_portfolio()
            market_result = await self._gateway.get_market_data(approved.symbol)
            if isinstance(market_result, MarketDataError):
                raise ExecutionBlockedError("Fresh market data could not be verified.")
            market: MarketData = market_result
            create_trade_plan(
                session_id=session_id,
                symbol=approved.symbol,
                side=approved.side,
                quote_usd=approved.quote_usd,
                reason=approved.reason,
                policy=self._policy_loader(session_id),
                portfolio=portfolio,
                market=market,
            )
            self._plans.start_execution(session_id, plan_id)
        except (TradeProposalError, ValueError, RuntimeError) as error:
            self._plans.fail_execution(session_id, plan_id, str(error))
            raise ExecutionBlockedError(str(error)) from error

        try:
            await self._gateway.submit_market_order(
                symbol=approved.symbol,
                side=approved.side,
                quote_usd=approved.quote_usd,
                client_order_id=client_order_id,
            )
            confirmed = await self._gateway.get_order(
                approved.symbol,
                client_order_id,
            )
        except RuntimeError:
            try:
                confirmed = await self._gateway.get_order(
                    approved.symbol,
                    client_order_id,
                )
            except RuntimeError as verify_error:
                self._plans.fail_execution(
                    session_id,
                    plan_id,
                    "Binance Demo order status could not be verified.",
                )
                raise ExecutionBlockedError(
                    "Binance Demo order status could not be verified."
                ) from verify_error

        if confirmed.status != "FILLED":
            reason = f"Binance Demo order is {confirmed.status}, not FILLED."
            self._plans.fail_execution(session_id, plan_id, reason)
            raise ExecutionBlockedError(reason)

        executed = self._plans.finish_execution(
            session_id,
            plan_id,
            order_id=confirmed.order_id,
            order_status=confirmed.status,
        )
        await self._gateway.get_portfolio()
        return executed

    def reject(self, session_id: str, plan_id: str) -> ExecutionPlan:
        try:
            return self._plans.reject(session_id, plan_id)
        except PlanStateError as error:
            raise ExecutionBlockedError(str(error)) from error


def _client_order_id(plan_id: str) -> str:
    return "SNTL-" + plan_id.removeprefix("PLAN-")
