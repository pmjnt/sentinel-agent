import asyncio
from decimal import Decimal
from types import SimpleNamespace

from app.agent.controlled_tools import (
    evaluate_cached_portfolio,
    read_market_data,
    read_portfolio,
    stage_policy_update,
)
from app.agent.tool_loop import MAX_AGENT_TURNS, SentinelToolLoop
from app.application import SentinelApplication
from app.config import LLMProvider, Settings
from app.models.market import MarketData, Volatility
from app.models.policy import PolicyChange, PolicyField
from app.models.portfolio import PortfolioAsset
from app.models.risk import RiskStatus
from app.services.portfolio_service import calculate_portfolio
from app.sessions import InMemoryPolicySessionStore


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


async def run_srd_agent(agent, agent_input, *, context, max_turns):
    assert max_turns == MAX_AGENT_TURNS
    assert "Giữ ít nhất 30% USDT" in agent_input
    stage_policy_update(
        context,
        [
            PolicyChange(
                field=PolicyField.MIN_STABLECOIN_WEIGHT,
                value=Decimal("0.30"),
            ),
            PolicyChange(
                field=PolicyField.MAX_ASSET_WEIGHT,
                value=Decimal("0.40"),
            ),
            PolicyChange(
                field=PolicyField.BLOCK_HIGH_VOLATILITY,
                value=True,
            ),
            PolicyChange(
                field=PolicyField.MAX_TRADE_USD_WITHOUT_APPROVAL,
                value=Decimal("1000"),
            ),
        ],
    )
    await read_portfolio(context)
    await read_market_data(context, "BTCUSDT")
    analysis = evaluate_cached_portfolio(context, [])
    assert analysis.risk_decision.status is RiskStatus.BLOCKED
    return SimpleNamespace(
        final_output="BTC concentration is above the configured limit."
    )


def test_srd_policy_scenario_reaches_blocked_without_external_calls() -> None:
    settings = Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="test-key",
    )
    loop = SentinelToolLoop(
        settings,
        SrdScenarioGateway(),
        run_agent=run_srd_agent,
    )
    application = SentinelApplication(loop, InMemoryPolicySessionStore())

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
