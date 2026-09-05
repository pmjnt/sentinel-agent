import re
from html.parser import HTMLParser
from pathlib import Path


GUIDE_PATH = Path(__file__).parents[1] / "docs" / "sentinel-project-guide.html"


class LandmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.main_count = 0
        self.nav_count = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "main":
            self.main_count += 1
        elif tag == "nav":
            self.nav_count += 1


def _read_guide() -> str:
    return GUIDE_PATH.read_text(encoding="utf-8")


def test_project_guide_has_semantic_landmarks_and_statuses() -> None:
    source = _read_guide()
    parser = LandmarkParser()
    parser.feed(source)

    assert parser.main_count == 1
    assert parser.nav_count >= 1
    for label in (
        "ĐÃ HOẠT ĐỘNG",
        "ĐÃ VIẾT — CHƯA NỐI END-TO-END",
        "TƯƠNG LAI",
    ):
        assert label in source


def test_project_guide_maps_runtime_and_policy_files() -> None:
    source = _read_guide()

    for path in (
        "main.py",
        "app/agent/sentinel.py",
        "app/tools/portfolio.py",
        "app/tools/market.py",
        "app/binance/gateway.py",
        "app/binance/runner.py",
        "app/agent/policy_parser.py",
        "app/services/policy_conversation_service.py",
        "app/services/policy_service.py",
        "app/services/rebalance_service.py",
        "app/services/risk_service.py",
        "binance-cli",
    ):
        assert path in source


def test_project_guide_states_current_limitations_explicitly() -> None:
    source = _read_guide()

    assert "UI hiện tại là bản tĩnh; tiến trình phân tích trên web đang được mô phỏng." in source
    assert "Policy orchestration chưa được kết nối vào main.py." in source
    assert "Custom MCP hiện không hoạt động." in source
    assert "Sentinel hiện không có khả năng giao dịch." in source


def test_project_guide_does_not_contain_a_binance_secret() -> None:
    source = _read_guide()

    secret_assignment = re.compile(
        r"BINANCE_SECRET_KEY\s*=\s*(?!your_)[A-Za-z0-9+/=_-]{16,}"
    )
    assert secret_assignment.search(source) is None
