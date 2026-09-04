# Sentinel Binance CLI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Sentinel's mock and unsupported MCP runtime paths with read-only Binance Demo Trading portfolio and market data through the official `binance-cli`.

**Architecture:** The Agent keeps two stable function tools, created from a `PortfolioMarketGateway` port. `BinanceCliGateway` is the only adapter allowed to choose fixed read commands; `BinanceCliRunner` executes argument arrays without a shell and parses JSON. Pydantic validates exchange payloads before deterministic domain services or the LLM can use them.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, LiteLLM, Pydantic 2, Binance Skills Hub `binance-cli` 2.1.1, pytest

---

### Task 1: Binance Demo configuration

**Files:**
- Modify: `app/config.py`
- Modify: `.env.example`
- Modify: `tests/test_config.py`

- [x] **Step 1: Write failing configuration tests**

Add tests asserting that `Settings` defaults to `BINANCE_API_ENV=demo` and
`BINANCE_CLI_PATH=binance-cli`, accepts optional credentials, rejects unsupported
environments, and raises a safe error naming missing variables without values when
account credentials are requested.

- [x] **Step 2: Run test to verify RED**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`

Expected: imports or assertions for `BinanceEnvironment` and Binance settings fail.

- [x] **Step 3: Implement minimal configuration**

Add:

```python
class BinanceEnvironment(str, Enum):
    DEMO = "demo"
    PROD = "prod"

class BinanceCredentials(BaseModel):
    api_key: str
    secret_key: str

def require_binance_credentials(settings: Settings) -> BinanceCredentials:
    ...
```

Extend `Settings` and `load_settings()` with `binance_environment`,
`binance_cli_path`, `binance_api_key`, and `binance_secret_key`. Keep credentials
optional at application startup so public market commands remain usable. Add only
empty/example Binance variables to `.env.example`.

- [x] **Step 4: Run test to verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`

- [x] **Step 5: Commit**

```bash
git add app/config.py .env.example tests/test_config.py
git commit -m "feat: configure Binance Demo access"
```

### Task 2: Safe JSON CLI runner

**Files:**
- Create: `app/binance/__init__.py`
- Create: `app/binance/runner.py`
- Create: `tests/unit/test_binance_cli_runner.py`

- [x] **Step 1: Write failing runner tests**

Patch `asyncio.create_subprocess_exec` with a fake process and assert:

- executable and arguments are separate positional values;
- `shell=True` cannot be supplied;
- Demo environment and credentials are passed only in the child environment;
- valid JSON is returned;
- timeout, non-zero exit, empty output, and invalid JSON raise
  `BinanceCliError` whose message contains no stdout, stderr, API key, or secret.

- [x] **Step 2: Run test to verify RED**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_cli_runner.py -q`

Expected: `app.binance.runner` cannot be imported.

- [x] **Step 3: Implement the runner**

Implement:

```python
class JsonCommandRunner(Protocol):
    async def run(
        self,
        arguments: Sequence[str],
        *,
        authenticated: bool = False,
    ) -> Any: ...

class BinanceCliRunner:
    async def run(...):
        process = await asyncio.create_subprocess_exec(
            self._executable,
            *arguments,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_environment,
        )
        ...
```

Use `asyncio.wait_for`, `json.loads`, a 15-second default timeout, and sanitized
fixed error messages. Authenticated calls use `require_binance_credentials`.

- [x] **Step 4: Run test to verify GREEN**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_cli_runner.py -q`

- [x] **Step 5: Commit**

```bash
git add app/binance tests/unit/test_binance_cli_runner.py
git commit -m "feat: run Binance CLI safely"
```

### Task 3: Portfolio gateway

**Files:**
- Create: `app/gateways.py`
- Create: `app/binance/schemas.py`
- Create: `app/binance/gateway.py`
- Modify: `app/models/portfolio.py`
- Create: `tests/unit/test_binance_portfolio_gateway.py`

- [x] **Step 1: Write failing portfolio mapping tests**

Use a fake `JsonCommandRunner` with account and ticker fixtures. Assert the gateway
calls exactly:

```text
spot get-account --omit-zero-balances true
spot ticker-price
```

