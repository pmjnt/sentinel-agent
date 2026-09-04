"""Command-line entry point for inspecting the official Binance MCP catalog."""

import asyncio
import json

from dotenv import load_dotenv

from app.mcp.binance import BinanceMcpDiscovery
from app.models.mcp import McpToolCatalogEntry


def render_catalog_json(entries: list[McpToolCatalogEntry]) -> str:
    """Render only the normalized, review-safe catalog fields."""
    data = [entry.model_dump(mode="json") for entry in entries]
    return json.dumps(data, ensure_ascii=False, indent=2)


async def discover_and_render() -> str:
    entries = await BinanceMcpDiscovery().discover()
    return render_catalog_json(entries)


def main() -> None:
    load_dotenv()
    print(asyncio.run(discover_and_render()))


if __name__ == "__main__":
    main()
