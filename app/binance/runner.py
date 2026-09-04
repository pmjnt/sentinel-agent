import asyncio
import json
import os
from collections.abc import Sequence
from typing import Any, Protocol

from app.config import Settings, require_binance_credentials


class BinanceCliError(RuntimeError):
    """A safe CLI failure that never contains command output or credentials."""


class JsonCommandRunner(Protocol):
    async def run(
        self,
        arguments: Sequence[str],
        *,
        authenticated: bool = False,
    ) -> Any: ...


class BinanceCliRunner:
    """Run Binance CLI commands as argument arrays and parse their JSON output."""

    def __init__(
        self,
        settings: Settings,
        timeout_seconds: float = 15,
    ) -> None:
        self._settings = settings
        self._executable = settings.binance_cli_path
        self._timeout_seconds = timeout_seconds

    async def run(
        self,
        arguments: Sequence[str],
        *,
        authenticated: bool = False,
    ) -> Any:
        environment = self._build_environment(authenticated)
        try:
            process = await asyncio.create_subprocess_exec(
                self._executable,
                *arguments,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=environment,
            )
        except FileNotFoundError as error:
            raise BinanceCliError(
                "Binance CLI executable was not found."
            ) from error

        try:
            stdout, _stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise BinanceCliError("Binance CLI command timed out.") from error

        if process.returncode != 0:
            raise BinanceCliError("Binance CLI command failed.")
        if not stdout:
            raise BinanceCliError("Binance CLI returned an empty response.")

        try:
            return json.loads(stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BinanceCliError(
                "Binance CLI returned invalid JSON."
            ) from error

    def _build_environment(self, authenticated: bool) -> dict[str, str]:
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "BINANCE_API_ENV": self._settings.binance_environment.value,
        }
        if authenticated:
            credentials = require_binance_credentials(self._settings)
            environment["BINANCE_API_KEY"] = credentials.api_key
            environment["BINANCE_SECRET_KEY"] = credentials.secret_key
        return environment
