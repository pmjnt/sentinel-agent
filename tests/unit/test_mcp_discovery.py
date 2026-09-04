import asyncio
import json
from collections.abc import Mapping
from types import SimpleNamespace

import pytest
from mcp.types import Tool

from app.mcp.binance import (
    BinanceMcpConfigurationError,
    BinanceMcpDiscovery,
    read_client_metadata_url,
)
from app.mcp.discover import render_catalog_json
from app.models.mcp import McpToolCatalogEntry


class FakeMcpSession:
    def __init__(self) -> None:
        self.list_tools_calls = 0
        self.call_tool_calls = 0

    async def list_tools(self) -> SimpleNamespace:
        self.list_tools_calls += 1
        return SimpleNamespace(
            tools=[
                Tool(
                    name="market_reader",
                    description="Read market data.",
                    inputSchema={"type": "object"},
                )
            ]
        )

    async def call_tool(self, *args: object, **kwargs: object) -> None:
        self.call_tool_calls += 1
        raise AssertionError("Discovery must never call an MCP tool.")


def test_discovery_lists_tools_once_without_invoking_them() -> None:
    session = FakeMcpSession()

    entries = asyncio.run(
        BinanceMcpDiscovery.discover_with_session(session)
    )

    assert [entry.name for entry in entries] == ["market_reader"]
    assert session.list_tools_calls == 1
    assert session.call_tool_calls == 0


def test_catalog_json_contains_only_normalized_metadata() -> None:
    output = render_catalog_json(
        [
            McpToolCatalogEntry(
                name="market_reader",
                description="Read market data.",
                input_schema={"type": "object"},
                read_only_hint=True,
                destructive_hint=False,
            )
        ]
    )
    parsed = json.loads(output)

    assert parsed[0]["name"] == "market_reader"
    assert "access_token" not in output
    assert "client_secret" not in output
    assert "_meta" not in output


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"BINANCE_MCP_CLIENT_METADATA_URL": "http://example.com/client.json"},
        {"BINANCE_MCP_CLIENT_METADATA_URL": "https://example.com/"},
    ],
)
def test_client_metadata_url_must_be_public_https_document(
    environment: Mapping[str, str],
) -> None:
    with pytest.raises(BinanceMcpConfigurationError):
        read_client_metadata_url(environment)


def test_reads_valid_client_metadata_url() -> None:
    url = "https://sentinel.example/oauth/client-metadata.json"

    assert read_client_metadata_url(
        {"BINANCE_MCP_CLIENT_METADATA_URL": url}
    ) == url
