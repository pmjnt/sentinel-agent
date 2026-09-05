from types import SimpleNamespace
import asyncio

from app.agent.streaming import ToolActivityTracker
from app.agent.tool_loop import SentinelToolLoop, ToolLoopStreamCompleted
from app.models.api import ActivityKind, ActivityStatus
from app.models.policy import PortfolioPolicy
from tests.unit.test_tool_loop import FakeGateway, _settings


def _event(name: str, item) -> SimpleNamespace:
    return SimpleNamespace(
        type="run_item_stream_event",
        name=name,
        item=item,
    )


def test_tracker_maps_allowlisted_tool_call_and_output_without_raw_data() -> None:
    tracker = ToolActivityTracker()
    started = tracker.consume(
        _event(
            "tool_called",
            SimpleNamespace(tool_name="get_portfolio", call_id="call-1"),
        )
    )
    completed = tracker.consume(
        _event(
            "tool_output",
            SimpleNamespace(
                call_id="call-1",
                output={"api_key": "secret", "total": "9999"},
            ),
        )
    )

    assert started.kind is ActivityKind.PORTFOLIO_READ
    assert started.status is ActivityStatus.STARTED
    assert completed.status is ActivityStatus.COMPLETED
    assert completed.sequence == 2
    assert "secret" not in completed.message
    assert "9999" not in completed.message


def test_tracker_ignores_unknown_tools() -> None:
    tracker = ToolActivityTracker()

    event = tracker.consume(
        _event(
            "tool_called",
            SimpleNamespace(tool_name="place_order", call_id="call-2"),
        )
    )

    assert event is None


def test_tool_loop_stream_emits_activity_and_validated_completion() -> None:
    class FakeStreamResult:
        final_output = "Hello from Sentinel."

        async def stream_events(self):
            yield _event(
                "tool_called",
                SimpleNamespace(tool_name="view_policy", call_id="call-1"),
            )
            yield _event(
                "tool_output",
                SimpleNamespace(call_id="call-1", output=PortfolioPolicy()),
            )

    loop = SentinelToolLoop(
        _settings(),
        FakeGateway(),
        run_streamed_agent=lambda *args, **kwargs: FakeStreamResult(),
    )

    async def collect():
        return [
            event
            async for event in loop.stream(
                "Show policy.",
                PortfolioPolicy(),
                "user-1",
            )
        ]

    events = asyncio.run(collect())

    assert [event.status for event in events[:-1]] == [
        ActivityStatus.STARTED,
        ActivityStatus.COMPLETED,
    ]
    assert isinstance(events[-1], ToolLoopStreamCompleted)
    assert events[-1].result.final_text == "Hello from Sentinel."
