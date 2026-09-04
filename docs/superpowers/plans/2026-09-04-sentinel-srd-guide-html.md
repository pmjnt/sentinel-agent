# Sentinel SRD Guide HTML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a self-contained Vietnamese HTML guide that explains Sentinel's SRD gap, target architecture, chat-editable policy, and read-only Binance MCP integration.

**Architecture:** Create one semantic HTML document with embedded CSS so it opens directly without a server or external assets. Add a small Python structural test using only the standard library to verify required sections, internal navigation, source links, and safety wording.

**Tech Stack:** HTML5, embedded CSS3, Python 3.12 standard library, pytest

---

### Task 1: Structural contract for the guide

**Files:**
- Create: `tests/test_srd_guide.py`
- Create: `docs/sentinel-srd-guide.html`

- [x] **Step 1: Write the failing test**

Create `tests/test_srd_guide.py` with a standard-library `HTMLParser` collector. The test must read `docs/sentinel-srd-guide.html` and verify:

```python
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
```

- [x] **Step 2: Run the test and verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_srd_guide.py -q
```

Expected: FAIL because `docs/sentinel-srd-guide.html` does not exist.

### Task 2: Educational HTML content

**Files:**
- Create: `docs/sentinel-srd-guide.html`

- [x] **Step 1: Create the semantic document shell**

Create a Vietnamese HTML5 document with embedded `<style>`, a title header, summary callout, sticky `<nav>` table of contents, and `<main>` containing sections with every ID from `REQUIRED_IDS`. Do not add `<script>`, external stylesheets, web fonts, or images.

- [x] **Step 2: Explain current state and SRD audit**

Write the executive conclusion, current real-vs-simulated flow, and the AC-001 through AC-010 table. Use exact current evidence: mocked portfolio 60/25/15, mocked BTC volatility HIGH, nine passing Python tests before this guide test, and absence of Policy Engine, Planner, and RiskEngine.

- [x] **Step 3: Explain responsibility boundaries**

For LLM, Python, RiskEngine, human approval, Binance MCP, and FastAPI, provide `Là gì?`, `Tại sao cần?`, and `Hoạt động trong Sentinel` explanations. Include a wrong-vs-correct example showing that the LLM must not authoritatively calculate or authorize a trade.

- [x] **Step 4: Explain chat-editable policy**

Use a four-turn example that creates, updates, removes, and reads policy fields. Show the resulting `PortfolioPolicy` JSON after each relevant turn and explain merge semantics, Pydantic validation, session state, ambiguity clarification, and deterministic enforcement.

- [x] **Step 5: Explain the real request flow and architecture**

Document the ten-step Frontend → FastAPI → LLM parse → Pydantic → Binance MCP → deterministic engines → LLM explanation → SSE flow. Include a text architecture diagram and a detailed “what happens when Analyze is pressed?” walkthrough.

- [x] **Step 6: Explain Binance MCP read-only integration**

Document the official endpoint, Streamable HTTP, browser authorization, Account scope, Agentic sub-account, regional eligibility, runtime tool discovery, application-level allow-list, and fail-closed behavior. State explicitly that Sentinel has no order-placement permission and that prompt instructions are not a security boundary.

- [x] **Step 7: Add code-change map, roadmap, security, checklist, and glossary**

List what to retain, replace, and add. Provide the five implementation milestones from the design, a security/failure table, an SRD checklist, and definitions of Agent, LLM, tool, MCP, policy, deterministic code, Pydantic/schema validation, session, SSE, and RiskEngine.

- [x] **Step 8: Add direct primary-source links**

Link the Binance MCP documentation and OpenAI Agents SDK MCP documentation in a final sources section. Do not name undiscovered Binance tools.

### Task 3: Accessible technical-document styling

**Files:**
- Modify: `docs/sentinel-srd-guide.html`

- [x] **Step 1: Add embedded responsive CSS**

Use CSS variables, a readable 16px base, `line-height` of at least 1.6, a two-column navigation/content layout above 980px, a single-column layout below 980px, scrollable wrappers for tables and diagrams, visible focus states, high-contrast status badges, and `scroll-margin-top` on sections.

- [x] **Step 2: Add print CSS**

Hide navigation, remove decorative backgrounds and shadows, expand content to page width, preserve table headers, and avoid breaking callouts or code blocks across printed pages.

- [x] **Step 3: Run the guide test and verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tests/test_srd_guide.py -q
```

Expected: one passing test.

### Task 4: Full verification and handoff

**Files:**
- Review: `docs/sentinel-srd-guide.html`
- Review: `tests/test_srd_guide.py`

- [x] **Step 1: Run all automated verification**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: all Python and JavaScript tests pass, compilation succeeds, and the diff has no whitespace errors.

- [x] **Step 2: Verify visible language and safety claims**

Search the document for every required section heading, `Mô phỏng`, `Thực tế`, `không có quyền đặt lệnh`, both official source URLs, and the three RiskEngine outcomes. Confirm the current and target systems are never described as the same thing.

- [x] **Step 3: Commit**

```bash
git add docs/sentinel-srd-guide.html tests/test_srd_guide.py docs/superpowers/plans/2026-09-04-sentinel-srd-guide-html.md
git commit -m "docs: add Sentinel SRD implementation guide"
```
