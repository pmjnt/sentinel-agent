import asyncio
from decimal import Decimal

import pytest

from app.agent.run_context import (
    AnalysisCompletedEvent,
    PolicyUpdatedEvent,
    ProfileUpdatedEvent,
    TradeProposedEvent,
)
from app.agent.tool_loop import ToolLoopResult
from app.agent.tool_loop import ToolLoopStreamCompleted
from app.application import SentinelApplication
from app.execution.store import InMemoryExecutionPlanStore
from app.models.execution import ExecutionPlan, ExecutionPlanStatus
from app.models.api import (
    ActivityEvent,
    ActivityKind,
    ActivityStatus,
    StructuredSentinelResponse,
    TextDeltaEvent,
)
from app.models.analysis import PortfolioAnalysis
from app.models.profile import InvestmentObjective, InvestorProfile, InvestorProfilePatch
from app.models.policy import PolicyPatch, PortfolioPolicy
from app.models.portfolio import Portfolio
from app.models.risk import RiskDecision, RiskReasonCode, RiskStatus
from app.models.trade import PlanStatus, RebalancePlan
from app.models.trade import TradeSide
from datetime import UTC, datetime, timedelta
from app.model_catalog import ModelRoute
from app.config import LLMProvider
from app.sessions import InMemoryInvestorProfileSessionStore, InMemoryPolicySessionStore


def _analysis(policy: PortfolioPolicy) -> PortfolioAnalysis:
    return PortfolioAnalysis(
        policy=policy,
        portfolio=Portfolio(assets=[], total_usd_value=Decimal("0")),
        violations=[],
        market_data=[],
        plan=RebalancePlan(
            violations=[],
            actions=[],
            status=PlanStatus.SAFE_TO_PROPOSE,
            explanation="No action required.",
        ),
        risk_decision=RiskDecision(
            status=RiskStatus.SAFE_TO_PROPOSE,
            reason_codes=[RiskReasonCode.NO_RESTRICTION_TRIGGERED],
            reasons=["No restriction triggered."],
        ),
    )


class FakeToolLoop:
    def __init__(
        self,
        result: ToolLoopResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[str, str, PortfolioPolicy, InvestorProfile]] = []

    async def run(
        self,
        message: str,
        policy: PortfolioPolicy,
        session_id: str = "default",
        profile: InvestorProfile | None = None,
    ) -> ToolLoopResult:
        self.calls.append((session_id, message, policy, profile or InvestorProfile()))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    async def stream(self, *args, **kwargs):
        yield ActivityEvent(
            sequence=1,
            kind=ActivityKind.PORTFOLIO_READ,
            status=ActivityStatus.COMPLETED,
            message="Completed portfolio retrieval.",
        )
        assert self.result is not None
        yield ToolLoopStreamCompleted(self.result)


def _result(
    *,
    final_text: str,
    policy: PortfolioPolicy | None = None,
    patches: tuple[PolicyPatch, ...] = (),
    events: tuple = (),
    analyses: tuple[PortfolioAnalysis, ...] = (),
    data_errors: tuple[str, ...] = (),
    profile: InvestorProfile | None = None,
    profile_patches: tuple[InvestorProfilePatch, ...] = (),
    execution_plans: tuple[ExecutionPlan, ...] = (),
) -> ToolLoopResult:
    return ToolLoopResult(
        final_text=final_text,
        events=events,
        policy_patches=patches,
        final_policy=policy or PortfolioPolicy(),
        analyses=analyses,
        data_errors=data_errors,
        profile_patches=profile_patches,
        final_profile=profile or InvestorProfile(),
        execution_plans=execution_plans,
    )


