import asyncio
from decimal import Decimal

from app.application import SentinelApplication
from app.models.chat import AnalyzePortfolioAction, ParsedRequest, UpdatePolicyAction
from app.models.market import MarketData, Volatility
from app.models.policy import PolicyPatch, PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.models.risk import RiskStatus
from app.services.policy_conversation_service import PolicyConversationService
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.services.portfolio_service import calculate_portfolio
from app.sessions import InMemoryPolicySessionStore


class SrdScenarioInterpreter:
    async def interpret(
        self,
        message: str,
        current_policy: PortfolioPolicy,
    ) -> ParsedRequest:
        return ParsedRequest(
            actions=[
                UpdatePolicyAction(
                    patch=PolicyPatch(
                        min_stablecoin_weight=Decimal("0.30"),
                        max_asset_weight=Decimal("0.40"),
                        block_high_volatility=True,
                        max_trade_usd_without_approval=Decimal("1000"),
                    )
                ),
                AnalyzePortfolioAction(),
            ]
        )


class SrdScenarioGateway:
    async def get_portfolio(self):
        return calculate_portfolio(
            [
                PortfolioAsset(
                    symbol="BTC",
                    amount=Decimal("0.05"),
                    usd_value=Decimal("5500"),
                ),
                PortfolioAsset(
                    symbol="ETH",
                    amount=Decimal("0.8"),
                    usd_value=Decimal("2500"),
                ),
                PortfolioAsset(
                    symbol="USDT",
                    amount=Decimal("2000"),
                    usd_value=Decimal("2000"),
                ),
            ]
        )

    async def get_market_data(self, symbol: str):
        assert symbol == "BTCUSDT"
        return MarketData(
            symbol=symbol,
            price=Decimal("110000"),
            change_24h_percent=Decimal("-4.2"),
            volatility=Volatility.HIGH,
            estimated_slippage_percent=Decimal("0.05"),
        )


class DecisionEchoReporter:
    async def report(self, message: str, analysis) -> str:
        return "BTC concentration is above the configured limit."


def test_srd_policy_scenario_reaches_blocked_without_external_calls() -> None:
    application = SentinelApplication(
        PolicyConversationService(
            SrdScenarioInterpreter(),
            InMemoryPolicySessionStore(),
        ),
        PortfolioAnalysisService(SrdScenarioGateway()),
        DecisionEchoReporter(),
    )

    result = asyncio.run(
        application.handle(
            "demo-user",
            "Giữ ít nhất 30% USDT, không asset nào trên 40%, chặn khi "
            "volatility cao, giao dịch trên 1.000 USD cần duyệt, rồi phân tích.",
        )
    )

    assert result.policy.min_stablecoin_weight == Decimal("0.30")
    assert result.policy.max_asset_weight == Decimal("0.40")
    assert result.analysis is not None
    assert len(result.analysis.violations) == 2
    assert result.analysis.plan.actions[0].estimated_usd_value == Decimal("1500.00")
    assert result.analysis.risk_decision.status is RiskStatus.BLOCKED
    assert "Risk Engine: BLOCKED" in result.message
    assert "Execution: NOT_EXECUTED" in result.message
