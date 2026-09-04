from mcp.types import Tool

from app.models.mcp import McpToolCatalogEntry


BINANCE_MCP_ENDPOINT = "https://agent.binance.com/mcp/agentic"


def to_catalog_entries(tools: list[Tool]) -> list[McpToolCatalogEntry]:
    """Copy only review-safe metadata from the server's tool definitions."""
    return [
        McpToolCatalogEntry(
            name=tool.name,
            title=tool.title,
            description=tool.description,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            read_only_hint=(
                tool.annotations.read_only_hint if tool.annotations else None
            ),
            destructive_hint=(
                tool.annotations.destructive_hint if tool.annotations else None
            ),
        )
        for tool in tools
    ]