def _execution_plan() -> ExecutionPlan:
    now = datetime.now(UTC)
    return ExecutionPlan(
        plan_id="PLAN-ABC123",
        session_id="user-1",
        symbol="BTCUSDT",
        side=TradeSide.BUY,
        quote_usd="50",
        estimated_quantity="0.0005",
        estimated_price="100000",
        reason="Controlled growth exposure.",
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def test_general_chat_uses_agent_text_without_policy_change() -> None:
    store = InMemoryPolicySessionStore()
    loop = FakeToolLoop(_result(final_text="Xin chào!"))
    application = SentinelApplication(loop, store)

    response = asyncio.run(application.handle("user-1", "xin chào"))

    assert response.message == "Xin chào!"
    assert response.policy == PortfolioPolicy()
    assert response.analysis is None
    assert loop.calls == [
        ("user-1", "xin chào", PortfolioPolicy(), InvestorProfile())
    ]


def test_application_passes_selected_model_route_to_agent_loop() -> None:
    route = ModelRoute(LLMProvider.GEMINI, "gemini-3.5-flash-lite")

    class RouteCapturingLoop(FakeToolLoop):
        selected_route: ModelRoute | None = None

        async def run(self, *args, model_route=None, **kwargs):
            self.selected_route = model_route
            return await super().run(*args, **kwargs)

    loop = RouteCapturingLoop(_result(final_text="Hello."))
    application = SentinelApplication(loop, InMemoryPolicySessionStore())

    asyncio.run(application.handle("user-1", "hello", model_route=route))

    assert loop.selected_route == route


def test_staged_investor_profile_commits_after_successful_run() -> None:
    profile_store = InMemoryInvestorProfileSessionStore()
    patch = InvestorProfilePatch(objective=InvestmentObjective.GROWTH)
    profile = InvestorProfile(objective=InvestmentObjective.GROWTH)
    loop = FakeToolLoop(
        _result(
            final_text="Profile handled.",
            profile=profile,
            profile_patches=(patch,),
            events=(ProfileUpdatedEvent(patch, profile),),
        )
    )
    application = SentinelApplication(
        loop,
        InMemoryPolicySessionStore(),
        profile_store,
    )

    response = asyncio.run(
        application.handle("user-1", "I want long-term growth.")
    )

    assert response.profile == profile
    assert profile_store.get("user-1") == profile
    assert "Investor profile updated" in response.message


def test_application_stream_finishes_with_structured_snapshot() -> None:
    analysis = _analysis(PortfolioPolicy())
    loop = FakeToolLoop(
        _result(
            final_text="Assessment: Low volatility.",
            events=(AnalysisCompletedEvent(analysis),),
            analyses=(analysis,),
        )
    )
    application = SentinelApplication(loop, InMemoryPolicySessionStore())

    route = ModelRoute(LLMProvider.OPENAI, "gpt-5.4-mini")

    async def collect():
        return [
            event
            async for event in application.stream_handle(
                "user-1",
                "Analyze.",
                model_route=route,
            )
        ]

    events = asyncio.run(collect())

    assert isinstance(events[0], ActivityEvent)
    assert any(isinstance(event, TextDeltaEvent) for event in events)
    assert isinstance(events[-1], StructuredSentinelResponse)
    assert events[-1].analysis == analysis
    assert events[-1].activity == [events[0]]
    assert events[-1].execution_status.value == "NOT_EXECUTED"
    assert events[-1].provider == "openai"
    assert events[-1].model == "gpt-5.4-mini"


def test_application_commits_pending_execution_plan_after_successful_agent_run() -> None:
    plan = _execution_plan()
    plans = InMemoryExecutionPlanStore()
    application = SentinelApplication(
        FakeToolLoop(
            _result(
                final_text="Approve the proposed plan.",
                execution_plans=(plan,),
                events=(TradeProposedEvent(plan),),
            )
        ),
        InMemoryPolicySessionStore(),
        execution_plans=plans,
    )

    response = asyncio.run(application.handle("user-1", "Buy $50 BTC."))

    assert response.execution_plan == plan
    assert plans.get("user-1", plan.plan_id) == plan
    assert "Pending Binance Demo plan" in response.message
    assert "PLAN-ABC123" in response.message
    assert "No order has been sent" in response.message


def test_analysis_without_safe_llm_prose_still_returns_verified_facts() -> None:
    analysis = _analysis(PortfolioPolicy())
    loop = FakeToolLoop(
        _result(
            final_text="",
            events=(AnalysisCompletedEvent(analysis),),
            analyses=(analysis,),
        )
    )
    application = SentinelApplication(loop, InMemoryPolicySessionStore())

    response = asyncio.run(application.handle("user-1", "Analyze."))

    assert "Verified facts" in response.message
    assert "AI interpretation:" not in response.message
    assert response.ai_interpretation is None


def test_staged_policy_patch_commits_only_after_successful_run() -> None:
    store = InMemoryPolicySessionStore()
    patch = PolicyPatch(max_asset_weight=Decimal("0.40"))
    updated = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    loop = FakeToolLoop(
        _result(
            final_text="Policy handled.",
            policy=updated,
            patches=(patch,),
            events=(PolicyUpdatedEvent(patch, updated),),
        )
    )
    application = SentinelApplication(loop, store)

    response = asyncio.run(application.handle("user-1", "Giới hạn 40%."))

    assert response.policy == updated
    assert store.get("user-1") == updated
    assert "Policy updated" in response.message
    assert "40%" in response.message


def test_failed_agent_run_does_not_commit_policy() -> None:
    store = InMemoryPolicySessionStore()
    application = SentinelApplication(
        FakeToolLoop(error=RuntimeError("provider failed")),
        store,
    )

    with pytest.raises(RuntimeError, match="provider failed"):
        asyncio.run(application.handle("user-1", "Giới hạn 40%."))

    assert store.get("user-1") == PortfolioPolicy()


def test_inconsistent_loop_policy_is_rejected_before_store_mutation() -> None:
    store = InMemoryPolicySessionStore()
    patch = PolicyPatch(max_asset_weight=Decimal("0.40"))
    application = SentinelApplication(
        FakeToolLoop(
            _result(
                final_text="Invalid result.",
                policy=PortfolioPolicy(max_asset_weight=Decimal("0.50")),
                patches=(patch,),
            )
        ),
        store,
    )

    with pytest.raises(RuntimeError, match="did not match"):
        asyncio.run(application.handle("user-1", "Set 40%."))

    assert store.get("user-1") == PortfolioPolicy()


def test_analysis_renders_authoritative_facts_before_agent_judgment() -> None:
    policy = PortfolioPolicy()
    analysis = _analysis(policy)
    application = SentinelApplication(
        FakeToolLoop(
            _result(
                final_text="Portfolio concentration deserves attention.",
                policy=policy,
                events=(AnalysisCompletedEvent(analysis),),
                analyses=(analysis,),
            )
        ),
        InMemoryPolicySessionStore(),
    )

    response = asyncio.run(application.handle("user-1", "Analyze."))

    assert "Verified facts (Binance Demo)" in response.message
    assert "Total portfolio: $0.00" in response.message
    assert "Policy violations: none" in response.message
    assert "Proposed actions: none" in response.message
    assert "Risk Engine: SAFE_TO_PROPOSE" in response.message
    assert "Execution: NOT_EXECUTED" in response.message
    assert response.message.index("Risk Engine") < response.message.index(
        "AI interpretation"
    )
    assert response.message.endswith("Portfolio concentration deserves attention.")


def test_data_error_uses_safe_deterministic_message() -> None:
    application = SentinelApplication(
        FakeToolLoop(
            _result(
                final_text="Unverified recommendation.",
                data_errors=("Portfolio data could not be verified.",),
            )
        ),
        InMemoryPolicySessionStore(),
    )

    response = asyncio.run(application.handle("user-1", "Analyze."))

    assert "Required Binance Demo data could not be verified" in response.message
    assert "Portfolio data could not be verified." in response.message
    assert "Unverified recommendation" not in response.message


def test_data_error_discards_earlier_analysis_and_verified_facts() -> None:
    analysis = _analysis(PortfolioPolicy())
    application = SentinelApplication(
        FakeToolLoop(
            _result(
                final_text="",
                events=(AnalysisCompletedEvent(analysis),),
                analyses=(analysis,),
                data_errors=("Market data could not be verified for BTCUSDT.",),
            )
        ),
        InMemoryPolicySessionStore(),
    )

    response = asyncio.run(application.handle("user-1", "Give me advice."))

    assert response.analysis is None
    assert response.analyses == ()
    assert "Verified facts" not in response.message
    assert "Market data could not be verified" in response.message


def test_data_error_does_not_commit_a_staged_execution_plan() -> None:
    plan = _execution_plan()
    plans = InMemoryExecutionPlanStore()
    application = SentinelApplication(
        FakeToolLoop(
            _result(
                final_text="",
                events=(TradeProposedEvent(plan),),
                execution_plans=(plan,),
                data_errors=("Market data could not be verified.",),
            )
        ),
        InMemoryPolicySessionStore(),
        execution_plans=plans,
    )

    response = asyncio.run(application.handle("user-1", "Buy BTC."))

    assert response.execution_plan is None
    with pytest.raises(KeyError):
        plans.get("user-1", plan.plan_id)


def test_events_are_rendered_in_tool_call_order() -> None:
    old_policy = PortfolioPolicy(max_asset_weight=Decimal("0.50"))
    new_policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    patch = PolicyPatch(max_asset_weight=Decimal("0.40"))
    analysis = _analysis(old_policy)
    store = InMemoryPolicySessionStore()
    store.apply("user-1", PolicyPatch(max_asset_weight=Decimal("0.50")))
    application = SentinelApplication(
        FakeToolLoop(
            _result(
                final_text="Phân tích định tính theo policy cũ.",
                policy=new_policy,
                patches=(patch,),
                events=(
                    AnalysisCompletedEvent(analysis),
                    PolicyUpdatedEvent(patch, new_policy),
                ),
                analyses=(analysis,),
            )
        ),
        store,
    )

    response = asyncio.run(
        application.handle("user-1", "Phân tích trước rồi đổi policy.")
    )

    assert response.message.index("Risk Engine") < response.message.index(
        "Policy updated"
    )
    assert response.policy == new_policy
