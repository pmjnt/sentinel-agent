import asyncio

from agents import Runner

from app.agent.sentinel import create_sentinel_agent
from app.binance.gateway import BinanceCliGateway
from app.binance.runner import BinanceCliRunner
from app.config import load_settings


SAMPLE_PROMPT = (
    "Analyze my BTC exposure and tell me whether it currently looks risky."
)


async def run_console() -> None:
    """Run Sentinel's interactive command-line loop."""
    settings = load_settings()
    runner = BinanceCliRunner(settings)
    gateway = BinanceCliGateway(runner, settings.binance_environment)
    sentinel = create_sentinel_agent(settings, gateway)

    print("Sentinel is ready. Portfolio and market data come from Binance Demo.")
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
            result = await Runner.run(sentinel, user_input)
            print(f"\n{result.final_output}\n")
        except Exception:
            print(
                "\nSentinel could not complete the request. "
                "Required Binance Demo data could not be verified. "
                "No portfolio recommendation was generated.\n"
            )


def main() -> None:
    try:
        asyncio.run(run_console())
    except ValueError as error:
        print(f"Configuration error: {error}")


if __name__ == "__main__":
    main()
