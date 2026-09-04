import asyncio
import json
from typing import Any

import pytest

from app.binance.runner import BinanceCliError, BinanceCliRunner
from app.config import BinanceEnvironment, LLMProvider, Settings


class FakeProcess:
    def __init__(
        self,
        stdout: bytes = b"{}",
        stderr: bytes = b"",
        returncode: int = 0,
        communicate_error: Exception | None = None,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.communicate_error = communicate_error
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self.communicate_error is not None:
            raise self.communicate_error
        return self.stdout, self.stderr

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        return self.returncode


def _settings(**updates: Any) -> Settings:
    values: dict[str, Any] = {
        "llm_provider": LLMProvider.GEMINI,
        "llm_model": "test-model",
        "gemini_api_key": "llm-secret-must-not-reach-cli",
        "binance_environment": BinanceEnvironment.DEMO,
        "binance_cli_path": "/safe/binance-cli",
        "binance_api_key": "demo-api-key",
        "binance_secret_key": "demo-secret-key",
    }
    values.update(updates)
    return Settings(**values)


def _install_fake_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    process: FakeProcess,
) -> list[tuple[tuple[object, ...], dict[str, object]]]:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def create_subprocess_exec(
        *args: object,
        **kwargs: object,
    ) -> FakeProcess:
        calls.append((args, kwargs))
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_subprocess_exec)
    return calls


def test_public_command_uses_argument_array_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", "/safe/home")
    process = FakeProcess(stdout=json.dumps({"price": "100"}).encode())
    calls = _install_fake_subprocess(monkeypatch, process)
    runner = BinanceCliRunner(_settings())

    result = asyncio.run(
        runner.run(["spot", "ticker-price", "--symbol", "BTCUSDT"])
    )

    assert result == {"price": "100"}
    args, kwargs = calls[0]
    assert args == (
        "/safe/binance-cli",
        "spot",
        "ticker-price",
        "--symbol",
        "BTCUSDT",
    )
    assert "shell" not in kwargs
    child_environment = kwargs["env"]
    assert isinstance(child_environment, dict)
    assert child_environment["HOME"] == "/safe/home"
    assert child_environment["BINANCE_API_ENV"] == "demo"
    assert "BINANCE_API_KEY" not in child_environment
    assert "BINANCE_SECRET_KEY" not in child_environment
    assert "GEMINI_API_KEY" not in child_environment


def test_authenticated_command_receives_only_binance_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_fake_subprocess(monkeypatch, FakeProcess())
    runner = BinanceCliRunner(_settings())

    asyncio.run(runner.run(["spot", "get-account"], authenticated=True))

    child_environment = calls[0][1]["env"]
    assert isinstance(child_environment, dict)
    assert child_environment["BINANCE_API_KEY"] == "demo-api-key"
    assert child_environment["BINANCE_SECRET_KEY"] == "demo-secret-key"
    assert "GEMINI_API_KEY" not in child_environment


@pytest.mark.parametrize(
    ("process", "expected_message"),
    [
        (FakeProcess(returncode=1, stderr=b"demo-secret-key"), "command failed"),
        (FakeProcess(stdout=b""), "empty response"),
        (FakeProcess(stdout=b"not-json demo-api-key"), "invalid JSON"),
    ],
)
def test_cli_failures_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    process: FakeProcess,
    expected_message: str,
) -> None:
    _install_fake_subprocess(monkeypatch, process)
    runner = BinanceCliRunner(_settings())

    with pytest.raises(BinanceCliError, match=expected_message) as error:
        asyncio.run(runner.run(["spot", "ticker-price"]))

    message = str(error.value)
    assert "demo-api-key" not in message
    assert "demo-secret-key" not in message


def test_timeout_kills_process_and_returns_sanitized_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess(communicate_error=TimeoutError())
    _install_fake_subprocess(monkeypatch, process)
    runner = BinanceCliRunner(_settings(), timeout_seconds=0.01)

    with pytest.raises(BinanceCliError, match="timed out"):
        asyncio.run(runner.run(["spot", "ticker-price"]))

    assert process.killed is True


def test_missing_executable_returns_safe_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def missing_executable(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("/secret/path/binance-cli")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", missing_executable)
    runner = BinanceCliRunner(_settings())

    with pytest.raises(BinanceCliError, match="executable was not found") as error:
        asyncio.run(runner.run(["spot", "ticker-price"]))

    assert "/secret/path" not in str(error.value)
