import pytest

import app.config as config
from app.config import load_settings


def test_load_settings_reads_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    settings = load_settings()

    assert settings.openai_api_key == "test-key"


def test_load_settings_requires_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(config, "load_dotenv", lambda: False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        load_settings()
