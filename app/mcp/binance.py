from collections.abc import Awaitable, Callable, Mapping
import os
from typing import Protocol
from urllib.parse import urlparse

import httpx2
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientMetadata
from mcp.types import ListToolsResult, Tool
from pydantic import AnyUrl

from app.mcp.oauth import (
    InMemoryOAuthStorage,
    LoopbackCallbackServer,
    open_authorization_url,
)
from app.models.mcp import McpToolCatalogEntry


BINANCE_MCP_ENDPOINT = "https://agent.binance.com/mcp/agentic"


class BinanceMcpConfigurationError(ValueError):
    """Raised when required public OAuth client metadata is not configured."""


def read_client_metadata_url(
    environment: Mapping[str, str] = os.environ,
) -> str:
    """Read and validate the public HTTPS Client ID Metadata Document URL."""
    # The loose mapping boundary keeps this pure function easy to test.
    raw_value = environment.get("BINANCE_MCP_CLIENT_METADATA_URL")
    if not raw_value:
        raise BinanceMcpConfigurationError(
            "BINANCE_MCP_CLIENT_METADATA_URL is required for Binance OAuth."
        )

    parsed = urlparse(raw_value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path in ("", "/"):
        raise BinanceMcpConfigurationError(
            "BINANCE_MCP_CLIENT_METADATA_URL must be a public HTTPS document URL."
        )
    return raw_value


class ToolListingSession(Protocol):
    """Small session boundary needed by discovery."""

    def list_tools(self) -> Awaitable[ListToolsResult]: ...


class BinanceMcpDiscovery:
    """Authenticate and read Binance MCP tool definitions without invoking tools."""

    def __init__(
        self,
        endpoint: str = BINANCE_MCP_ENDPOINT,
        callback_port: int = 8766,
        browser_opener: Callable[[str], bool] | None = None,
        client_metadata_url: str | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._callback_port = callback_port
        self._browser_opener = browser_opener
        self._client_metadata_url = client_metadata_url

    async def discover(self) -> list[McpToolCatalogEntry]:
        client_metadata_url = (
            self._client_metadata_url or read_client_metadata_url()
        )
        callback = LoopbackCallbackServer(port=self._callback_port)

        async def redirect_handler(url: str) -> None:
            if self._browser_opener is None:
                open_authorization_url(url)
            else:
                open_authorization_url(url, opener=self._browser_opener)

        provider = OAuthClientProvider(
            server_url=self._endpoint,
            client_metadata=OAuthClientMetadata(
                client_name="Sentinel",
                redirect_uris=[AnyUrl(callback.redirect_uri)],
                grant_types=["authorization_code"],
                response_types=["code"],
                application_type="native",
            ),
            storage=InMemoryOAuthStorage(),
            redirect_handler=redirect_handler,
            callback_handler=callback.wait_for_callback,
            client_metadata_url=client_metadata_url,
        )

        try:
            async with httpx2.AsyncClient(
                auth=provider,
                follow_redirects=True,
            ) as http_client:
                async with streamable_http_client(
                    self._endpoint,
                    http_client=http_client,
                ) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        return await self.discover_with_session(session)
        finally:
            callback.close()

    @staticmethod
    async def discover_with_session(
        session: ToolListingSession,
    ) -> list[McpToolCatalogEntry]:
        result = await session.list_tools()
        return to_catalog_entries(result.tools)


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
