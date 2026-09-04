# Sentinel Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal interactive Python AI Agent that uses mock portfolio and market tools to analyze crypto risk.

**Architecture:** Keep mock-data functions as ordinary typed Python functions so unit tests can call them directly, then wrap them separately with OpenAI Agents SDK `function_tool` objects for the LLM. A single Sentinel Agent receives those tools, while a small async console loop uses `Runner.run` and environment-based configuration.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, python-dotenv, Pydantic, pytest

---

### Task 1: Project foundation and portfolio model behavior

**Files:**
- Create: `app/__init__.py`
- Create: `app/tools/__init__.py`
- Create: `app/models.py`
- Create: `tests/test_portfolio.py`

- [ ] **Step 1: Write the failing portfolio test**

```python
from app.tools.portfolio import get_portfolio


def test_get_portfolio_returns_expected_mock_allocation() -> None:
    portfolio = get_portfolio()
    values = {asset.symbol: asset.value_usd for asset in portfolio.assets}

    assert values == {"BTC": 6000.0, "ETH": 2500.0, "USDT": 1500.0}
    assert portfolio.total_value_usd == 10000.0
```

- [ ] **Step 2: Run the test to observe the missing implementation**

Run: `python -m pytest tests/test_portfolio.py -v`
Expected: FAIL during collection because `app.tools.portfolio` does not exist.

- [ ] **Step 3: Add the minimal typed portfolio implementation and SDK wrapper**

Create Pydantic `PortfolioAsset` and `Portfolio`, then implement:

```python
def get_portfolio() -> Portfolio:
    return Portfolio(
        assets=[
            PortfolioAsset(symbol="BTC", value_usd=6000.0),
            PortfolioAsset(symbol="ETH", value_usd=2500.0),
            PortfolioAsset(symbol="USDT", value_usd=1500.0),
        ],
        total_value_usd=10000.0,
    )


get_portfolio_tool = function_tool(get_portfolio)
```

- [ ] **Step 4: Run the portfolio test**

Run: `python -m pytest tests/test_portfolio.py -v`
Expected: 1 passed.

### Task 2: Market data model behavior

**Files:**
- Modify: `app/models.py`
- Create: `app/tools/market.py`
- Create: `tests/test_market.py`

- [ ] **Step 1: Write failing BTC and unsupported-symbol tests**

```python
from app.models import Volatility
from app.tools.market import get_market_data


def test_get_market_data_returns_btc_mock_data() -> None:
    market_data = get_market_data("BTCUSDT")

    assert market_data.supported is True
    assert market_data.price == 110000.0
    assert market_data.change_24h_percent == -4.2
    assert market_data.volatility is Volatility.HIGH
    assert market_data.error is None


def test_get_market_data_returns_error_for_unsupported_symbol() -> None:
    market_data = get_market_data("SOLUSDT")

    assert market_data.supported is False
    assert market_data.price is None
    assert market_data.error == "Unsupported symbol: SOLUSDT"
```

- [ ] **Step 2: Run the tests to observe the missing implementation**

Run: `python -m pytest tests/test_market.py -v`
Expected: FAIL during collection because the market model/tool does not exist.

- [ ] **Step 3: Implement the market model, mock lookup and SDK wrapper**

Use a string enum with `LOW`, `MEDIUM`, `HIGH`. Return BTCUSDT and ETHUSDT records from a small constant dictionary. Normalize input with `symbol.strip().upper()`. Return a `MarketData` record with `supported=False` and `error=f"Unsupported symbol: {normalized_symbol}"` for unknown symbols.

- [ ] **Step 4: Run all tool tests**

Run: `python -m pytest tests/test_portfolio.py tests/test_market.py -v`
Expected: 3 passed.

### Task 3: Sentinel Agent and configuration

**Files:**
- Create: `app/config.py`
- Create: `app/agent.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `requirements.txt`

- [ ] **Step 1: Add focused configuration tests**

Create `tests/test_config.py` to verify that `load_settings()` returns the environment key after loading dotenv and raises a clear `ValueError` when the key is absent. Use pytest `monkeypatch`; do not call OpenAI.

- [ ] **Step 2: Run the configuration tests and confirm failure**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL because `app.config` is missing.

- [ ] **Step 3: Implement configuration and Agent construction**

`load_settings()` calls `load_dotenv()`, reads `OPENAI_API_KEY`, and returns a small immutable Pydantic `Settings`. `create_sentinel_agent()` returns:

```python
Agent(
    name="Sentinel",
    instructions=SENTINEL_INSTRUCTIONS,
    tools=[get_portfolio_tool, get_market_data_tool],
)
```

Instructions enforce tool-grounded facts, concise concentration-risk analysis, separation of facts and interpretation, and the prohibition on trading.

- [ ] **Step 4: Run all unit tests**

Run: `python -m pytest -v`
Expected: all tests pass without an API request.

### Task 4: Interactive console

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement the minimal console loop**

Use `asyncio.run`, initialize settings and the Agent once, call `await Runner.run(agent, user_input)` for each non-empty prompt, print `result.final_output`, and stop on case-insensitive `exit`. Catch EOF/keyboard interruption cleanly and avoid printing raw API exceptions that could expose sensitive details.

- [ ] **Step 2: Validate imports and syntax**

Run: `python -m compileall app main.py tests`
Expected: exit code 0 and all Python files compile.

### Task 5: Learning-focused documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write setup and concept documentation**

Explain what an Agent, LLM and tool are; show the required architecture diagram; walk through the Sentinel agent loop; provide Python 3.12 virtual-environment, dependency installation, `.env`, run and test commands; identify exactly which mock tool files a future Binance MCP integration replaces.

- [ ] **Step 2: Check the documented commands and project structure**

Run the documented test and compile commands and compare `find` output with the requested structure.

### Task 6: Final verification

**Files:**
- Review: all created files

- [ ] **Step 1: Install dependencies if they are not already available**

Run: `python -m pip install -r requirements.txt`
Expected: dependencies install successfully in the active virtual environment.

- [ ] **Step 2: Run fresh tests**

Run: `python -m pytest -v`
Expected: all tests pass, with no OpenAI API call.

- [ ] **Step 3: Run fresh syntax validation**

Run: `python -m compileall app main.py tests`
Expected: exit code 0.

- [ ] **Step 4: Inspect status and final tree**

Run: `git status --short` and `find . -maxdepth 3 -type f | sort` with generated caches excluded from the reported structure.
Expected: only intentional Phase 1 project and documentation files are present.

