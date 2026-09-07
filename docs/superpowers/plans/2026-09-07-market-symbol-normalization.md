# Market Symbol Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the LLM-facing market tool to accept either an asset name or a USDT pair without failing the advice workflow.

**Architecture:** Normalize market input inside `controlled_tools.py`, before the trusted Binance gateway is called. Keep the gateway strict and keep all returned financial data sourced from Binance Demo.

**Tech Stack:** Python 3.12, Pydantic, OpenAI Agents SDK, pytest

---

### Task 1: Normalize asset symbols at the controlled-tool boundary

**Files:**
- Modify: `app/agent/controlled_tools.py:187-205`
- Test: `tests/unit/test_controlled_tools.py`

- [ ] **Step 1: Write the failing test**

```python
def test_market_reader_converts_asset_to_usdt_pair() -> None:
    context = _context()

    result = asyncio.run(read_market_data(context, "BTC"))

    assert isinstance(result, MarketData)
    assert result.symbol == "BTCUSDT"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_controlled_tools.py::test_market_reader_converts_asset_to_usdt_pair -q`

Expected: FAIL because the gateway receives `BTC` instead of `BTCUSDT`.

- [ ] **Step 3: Implement minimal normalization**

```python
def normalize_usdt_market(symbol: str) -> str | None:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Market symbol must not be empty.")
    if normalized in {"USDT", "USDTUSDT"}:
        return None
    if normalized.endswith("USDT"):
        return normalized
    return f"{normalized}USDT"
```

Use the returned pair in `read_market_data`; return `ToolDataNotRequired` when it is `None`.

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/python -m pytest tests/unit/test_controlled_tools.py -q`

Expected: all controlled-tool tests pass.

- [ ] **Step 5: Verify the original workflow**

Submit two messages to the same streaming API session:

```text
Give me some investment advice for my portfolio
Investor profile updated: acceptable loss is 20%; objective is growth; time horizon is 12 months.
```

Expected: profile update is followed by portfolio analysis and advice; no failure for `USDC` or `USDTUSDT`.

- [ ] **Step 6: Run complete validation**

Run:

```text
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app main.py
node --test tests/test_ui.js
git diff --check
```

Expected: all commands exit successfully.

- [ ] **Step 7: Commit the implementation**

```text
git add app/agent/controlled_tools.py tests/unit/test_controlled_tools.py
git commit -m "fix: normalize Agent market symbols"
```
