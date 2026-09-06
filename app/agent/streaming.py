from dataclasses import dataclass, field
from typing import Any

from app.models.api import ActivityEvent, ActivityKind, ActivityStatus


_TOOL_ACTIVITY: dict[str, tuple[ActivityKind, str]] = {
    "get_portfolio": (ActivityKind.PORTFOLIO_READ, "portfolio retrieval"),
    "get_market_data": (ActivityKind.MARKET_DATA_READ, "market data retrieval"),
    "update_policy": (ActivityKind.POLICY_UPDATE, "policy update"),
    "view_policy": (ActivityKind.POLICY_VIEW, "policy review"),
    "update_investor_profile": (
        ActivityKind.PROFILE_UPDATE,
        "investor profile update",
    ),
    "view_investor_profile": (
        ActivityKind.PROFILE_VIEW,
        "investor profile review",
    ),
    "evaluate_portfolio_risk": (
        ActivityKind.RISK_EVALUATION,
        "deterministic risk evaluation",
    ),
    "propose_trade": (
        ActivityKind.TRADE_PROPOSAL,
        "Demo trade proposal",
    ),
}


@dataclass
class ToolActivityTracker:
    """Convert safe SDK semantic events into public progress events."""

    sequence: int = 0
    calls: dict[str, tuple[ActivityKind, str]] = field(default_factory=dict)

    def consume(self, event: Any) -> ActivityEvent | None:
        if getattr(event, "type", None) != "run_item_stream_event":
            return None
        if event.name == "tool_called":
            return self._started(event.item)
        if event.name == "tool_output":
            return self._completed(event.item)
        return None

    def _started(self, item: Any) -> ActivityEvent | None:
        tool_name = getattr(item, "tool_name", None)
        activity = _TOOL_ACTIVITY.get(tool_name)
        call_id = getattr(item, "call_id", None)
        if activity is None or call_id is None:
            return None
        self.calls[str(call_id)] = activity
        return self._event(*activity, ActivityStatus.STARTED)

    def _completed(self, item: Any) -> ActivityEvent | None:
        call_id = getattr(item, "call_id", None)
        activity = self.calls.pop(str(call_id), None)
        if activity is None:
            return None
        status = (
            ActivityStatus.FAILED
            if getattr(getattr(item, "output", None), "status", None) == "ERROR"
            else ActivityStatus.COMPLETED
        )
        return self._event(*activity, status)

    def _event(
        self,
        kind: ActivityKind,
        label: str,
        status: ActivityStatus,
    ) -> ActivityEvent:
        self.sequence += 1
        verb = {
            ActivityStatus.STARTED: "Started",
            ActivityStatus.COMPLETED: "Completed",
            ActivityStatus.FAILED: "Failed",
        }[status]
        return ActivityEvent(
            sequence=self.sequence,
            kind=kind,
            status=status,
            message=f"{verb} {label}.",
        )
