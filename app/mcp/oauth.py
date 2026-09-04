import asyncio
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import AuthorizationCodeResult
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class OAuthCallbackError(ValueError):
    """Raised when the local OAuth redirect is missing a valid authorization code."""


def parse_authorization_callback(url: str) -> AuthorizationCodeResult:
    """Parse OAuth callback parameters without logging secret values."""
    parameters = parse_qs(urlparse(url).query)
    if "error" in parameters:
        description = parameters.get(
            "error_description",
            parameters["error"],
        )[0]
        raise OAuthCallbackError(f"OAuth authorization failed: {description}")

    codes = parameters.get("code")
    if not codes or not codes[0]:
        raise OAuthCallbackError("OAuth callback is missing authorization code.")

    return AuthorizationCodeResult(
        code=codes[0],
        state=_first_optional(parameters, "state"),
        iss=_first_optional(parameters, "iss"),
    )


def open_authorization_url(
    url: str,
    opener: Callable[[str], bool] = webbrowser.open,
) -> None:
    """Open the authorization URL using an injectable browser boundary."""
    if not opener(url):
        raise RuntimeError("Could not open the Binance authorization page.")


class LoopbackCallbackServer:
    """Receive one OAuth redirect on a local loopback address."""

    def __init__(
        self,
        port: int = 8766,
        timeout_seconds: float = 300,
    ) -> None:
        self._result: AuthorizationCodeResult | None = None
        self._error: Exception | None = None

        owner = self

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if urlparse(self.path).path != "/callback":
                    owner._error = OAuthCallbackError(
                        "OAuth callback used an unexpected path."
                    )
                    self._send_page(404, "Authorization callback was not recognized.")
                    return

                callback_url = f"{owner.redirect_uri}{self.path.partition('?')[2]}"
                if "?" in self.path:
                    callback_url = (
                        f"{owner.redirect_uri}?{self.path.partition('?')[2]}"
                    )
                try:
                    owner._result = parse_authorization_callback(callback_url)
                except OAuthCallbackError as error:
                    owner._error = error
                    self._send_page(400, "Authorization failed. Return to Sentinel.")
                    return

                self._send_page(
                    200,
                    "Authorization received. You may close this tab and return to Sentinel.",
                )

            def _send_page(self, status: int, message: str) -> None:
                body = (
                    "<!doctype html><html lang='en'><meta charset='utf-8'>"
                    f"<title>Sentinel OAuth</title><body><p>{message}</p></body></html>"
                ).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = HTTPServer(("127.0.0.1", port), CallbackHandler)
        self._server.timeout = timeout_seconds

    @property
    def redirect_uri(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/callback"

    async def wait_for_callback(self) -> AuthorizationCodeResult:
        await asyncio.to_thread(self._server.handle_request)
        if self._error is not None:
            raise self._error
        if self._result is None:
            raise OAuthCallbackError("Timed out waiting for OAuth authorization.")
        return self._result

    def close(self) -> None:
        self._server.server_close()


def _first_optional(
    parameters: dict[str, list[str]],
    name: str,
) -> str | None:
    values = parameters.get(name)
    return values[0] if values else None


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
