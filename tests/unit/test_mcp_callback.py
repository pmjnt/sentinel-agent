import asyncio
from urllib.request import urlopen

import pytest

from app.mcp.oauth import (
    LoopbackCallbackServer,
    OAuthCallbackError,
    open_authorization_url,
    parse_authorization_callback,
)


def test_parses_authorization_callback_values() -> None:
    result = parse_authorization_callback(
        "http://127.0.0.1:8766/callback"
        "?code=code-value&state=state-value&iss=https%3A%2F%2Fissuer.example"
    )

    assert result.code == "code-value"
    assert result.state == "state-value"
    assert result.iss == "https://issuer.example"


def test_callback_rejects_missing_code() -> None:
    with pytest.raises(OAuthCallbackError, match="missing authorization code"):
        parse_authorization_callback(
            "http://127.0.0.1:8766/callback?state=state-value"
        )


def test_callback_rejects_oauth_error() -> None:
    with pytest.raises(OAuthCallbackError, match="Access was denied"):
        parse_authorization_callback(
            "http://127.0.0.1:8766/callback"
            "?error=access_denied&error_description=Access+was+denied"
        )


def test_authorization_url_uses_injected_browser_opener() -> None:
    opened_urls: list[str] = []

    open_authorization_url(
        "https://auth.example/authorize",
        opener=lambda url: not opened_urls.append(url),
    )

    assert opened_urls == ["https://auth.example/authorize"]


def test_loopback_server_receives_one_callback() -> None:
    async def scenario() -> None:
        server = LoopbackCallbackServer(port=0)
        try:
            wait_task = asyncio.create_task(server.wait_for_callback())
            callback_url = (
                f"{server.redirect_uri}?code=code-value&state=state-value"
            )

            def send_callback() -> int:
                with urlopen(callback_url, timeout=2) as response:
                    return response.status

            status = await asyncio.to_thread(send_callback)
            result = await asyncio.wait_for(wait_task, timeout=2)

            assert status == 200
            assert result.code == "code-value"
            assert result.state == "state-value"
        finally:
            server.close()

    asyncio.run(scenario())
