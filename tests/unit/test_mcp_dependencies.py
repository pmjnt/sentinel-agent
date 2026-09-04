import httpx2
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client

from app.mcp.binance import BINANCE_MCP_ENDPOINT


def test_required_mcp_client_api_is_available() -> None:
    assert OAuthClientProvider is not None
    assert TokenStorage is not None
    assert callable(streamable_http_client)
    assert hasattr(httpx2, "AsyncClient")


def test_binance_mcp_endpoint_is_exact() -> None:
    assert BINANCE_MCP_ENDPOINT == "https://agent.binance.com/mcp/agentic"
