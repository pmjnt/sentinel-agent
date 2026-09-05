import asyncio
from decimal import Decimal

import pytest

from app.agent.run_context import AnalysisCompletedEvent, PolicyUpdatedEvent
from app.agent.tool_loop import ToolLoopResult
from app.application import SentinelApplication
from app.models.analysis import PortfolioAnalysis
from app.models.policy import PolicyPatch, PortfolioPolicy
from app.models.portfolio import Portfolio
from app.models.risk import RiskDecision, RiskReasonCode, RiskStatus
from app.models.trade import PlanStatus, RebalancePlan
from app.sessions import InMemoryPolicySessionStore


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
        self.calls: list[tuple[str, PortfolioPolicy]] = []

    async def run(self, message: str, policy: PortfolioPolicy) -> ToolLoopResult:
        self.calls.append((message, policy))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _result(
    *,
    final_text: str,
    policy: PortfolioPolicy | None = None,
    patches: tuple[PolicyPatch, ...] = (),
    events: tuple = (),
    analyses: tuple[PortfolioAnalysis, ...] = (),
    data_errors: tuple[str, ...] = (),
) -> ToolLoopResult:
    return ToolLoopResult(
        final_text=final_text,
        events=events,
        policy_patches=patches,
        final_policy=policy or PortfolioPolicy(),
        analyses=analyses,
        data_errors=data_errors,
    )


def test_general_chat_uses_agent_text_without_policy_change() -> None:
    store = InMemoryPolicySessionStore()
    loop = FakeToolLoop(_result(final_text="Xin chào!"))
    application = SentinelApplication(loop, store)

    response = asyncio.run(application.handle("user-1", "xin chào"))

    assert response.message == "Xin chào!"
    assert response.policy == PortfolioPolicy()
    assert response.analysis is None


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
    assert "Unverified recommendation" not in response.message


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
