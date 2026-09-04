from html.parser import HTMLParser
from pathlib import Path


GUIDE_PATH = Path(__file__).parents[1] / "docs" / "sentinel-srd-guide.html"
REQUIRED_IDS = {
    "ket-luan",
    "hien-trang",
    "acceptance-criteria",
    "ranh-gioi-trach-nhiem",
    "policy-qua-chat",
    "request-flow",
    "binance-mcp",
    "kien-truc-dich",
    "thay-doi-code",
    "lo-trinh",
    "bao-mat",
    "checklist",
    "glossary",
}


class GuideParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.internal_links: set[str] = set()
        self.external_assets: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")

        href = values.get("href", "") or ""
        if tag == "a" and href.startswith("#"):
            self.internal_links.add(href[1:])

        if tag in {"script", "img"} and values.get("src"):
            self.external_assets.append(values["src"] or "")
        if tag == "link" and values.get("href"):
            self.external_assets.append(values["href"] or "")


def test_srd_guide_is_self_contained_and_complete() -> None:
    html = GUIDE_PATH.read_text(encoding="utf-8")
    parser = GuideParser()
    parser.feed(html)

    assert REQUIRED_IDS <= parser.ids
    assert parser.internal_links <= parser.ids
    assert parser.external_assets == []
    assert "https://agent.binance.com/mcp/agentic" in html
    assert "BLOCKED" in html
    assert "REQUIRES_APPROVAL" in html
    assert "SAFE_TO_PROPOSE" in html
    assert "không có quyền đặt lệnh" in html.lower()