Assert amount equals `free + locked`, USDT is worth one USD, other assets use the
matching `ASSETUSDT` price, and `calculate_portfolio()` supplies authoritative
total and weights. Assert zero balances are excluded and a missing price fails
instead of silently dropping an asset. Assert the result is labelled
`BINANCE_DEMO`.

- [x] **Step 2: Run test to verify RED**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_portfolio_gateway.py -q`

Expected: gateway modules or data-source field are missing.

- [x] **Step 3: Implement schemas, port, and portfolio mapping**

Define `PortfolioMarketGateway` in `app/gateways.py`. In `schemas.py`, define
strict transport models for account balances and price ticker rows. In
`gateway.py`, implement `BinanceCliGateway.get_portfolio()` using only the two
fixed commands. Add a `data_source` field whose values are `BINANCE_DEMO` and
`BINANCE_PROD` to the portfolio model.

- [x] **Step 4: Run test to verify GREEN**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_portfolio_gateway.py -q`

- [x] **Step 5: Commit**

```bash
git add app/gateways.py app/binance app/models/portfolio.py tests/unit/test_binance_portfolio_gateway.py
git commit -m "feat: map Binance Demo portfolio data"
```

### Task 4: Market gateway

**Files:**
- Modify: `app/binance/schemas.py`
- Modify: `app/binance/gateway.py`
- Modify: `app/models/market.py`
- Create: `tests/unit/test_binance_market_gateway.py`

- [x] **Step 1: Write failing market mapping tests**

Use ticker and depth fixtures. Assert normalized `BTCUSDT` calls exactly:

```text
spot ticker24hr --symbol BTCUSDT
spot depth --symbol BTCUSDT --limit 100
```

Assert price/change mapping, Demo source label, LOW/MEDIUM/HIGH thresholds at
absolute 24-hour moves of 2% and 4%, and deterministic slippage for a $1,000
reference sale. Assert malformed symbols make zero CLI calls; unsupported symbol,
invalid schema, and insufficient bid depth return `MarketDataError`.

- [x] **Step 2: Run test to verify RED**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_market_gateway.py -q`

Expected: market methods or schemas are missing.

- [x] **Step 3: Implement market mapping**

Validate symbols against `^[A-Z0-9]{5,20}$`. Add strict ticker/depth schemas,
`classify_volatility(change_percent)`, and
`estimate_sell_slippage(bids, price, reference_usd=Decimal("1000"))`. Convert
known CLI/data failures to a clear `MarketDataError`; do not return guessed values.
Add the same `data_source` field to `MarketData`.

- [x] **Step 4: Run test to verify GREEN**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_market_gateway.py -q`

- [ ] **Step 5: Commit**

```bash
git add app/binance app/models/market.py tests/unit/test_binance_market_gateway.py
git commit -m "feat: map Binance Demo market data"
```

### Task 5: Bind gateway-backed tools to Sentinel

**Files:**
- Modify: `app/tools/portfolio.py`
- Modify: `app/tools/market.py`
- Modify: `app/agent/prompts.py`
- Modify: `app/agent/sentinel.py`
- Modify: `main.py`
- Modify: `tests/test_portfolio.py`
- Modify: `tests/test_market.py`
- Modify: `tests/test_agent.py`

- [ ] **Step 1: Write failing Agent/tool tests**

Create a fake `PortfolioMarketGateway`. Assert tool factories retain the names
`get_portfolio` and `get_market_data`, the Agent is built with those tools, mock
constants no longer exist, and instructions require explicit Binance Demo labels
and prohibit claims about real holdings or trades.

- [ ] **Step 2: Run test to verify RED**

Run: `.venv/bin/python -m pytest tests/test_portfolio.py tests/test_market.py tests/test_agent.py -q`

Expected: tool factories and gateway argument are missing.

- [ ] **Step 3: Implement tool factories and runtime composition**

Implement `create_portfolio_tool(gateway)` and `create_market_data_tool(gateway)`
as closures. Change `create_sentinel_agent(settings, gateway)` and create the
runner/gateway in `main.py`. Update startup text to state Binance Demo. On a tool
failure, report that Binance data could not be verified and do not offer a risk
recommendation.

