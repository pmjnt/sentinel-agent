import asyncio
from collections.abc import Callable

import litellm

from app.agent.tool_loop import SentinelToolLoop
from app.application import SentinelApplication
from app.binance.gateway import BinanceCliGateway
from app.binance.runner import BinanceCliRunner
from app.config import Settings, load_settings
from app.gateways import PortfolioMarketGateway
from app.sessions import InMemoryPolicySessionStore


SAMPLE_PROMPT = (
    "Analyze my BTC exposure and tell me whether it currently looks risky."
)


def configure_litellm_debug(
    settings: Settings,
    enable_debug: Callable[[], None] = litellm._turn_on_debug,
) -> None:
    """Enable verbose LiteLLM logs only after an explicit local opt-in."""
    if not settings.litellm_debug:
        return

    enable_debug()
    print(
        "WARNING: LiteLLM debug is ON. Prompt, policy/portfolio context, and "
        "request body may appear in this terminal; do not share these logs publicly."
    )


def read_console_input(reader: Callable[[], str] = input) -> str:
    """Render the prompt ourselves to avoid terminal-specific input echo."""
    print("Sentinel > ", end="", flush=True)
    try:
        value = reader()
    except UnicodeDecodeError as error:
        # Some terminals or input methods can emit one malformed byte while
        # entering Vietnamese. Preserve the rest of the line instead of
        # terminating the interactive session.
        value = error.object.decode(error.encoding, errors="replace")
    return value.strip()


def format_debug_error(error: Exception, settings: Settings) -> str | None:
    """Return an opt-in diagnostic with configured credentials redacted."""
    if not settings.litellm_debug:
        return None

    diagnostic = f"{type(error).__name__}: {error}"
    secrets = (
        settings.openai_api_key,
        settings.gemini_api_key,
        settings.binance_api_key,
        settings.binance_secret_key,
    )
    for secret in secrets:
        if secret:
            diagnostic = diagnostic.replace(secret, "[REDACTED]")
    return diagnostic


def create_application(
    settings: Settings,
    gateway: PortfolioMarketGateway,
) -> SentinelApplication:
    """Compose Sentinel's use cases; construction performs no external calls."""
    return SentinelApplication(
        agent_loop=SentinelToolLoop(settings, gateway),
        store=InMemoryPolicySessionStore(),
    )


async def run_console() -> None:
    """Run Sentinel's interactive command-line loop."""
    settings = load_settings()
    configure_litellm_debug(settings)
    runner = BinanceCliRunner(settings)
    gateway = BinanceCliGateway(runner, settings.binance_environment)
    application = create_application(settings, gateway)

    print("Sentinel is ready. Financial data comes from Binance Demo.")
    print("Policy and risk decisions are validated by deterministic Python code.")
    print(f"Try: {SAMPLE_PROMPT}")
    print("Type 'exit' to close the application.\n")

    while True:
        try:
            user_input = read_console_input()
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
        except Exception as error:
            print(
                "\nSentinel could not complete the request. "
                "No portfolio recommendation or financial action was generated.\n"
            )
            diagnostic = format_debug_error(error, settings)
            if diagnostic is not None:
                print(f"Technical error: {diagnostic}\n")


def main() -> None:
    try:
        asyncio.run(run_console())
    except ValueError as error:
        print(f"Configuration error: {error}")


if __name__ == "__main__":
    main()
