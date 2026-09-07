# Adaptive Binance Market Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Sentinel create a bounded research recipe, scan real Binance Spot USDT volume, analyze selected market history, and make an evidence-driven personal judgment.

**Architecture:** The LLM controls an inspectable research plan and chooses which verified candidates to investigate. BinanceCliGateway retrieves schema-validated exchange, ticker, depth, and kline data; deterministic Python filters markets and calculates indicators; the existing Agent loop, API, and UI expose safe research results without granting arbitrary code or command execution.

**Tech Stack:** Python 3.12, Pydantic, OpenAI Agents SDK, Binance CLI, FastAPI, vanilla JavaScript, pytest, Node test runner

---

### Task 1: Complete natural response readability

**Files:**
- Modify: `app/agent/prompts.py`
- Modify: `tests/unit/test_tool_loop.py`
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Modify: `tests/test_ui.js`
- Include: `docs/superpowers/plans/2026-09-07-inline-numbered-list-rendering.md`
- Include: `docs/superpowers/plans/2026-09-07-natural-analysis-responses.md`

- [ ] **Step 1: Verify the existing failing prompt test**

Run: `.venv/bin/python -m pytest tests/unit/test_tool_loop.py -q`

Expected: fail because the prompt still requires fixed localized headings.

- [ ] **Step 2: Replace the fixed response template**

Replace the active prompt rule requiring Assessment, Rationale, Recommendation,
and Limitations with:

```text
Choose a natural response structure that fits the content and length. Use short
paragraphs, optional headings, bullets, or numbered choices when they improve
clarity. Disclose material uncertainty or missing evidence naturally; a fixed
Limitations section is not required.
```

Keep the existing grounding, no-chain-of-thought, and no-execution-claim rules.

- [ ] **Step 3: Verify response tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_tool_loop.py -q
node --test tests/test_ui.js
```

Expected: all focused tests pass, including inline ordered-list and decimal tests.

### Task 2: Add bounded market-research domain models and calculations

**Files:**
- Create: `app/models/research.py`
- Create: `app/services/market_research_service.py`
- Test: `tests/unit/test_market_research_service.py`

- [ ] **Step 1: Add failing plan and calculation tests**

Test these contracts:

```python
plan = MarketResearchPlan(
    candidate_limit=5,
    timeframes=[ResearchTimeframe.H4, ResearchTimeframe.D1],
    lookback_days=30,
    priorities=[ResearchPriority.MOMENTUM, ResearchPriority.DOWNSIDE_CONTROL],
)
assert plan.candidate_limit == 5
```

Reject duplicate/empty priorities, more than two timeframes, combinations over
1,000 candles per timeframe, and combinations producing fewer than 20 candles.
Verify quote-volume ranking excludes stablecoins and leveraged tokens. Verify
return, moving-average trend, realized volatility, maximum drawdown, and volume
change from fixed candle fixtures.

- [ ] **Step 2: Run tests and observe missing models/service**

Run: `.venv/bin/python -m pytest tests/unit/test_market_research_service.py -q`

Expected: fail during import because the research module does not exist.

- [ ] **Step 3: Implement immutable research models**

Create Pydantic models and enums:

```text
ResearchTimeframe: 15m | 1h | 4h | 1d
ResearchPriority: LIQUIDITY | MOMENTUM | DOWNSIDE_CONTROL | VOLATILITY_OPPORTUNITY
MarketResearchPlan: candidate_limit, timeframes, lookback_days, priorities
MarketTicker: symbol, price, change_24h_percent, quote_volume, observed_at
MarketScan: candidates, observed_at
MarketCandle: open_time, close_time, open, high, low, close, volume, quote_volume
TimeframeResearch: timeframe, sample_size, return_percent, trend,
  realized_volatility_percent, max_drawdown_percent, volume_change_percent
