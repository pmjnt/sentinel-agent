import asyncio

from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from app.mcp.oauth import InMemoryOAuthStorage


def test_oauth_storage_starts_empty() -> None:
    storage = InMemoryOAuthStorage()

    assert asyncio.run(storage.get_tokens()) is None
    assert asyncio.run(storage.get_client_info()) is None


def test_oauth_values_round_trip_and_clear() -> None:
    storage = InMemoryOAuthStorage()
    tokens = OAuthToken(
        access_token="secret-access-token",
        refresh_token="secret-refresh-token",
        expires_in=3600,
    )
    client_info = OAuthClientInformationFull(
        client_id="sentinel-client",
        client_secret="secret-client-value",
    )

    asyncio.run(storage.set_tokens(tokens))
    asyncio.run(storage.set_client_info(client_info))

    assert asyncio.run(storage.get_tokens()) == tokens
    assert asyncio.run(storage.get_client_info()) == client_info

    storage.clear()

    assert asyncio.run(storage.get_tokens()) is None
    assert asyncio.run(storage.get_client_info()) is None


def test_oauth_storage_repr_does_not_reveal_secrets() -> None:
    storage = InMemoryOAuthStorage()
    asyncio.run(
        storage.set_tokens(OAuthToken(access_token="do-not-print-this-token"))
    )

    assert "do-not-print-this-token" not in repr(storage)
