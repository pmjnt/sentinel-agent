from dataclasses import dataclass, field

from app.gateways import PortfolioMarketGateway
from app.models.analysis import PortfolioAnalysis
from app.models.market import MarketData
from app.models.profile import InvestorProfile, InvestorProfilePatch
from app.models.policy import PolicyPatch, PortfolioPolicy
from app.models.portfolio import Portfolio


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


SentinelRunEvent = (
    PolicyUpdatedEvent
    | PolicyViewedEvent
    | ProfileUpdatedEvent
    | ProfileViewedEvent
    | AnalysisCompletedEvent
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

    @classmethod
    def create(
        cls,
        gateway: PortfolioMarketGateway,
        policy: PortfolioPolicy,
        profile: InvestorProfile | None = None,
    ) -> "SentinelRunContext":
        return cls(
            gateway=gateway,
            starting_policy=policy,
            working_policy=policy,
            starting_profile=profile or InvestorProfile(),
            working_profile=profile or InvestorProfile(),
        )
