# Hybrid Trading Universe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow normal approval for configured popular Spot USDT pairs and plan-scoped override approval for other Binance-verified pairs.

**Architecture:** Binance `exchange-info` provides authoritative symbol capabilities. Deterministic Python validates eligibility and classifies default versus override-required symbols; the execution state machine and UI enforce two-stage approval for non-default symbols.

**Tech Stack:** Python 3.12, Pydantic, Binance CLI, FastAPI, JavaScript, pytest

---

### Task 1: Retrieve verified Binance symbol information

**Files:**
- Create: `app/models/symbol.py`
- Modify: `app/binance/schemas.py`
- Modify: `app/gateways.py`
- Modify: `app/binance/gateway.py`
- Test: `tests/unit/test_binance_market_gateway.py`

- [ ] **Step 1: Add failing gateway tests**

Use Binance's actual `exchangeInfo` response and expect:

```python
TradingSymbolInfo(
    symbol="SOLUSDT",
    status="TRADING",
    base_asset="SOL",
    quote_asset="USDT",
    order_types=("LIMIT", "MARKET"),
    is_spot_trading_allowed=True,
    quote_order_qty_market_allowed=True,
)
```

Also verify an empty or mismatched `symbols` response returns a safe error.

- [ ] **Step 2: Run tests and observe failure**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_market_gateway.py -q`

Expected: fail because symbol-info models and gateway method do not exist.

- [ ] **Step 3: Add immutable domain results**

```python
class TradingSymbolInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    order_types: tuple[str, ...]
    is_spot_trading_allowed: bool
    quote_order_qty_market_allowed: bool


class TradingSymbolInfoError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    symbol: str
    error: str
```

- [ ] **Step 4: Map and call `exchange-info`**

Add Pydantic payload aliases for `baseAsset`, `quoteAsset`, `orderTypes`,
`isSpotTradingAllowed`, and `quoteOrderQtyMarketAllowed`. Implement a public call:

```python
await self._runner.run([
    "spot", "exchange-info", "--symbol", normalized,
    "--show-permission-sets", "false",
])
```

Require one matching symbol and sanitize CLI or validation failures.

- [ ] **Step 5: Run gateway tests**

Run: `.venv/bin/python -m pytest tests/unit/test_binance_market_gateway.py -q`

Expected: all gateway tests pass.

### Task 2: Classify default and override-required symbols

**Files:**
- Create: `app/services/trade_universe_service.py`
- Modify: `app/models/execution.py`
- Modify: `app/services/trade_proposal_service.py`
- Test: `tests/unit/test_trade_universe_service.py`
- Test: `tests/unit/test_trade_proposal_service.py`

- [ ] **Step 1: Add failing classification tests**

Test this default set:

```python
DEFAULT_TRADE_SYMBOLS = frozenset({
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "XRPUSDT", "ADAUSDT", "DOGEUSDT",
})
```

Verify a valid `LINKUSDT` requires override and inactive, non-USDT, non-Spot,
or no-MARKET symbols raise `TradeUniverseError`.

- [ ] **Step 2: Run tests and observe failure**

Run: `.venv/bin/python -m pytest tests/unit/test_trade_universe_service.py tests/unit/test_trade_proposal_service.py -q`

Expected: fail because classification and override plan state do not exist.

- [ ] **Step 3: Implement deterministic eligibility**

```python
def requires_symbol_override(info: TradingSymbolInfo) -> bool:
    require_trade_eligibility(info)
    return info.symbol not in DEFAULT_TRADE_SYMBOLS
