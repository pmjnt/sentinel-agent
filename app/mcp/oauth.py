from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class InMemoryOAuthStorage:
    """Hold OAuth state for one local process without persisting secrets."""

    def __init__(self) -> None:
        self._tokens: OAuthToken | None = None
        self._client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self._client_info

    async def set_client_info(
        self,
        client_info: OAuthClientInformationFull,
    ) -> None:
        self._client_info = client_info

    def clear(self) -> None:
        self._tokens = None
        self._client_info = None

    def __repr__(self) -> str:
        return "InMemoryOAuthStorage(tokens=<redacted>, client_info=<redacted>)"