CandidateResearch: candidate, timeframes
MarketResearchResult: plan, scan, analyzed_candidates, failed_symbols
```

All financial values use `Decimal`; immutable models use `extra="forbid"`.

- [ ] **Step 4: Implement deterministic filtering and indicators**

Use explicit stablecoin symbols and leveraged suffixes `UP`, `DOWN`, `BULL`, and
`BEAR`. Rank descending by `quote_volume`, then symbol for stable ties. Calculate:

```text
return = (last_close / first_close - 1) * 100
realized volatility = population standard deviation of close-to-close returns
max drawdown = maximum percentage decline from a prior close peak
volume change = (second-half average / first-half average - 1) * 100
trend = short moving average versus long moving average with a 0.5% neutral band
```

- [ ] **Step 5: Run service tests**

Run: `.venv/bin/python -m pytest tests/unit/test_market_research_service.py -q`

Expected: all tests pass.

### Task 3: Retrieve Binance market universe and klines safely

**Files:**
- Modify: `app/binance/schemas.py`
- Modify: `app/binance/gateway.py`
- Modify: `app/gateways.py`
- Test: `tests/unit/test_binance_market_gateway.py`

- [ ] **Step 1: Add failing gateway mapping tests**

Use actual Binance shapes. Expect `get_market_universe()` to call:

```text
spot exchange-info --symbol-status TRADING --show-permission-sets false
spot ticker24hr --symbols <JSON batch of at most 100> --type FULL
```

Verify only eligible Spot USDT symbols reach ticker batches. Verify bulk ticker
fields `lastPrice`, `priceChangePercent`, `quoteVolume`, and `closeTime` map to
`MarketTicker`. Expect `get_market_candles()` to call:

```text
spot klines --symbol BTCUSDT --interval 4h --limit 180
```

and map the 12-field Binance array to `MarketCandle`. Test malformed payloads,
mismatched symbols, invalid intervals, and batch size.

- [ ] **Step 2: Run gateway tests and observe failure**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_market_gateway.py -q`

Expected: fail because gateway methods and schemas do not exist.

- [ ] **Step 3: Add exact external payload schemas**

Add a bulk ticker schema with required quote volume and close time. Add a strict
12-position kline payload adapter. Keep the existing single-symbol market schema
unchanged to avoid weakening current validation.

- [ ] **Step 4: Implement bounded gateway reads**

Add protocol and gateway methods:

```python
async def get_market_universe(self) -> tuple[MarketTicker, ...]: ...
async def get_market_candles(
    self, symbol: str, timeframe: ResearchTimeframe, limit: int
) -> tuple[MarketCandle, ...]: ...
```

Batch ticker symbols in groups of 100, serialize only with `json.dumps`, validate
symbol identity, cap kline limit at 1,000, retry each public read once, and return
sanitized typed errors instead of provider output.

- [ ] **Step 5: Run gateway tests**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_market_gateway.py -q`

Expected: all gateway tests pass.

### Task 4: Add the adaptive research tools to the Agent loop

**Files:**
- Modify: `app/agent/run_context.py`
- Modify: `app/agent/controlled_tools.py`
- Modify: `app/agent/tool_loop.py`
- Modify: `app/agent/prompts.py`
- Test: `tests/unit/test_controlled_tools.py`
- Test: `tests/unit/test_tool_loop.py`

- [ ] **Step 1: Add failing controlled-loop tests**

Test this enforced sequence:

```text
set_market_research_plan
→ scan_top_markets
→ analyze_market_history for at least two scanned symbols
→ finalize_market_research
```

Verify scanning fails without a plan, history analysis rejects unscanned symbols,
no more than five candidates can be analyzed deeply, partial failures are recorded,
and finalization requires at least two successful candidate analyses.

- [ ] **Step 2: Run focused tests and observe failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_controlled_tools.py tests/unit/test_tool_loop.py -q
```

Expected: fail because the four research tools and run-context state do not exist.

- [ ] **Step 3: Add run-scoped research state and events**

