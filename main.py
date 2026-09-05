import asyncio

from app.agent.analysis_reporter import AgentAnalysisReporter
from app.agent.request_interpreter import AgentRequestInterpreter
from app.application import SentinelApplication
from app.binance.gateway import BinanceCliGateway
from app.binance.runner import BinanceCliRunner
from app.config import Settings, load_settings
from app.gateways import PortfolioMarketGateway
from app.services.policy_conversation_service import PolicyConversationService
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.sessions import InMemoryPolicySessionStore


SAMPLE_PROMPT = (
    "Analyze my BTC exposure and tell me whether it currently looks risky."
)


def create_application(
    settings: Settings,
    gateway: PortfolioMarketGateway,
) -> SentinelApplication:
    """Compose Sentinel's use cases; construction performs no external calls."""
    interpreter = AgentRequestInterpreter(settings)
    conversation = PolicyConversationService(
        interpreter=interpreter,
        store=InMemoryPolicySessionStore(),
    )
    analysis_service = PortfolioAnalysisService(gateway)
    reporter = AgentAnalysisReporter(settings)
    return SentinelApplication(conversation, analysis_service, reporter)


async def run_console() -> None:
    """Run Sentinel's interactive command-line loop."""
    settings = load_settings()
    runner = BinanceCliRunner(settings)
    gateway = BinanceCliGateway(runner, settings.binance_environment)
    application = create_application(settings, gateway)

    print("Sentinel is ready. Financial data comes from Binance Demo.")
    print("Policy and risk decisions are validated by deterministic Python code.")
    print(f"Try: {SAMPLE_PROMPT}")
    print("Type 'exit' to close the application.\n")

    while True:
        try:
            user_input = input("Sentinel > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return

        if user_input.lower() == "exit":
            print("Goodbye.")
            return

        if not user_input:
            continue

        try:
            result = await application.handle("console-user", user_input)
            print(f"\n{result.message}\n")
        except Exception:
            print(
                "\nSentinel could not complete the request. "
                "No portfolio recommendation or financial action was generated.\n"
            )


def main() -> None:
    try:
        asyncio.run(run_console())
    except ValueError as error:
        print(f"Configuration error: {error}")


if __name__ == "__main__":
    main()