- [ ] **Step 4: Run test to verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_portfolio.py tests/test_market.py tests/test_agent.py -q`

- [ ] **Step 5: Commit**

```bash
git add app/tools app/agent main.py tests/test_portfolio.py tests/test_market.py tests/test_agent.py
git commit -m "feat: use Binance Demo tools in Sentinel"
```

### Task 6: Remove unsupported MCP runtime

**Files:**
- Delete: `app/mcp/`
- Delete: `app/models/mcp.py`
- Delete: `tests/unit/test_mcp_callback.py`
- Delete: `tests/unit/test_mcp_catalog.py`
- Delete: `tests/unit/test_mcp_dependencies.py`
- Delete: `tests/unit/test_mcp_discovery.py`
- Delete: `docs/binance-mcp.md`
- Delete: `web/oauth/client-metadata.json`
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Write/adjust a dependency-boundary test**

Add an assertion to the runner/gateway tests that importing the normal application
does not require `mcp` or `httpx2`. Search for runtime `app.mcp` imports and record
the expected RED state before deletion.

- [ ] **Step 2: Run boundary check to verify RED**

Run: `rg -n "app\.mcp|from mcp|import mcp|httpx2" app requirements.txt`

Expected: MCP implementation and dependencies are still present.

- [ ] **Step 3: Remove MCP code and update documentation**

Delete the listed files with `apply_patch`, remove `mcp` and `httpx2` from
requirements, and document the Skills Hub architecture, Demo key creation,
read-only allowlist, installation, and run commands. Keep historical design/plan
documents under `docs/superpowers/` as decision records.

- [ ] **Step 4: Verify boundary is GREEN**

Run: `rg -n "app\.mcp|from mcp|import mcp|httpx2" app requirements.txt`

Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add -A app tests requirements.txt README.md docs web/oauth
git commit -m "refactor: replace Binance MCP with Skills Hub"
```

### Task 7: Install CLI and verify safely

**Files:**
- Modify: `docs/superpowers/plans/2026-09-04-sentinel-binance-cli.md`

- [ ] **Step 1: Download the official installer for review**

Download the installer from the signed `binance/binance-cli` v2.1.1 GitHub release
to a temporary file. Inspect it before execution; do not pipe network output
directly into a shell.

- [ ] **Step 2: Install and inspect CLI schema**

Run the reviewed installer, then:

```bash
binance-cli --version
binance-cli spot get-account --help
binance-cli spot ticker-price --help
binance-cli spot ticker24hr --help
binance-cli spot depth --help
```

Expected version: `2.1.1` or a later compatible official release. If actual command
names or JSON differ from the official references, update fixtures and mappings
through a new RED/GREEN cycle before continuing.

- [ ] **Step 3: Verify public Demo market data**

Run:

```bash
BINANCE_API_ENV=demo binance-cli spot ticker24hr --symbol BTCUSDT
```

Do not display or pass credentials. Validate the returned JSON shape only.

- [ ] **Step 4: Run all offline checks**

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

- [ ] **Step 5: User-only authenticated verification**

The user creates a Binance Demo key and writes it directly to local `.env`:

```dotenv
BINANCE_API_ENV=demo
BINANCE_API_KEY=
BINANCE_SECRET_KEY=
```

The user fills the two empty values locally and never sends them through chat.

Run Sentinel without printing the environment. Confirm the tool activity and final
answer label all portfolio data as Binance Demo. No command containing `order`,
`trade`, `transfer`, `withdraw`, or generic `request` may run.

### Task 8: Remove obsolete hosted OAuth metadata

**Files:**
- No local source changes beyond Task 6

- [ ] **Step 1: Redeploy only `web/`**

Deploy the static web directory to the existing Vercel project after the local
metadata file has been removed.

- [ ] **Step 2: Verify removal and UI availability**

Assert the former `/oauth/client-metadata.json` URL returns 404 while `/` returns
200. This removes the unused OAuth identity document without deleting the demo UI.

- [ ] **Step 3: Record final status**

Show the final project tree, test counts, installed CLI version, public Demo command
result shape, and the remaining user-only step for Demo credentials.

## Completion boundary

Completion means Sentinel's normal runtime is wired only to read-only Binance Demo
CLI capabilities, all offline tests pass, and the obsolete public OAuth metadata is
gone. It does not mean live account verification, production access, trade
execution, FastAPI, database work, or Track B participation.