Store the validated plan, latest scan, candidate results, failed symbols, and final
research result in `SentinelRunContext`. Add ordered events for plan accepted,
scan completed, candidate analyzed, and research finalized. No research state is
persisted as current market truth across conversations.

- [ ] **Step 4: Implement four function tools**

Expose only:

```text
set_market_research_plan(candidate_limit, timeframes, lookback_days, priorities)
scan_top_markets()
analyze_market_history(symbol)
finalize_market_research()
```

Tool parameters use enum/Literal values rather than CLI strings. Python derives
kline limits from timeframe and lookback. Fetch the selected timeframes
concurrently, propagate cancellation, sanitize failures, and never expose a raw
command tool.

- [ ] **Step 5: Update Agent behavior and completion validation**

Tell Sentinel to use adaptive research for opportunity, allocation-candidate, or
market-comparison requests. Require a finalized result before comparative advice.
Add a calm, direct, evidence-driven personality; permit disagreement and a clear
preferred option. Increase the controlled tool allowlist assertions to 12 tools.

- [ ] **Step 6: Run Agent tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_controlled_tools.py tests/unit/test_tool_loop.py -q
```

Expected: all focused tests pass.

### Task 5: Stream safe research activity and structured evidence

**Files:**
- Modify: `app/models/api.py`
- Modify: `app/agent/streaming.py`
- Modify: `app/application.py`
- Create: `app/services/research_response_service.py`
- Modify: `web/app.js`
- Test: `tests/unit/test_streaming_activity.py`
- Test: `tests/unit/test_tool_loop_application.py`
- Test: `tests/unit/test_api.py`
- Test: `tests/test_ui.js`

- [ ] **Step 1: Add failing activity, response, and UI tests**

Expect activity kinds `RESEARCH_PLAN`, `MARKET_SCAN`, `MARKET_HISTORY`, and
`MARKET_RESEARCH`. Expect completed SSE JSON to contain `market_research`.
Expect the collapsed Verified tool facts panel to list scan time, top quote-volume
candidates, analyzed timeframes, and failed symbols without raw candles.

- [ ] **Step 2: Run focused tests and observe failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_streaming_activity.py tests/unit/test_tool_loop_application.py tests/unit/test_api.py -q
node --test tests/test_ui.js
```

Expected: fail because research activity and structured response fields do not exist.

- [ ] **Step 3: Extend structured application results**

Carry the latest finalized `MarketResearchResult` through `ToolLoopResult`,
`SentinelResponse`, and `StructuredSentinelResponse`. Model prose is accepted as
qualitative interpretation only after finalization. Deterministic response text
and UI evidence render verified values separately.

- [ ] **Step 4: Add safe streaming labels and evidence rendering**

Map the four research tool names to generic activity labels. Render only summary
models in UI DOM nodes using `textContent`; do not use `innerHTML`, raw klines,
tool arguments, provider errors, prompts, or chain-of-thought.

- [ ] **Step 5: Run response and UI tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_streaming_activity.py tests/unit/test_tool_loop_application.py tests/unit/test_api.py -q
node --test tests/test_ui.js
```

Expected: all focused tests pass.

### Task 6: Document, verify, and commit

**Files:**
- Modify: `README.md`
- Modify: `docs/agent-guidelines.md`
- Modify: `docs/testing.md`

- [ ] **Step 1: Document the adaptive boundary**

Explain that the LLM chooses a validated research recipe and makes qualitative
judgments, while Python retrieves data, calculates indicators, and protects
execution. Document Binance command boundaries, plan limits, data freshness,
activity events, and the difference between a recommendation and approval.

- [ ] **Step 2: Run complete verification**

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app main.py
node --test tests/test_ui.js
git diff --check
```

Expected: every command exits successfully and no test calls Binance or an LLM.

- [ ] **Step 3: Commit implementation**

```bash
git add app tests web README.md docs
git commit -m "feat: add adaptive Binance market research"
```
