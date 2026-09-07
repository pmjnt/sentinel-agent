from dataclasses import dataclass, field

from app.gateways import PortfolioMarketGateway
from app.models.analysis import PortfolioAnalysis
from app.models.market import MarketData
from app.models.execution import ExecutionPlan
from app.models.profile import InvestorProfile, InvestorProfilePatch
from app.models.policy import PolicyPatch, PortfolioPolicy
from app.models.portfolio import Portfolio
from app.models.research import (
    CandidateResearch,
    MarketResearchPlan,
    MarketResearchResult,
    MarketScan,
)


@dataclass(frozen=True)
class PolicyUpdatedEvent:
    patch: PolicyPatch
    policy: PortfolioPolicy


@dataclass(frozen=True)
class PolicyViewedEvent:
    policy: PortfolioPolicy


@dataclass(frozen=True)
class AnalysisCompletedEvent:
    analysis: PortfolioAnalysis


@dataclass(frozen=True)
class ProfileUpdatedEvent:
    patch: InvestorProfilePatch
    profile: InvestorProfile


@dataclass(frozen=True)
class ProfileViewedEvent:
    profile: InvestorProfile


@dataclass(frozen=True)
class TradeProposedEvent:
    plan: ExecutionPlan


@dataclass(frozen=True)
class ResearchPlanSetEvent:
    plan: MarketResearchPlan


@dataclass(frozen=True)
class MarketScanCompletedEvent:
    scan: MarketScan


@dataclass(frozen=True)
class MarketCandidateAnalyzedEvent:
    research: CandidateResearch


@dataclass(frozen=True)
class MarketResearchCompletedEvent:
    result: MarketResearchResult


SentinelRunEvent = (
    PolicyUpdatedEvent
    | PolicyViewedEvent
    | ProfileUpdatedEvent
    | ProfileViewedEvent
    | AnalysisCompletedEvent
    | TradeProposedEvent
    | ResearchPlanSetEvent
    | MarketScanCompletedEvent
    | MarketCandidateAnalyzedEvent
    | MarketResearchCompletedEvent
)


@dataclass
class SentinelRunContext:
    """Trusted mutable state scoped to one Agent run."""

    gateway: PortfolioMarketGateway
    starting_policy: PortfolioPolicy
    working_policy: PortfolioPolicy
    starting_profile: InvestorProfile
    working_profile: InvestorProfile
    policy_patches: list[PolicyPatch] = field(default_factory=list)
    profile_patches: list[InvestorProfilePatch] = field(default_factory=list)
    ordered_events: list[SentinelRunEvent] = field(default_factory=list)
    portfolio: Portfolio | None = None
    market_by_symbol: dict[str, MarketData] = field(default_factory=dict)
    data_errors: list[str] = field(default_factory=list)
    analyses: list[PortfolioAnalysis] = field(default_factory=list)
    execution_plans: list[ExecutionPlan] = field(default_factory=list)
    research_plan: MarketResearchPlan | None = None
    market_scan: MarketScan | None = None
    research_by_symbol: dict[str, CandidateResearch] = field(default_factory=dict)
    research_failed_symbols: list[str] = field(default_factory=list)
    market_research_results: list[MarketResearchResult] = field(default_factory=list)
    session_id: str = "default"

    @classmethod
    def create(
        cls,
        gateway: PortfolioMarketGateway,
        policy: PortfolioPolicy,
        profile: InvestorProfile | None = None,
        session_id: str = "default",
    ) -> "SentinelRunContext":
        return cls(
            gateway=gateway,
            starting_policy=policy,
            working_policy=policy,
            starting_profile=profile or InvestorProfile(),
            working_profile=profile or InvestorProfile(),
            session_id=session_id,
        )
