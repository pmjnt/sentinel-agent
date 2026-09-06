from app.agent.tool_loop import SentinelToolLoop
from app.application import SentinelApplication
from app.config import Settings
from app.execution.store import InMemoryExecutionPlanStore
from app.gateways import DemoExecutionGateway
from app.model_catalog import ModelCatalog
from app.sessions import InMemoryPolicySessionStore
from app.services.execution_service import DemoExecutionService


def create_application(
    settings: Settings,
    gateway: DemoExecutionGateway,
    catalog: ModelCatalog | None = None,
) -> SentinelApplication:
    """Compose Sentinel's use cases without performing external calls."""
    model_catalog = catalog or ModelCatalog.from_settings(settings)
    policy_store = InMemoryPolicySessionStore()
    plan_store = InMemoryExecutionPlanStore()
    execution_service = DemoExecutionService(
        gateway=gateway,
        plans=plan_store,
        policy_loader=policy_store.get,
        enabled=settings.demo_execution_enabled,
    )
    return SentinelApplication(
        agent_loop=SentinelToolLoop(
            settings,
            gateway,
            catalog=model_catalog,
        ),
        store=policy_store,
        execution_plans=plan_store,
        execution_service=execution_service,
    )
