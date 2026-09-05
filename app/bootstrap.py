from app.agent.tool_loop import SentinelToolLoop
from app.application import SentinelApplication
from app.config import Settings
from app.gateways import PortfolioMarketGateway
from app.sessions import InMemoryPolicySessionStore


def create_application(
    settings: Settings,
    gateway: PortfolioMarketGateway,
) -> SentinelApplication:
    """Compose Sentinel's use cases without performing external calls."""
    return SentinelApplication(
        agent_loop=SentinelToolLoop(settings, gateway),
        store=InMemoryPolicySessionStore(),
    )
