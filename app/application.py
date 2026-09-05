from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.models.analysis import PortfolioAnalysis
from app.models.policy import PortfolioPolicy
from app.services.analysis_response_service import format_authoritative_analysis
from app.services.policy_conversation_service import (
    PolicyConversationResult,
    PolicyMessageEvent,
    PortfolioAnalysisEvent,
)
from app.services.portfolio_analysis_service import AnalysisDataError


class ConversationHandler(Protocol):
    async def handle(
        self,
        session_id: str,
        message: str,
    ) -> PolicyConversationResult: ...


class AnalysisService(Protocol):
    async def analyze(
        self,
        policy: PortfolioPolicy,
        focus_symbols: list[str],
    ) -> PortfolioAnalysis: ...


class AnalysisReporter(Protocol):
    async def report(
        self,
        message: str,
        analysis: PortfolioAnalysis,
    ) -> str: ...


class SentinelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    policy: PortfolioPolicy
    analyses: tuple[PortfolioAnalysis, ...] = ()

    @property
    def analysis(self) -> PortfolioAnalysis | None:
        """Convenience access to the latest successful analysis, if any."""
        return self.analyses[-1] if self.analyses else None


class SentinelApplication:
    """Coordinate conversation, deterministic analysis, and explanation."""

    def __init__(
        self,
        conversation: ConversationHandler,
        analysis_service: AnalysisService,
        reporter: AnalysisReporter,
    ) -> None:
        self._conversation = conversation
        self._analysis_service = analysis_service
        self._reporter = reporter

    async def handle(self, session_id: str, message: str) -> SentinelResponse:
        conversation_result = await self._conversation.handle(session_id, message)
        response_parts: list[str] = []
        analyses: list[PortfolioAnalysis] = []

        for event in conversation_result.events:
            if isinstance(event, PolicyMessageEvent):
                response_parts.append(event.message)
                continue

            if isinstance(event, PortfolioAnalysisEvent):
                try:
                    analysis = await self._analysis_service.analyze(
                        event.policy,
                        list(event.focus_symbols),
                    )
                except AnalysisDataError:
                    response_parts.append(
                        "Dữ liệu Binance Demo cần thiết không thể được xác minh. "
                        "Sentinel không tạo khuyến nghị hoặc cho phép thực thi."
                    )
                    continue

                analyses.append(analysis)
                response_parts.append(format_authoritative_analysis(analysis))
                try:
                    report = await self._reporter.report(message, analysis)
                except Exception:
                    response_parts.append(
                        "AI interpretation không khả dụng; dữ kiện và quyết định "
                        "Risk Engine ở trên vẫn giữ nguyên."
                    )
                else:
                    response_parts.append(f"AI interpretation:\n{report}")

        return SentinelResponse(
            message=_join_messages(*response_parts),
            policy=conversation_result.policy,
            analyses=tuple(analyses),
        )


def _join_messages(*messages: str) -> str:
    return "\n\n".join(message for message in messages if message)