```

Require `TRADING`, quote asset `USDT`, Spot, `MARKET`, and quote-order-quantity
market support.

- [ ] **Step 4: Extend the immutable plan**

Add `PENDING_SYMBOL_APPROVAL` to `ExecutionPlanStatus` and
`requires_symbol_override: bool = False` to `ExecutionPlan`. Pass verified
`symbol_info` into `create_trade_plan`, remove the BTC/ETH-only rejection, and
start non-default plans in `PENDING_SYMBOL_APPROVAL`.

- [ ] **Step 5: Run service tests**

Run: `.venv/bin/python -m pytest tests/unit/test_trade_universe_service.py tests/unit/test_trade_proposal_service.py -q`

Expected: all service tests pass.

### Task 3: Revalidate symbol eligibility before execution

**Files:**
- Modify: `app/agent/controlled_tools.py`
- Modify: `app/services/execution_service.py`
- Modify: `app/binance/gateway.py`
- Modify: affected test fake gateways
- Test: `tests/unit/test_controlled_tools.py`
- Test: `tests/unit/test_execution_service.py`

- [ ] **Step 1: Add failing orchestration tests**

Test that proposal awaits `get_symbol_info`, non-default symbols create override
plans, symbol-info failures return a sanitized tool error, and execution blocks
without order submission when a symbol becomes inactive.

- [ ] **Step 2: Run tests and observe failure**

Run: `.venv/bin/python -m pytest tests/unit/test_controlled_tools.py tests/unit/test_execution_service.py -q`

Expected: fail because proposal and execution do not retrieve symbol info.

- [ ] **Step 3: Make proposal orchestration asynchronous**

Change `propose_trade_plan` to `async`, retrieve
`context.gateway.get_symbol_info`, and await it from the `propose_trade` function
tool. Keep Binance failures fail-closed.

- [ ] **Step 4: Revalidate before execution**

Refetch portfolio, market, and symbol info before calling `create_trade_plan`.
Validate symbol format and Binance eligibility in the gateway before order submit
and verification; remove the gateway's BTC/ETH-only constant.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/python -m pytest tests/unit/test_controlled_tools.py tests/unit/test_execution_service.py tests/unit/test_binance_market_gateway.py -q`

Expected: all focused tests pass.

### Task 4: Enforce two-stage approval in store, API, and UI

**Files:**
- Modify: `app/execution/store.py`
- Modify: `app/application.py`
- Modify: `app/api.py`
- Modify: `app/models/api.py`
- Modify: `app/services/execution_response_service.py`
- Modify: `web/app.js`
- Test: `tests/unit/test_execution_store.py`
- Test: `tests/unit/test_api.py`
- Test: `tests/test_ui.js`

- [ ] **Step 1: Add failing state and endpoint tests**

Test `approve_symbol_override` only accepts the same session's unexpired
`PENDING_SYMBOL_APPROVAL` plan, moves it to `PENDING_APPROVAL`, and normal approval
cannot skip it. Test `POST /api/plans/{plan_id}/approve-symbol`.

- [ ] **Step 2: Run tests and observe failure**

Run: `.venv/bin/python -m pytest tests/unit/test_execution_store.py tests/unit/test_api.py -q`

Expected: fail because the override transition and endpoint do not exist.

- [ ] **Step 3: Implement backend state transition**

Add `approve_symbol_override` to the store, execution service, application, and
FastAPI. Add `PENDING_SYMBOL_APPROVAL` to API `ExecutionStatus`. Reject must accept
both pending states while preserving expiry and session checks.

- [ ] **Step 4: Implement explicit two-stage UI**

Show `TOKEN OUTSIDE DEFAULT UNIVERSE` and `Approve token exception` for override
plans. After success, keep the same plan card and change its action to
`Approve Demo order`; only the second click may execute.

- [ ] **Step 5: Run backend and UI tests**

Run: `.venv/bin/python -m pytest tests/unit/test_execution_store.py tests/unit/test_api.py -q`

Run: `node --test tests/test_ui.js`

Expected: all tests pass.

### Task 5: Document, verify, and commit

**Files:**
- Modify: `app/agent/prompts.py`
- Modify: `README.md`

- [ ] **Step 1: Document Agent behavior and safety**

Explain default universe versus plan-scoped override and the new endpoint. Tell
the LLM that non-default symbols may be proposed but never described as approved
or executed.

- [ ] **Step 2: Run complete validation**

Run:

```text
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app main.py
node --test tests/test_ui.js
git diff --check
```

Expected: every command exits successfully.

- [ ] **Step 3: Commit implementation**

```text
git add app tests web README.md
git commit -m "feat: add hybrid trading universe approvals"
```
