from dataclasses import dataclass, field

from app.gateways import PortfolioMarketGateway
from app.models.analysis import PortfolioAnalysis
from app.models.market import MarketData
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


SentinelRunEvent = PolicyUpdatedEvent | PolicyViewedEvent | AnalysisCompletedEvent


@dataclass
class SentinelRunContext:
    """Trusted mutable state scoped to one Agent run."""

    gateway: PortfolioMarketGateway
    starting_policy: PortfolioPolicy
    working_policy: PortfolioPolicy
    policy_patches: list[PolicyPatch] = field(default_factory=list)
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
    ) -> "SentinelRunContext":
        return cls(
            gateway=gateway,
            starting_policy=policy,
            working_policy=policy,
        )
