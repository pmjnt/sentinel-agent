from app.agent.tool_loop import SentinelToolLoop
from app.application import SentinelApplication
from app.config import Settings
from app.gateways import PortfolioMarketGateway
from app.model_catalog import ModelCatalog
from app.sessions import InMemoryPolicySessionStore


def create_application(
    settings: Settings,
    gateway: PortfolioMarketGateway,
    catalog: ModelCatalog | None = None,
) -> SentinelApplication:
    """Compose Sentinel's use cases without performing external calls."""
    model_catalog = catalog or ModelCatalog.from_settings(settings)
    return SentinelApplication(
        agent_loop=SentinelToolLoop(
            settings,
            gateway,
            catalog=model_catalog,
        ),
        store=InMemoryPolicySessionStore(),
    )
