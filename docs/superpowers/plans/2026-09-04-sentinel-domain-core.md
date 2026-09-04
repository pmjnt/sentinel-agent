# Sentinel Deterministic Domain Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Sentinel's typed, deterministic portfolio, policy, rebalance, and risk core with no LLM or network dependency.

**Architecture:** Replace the single `app/models.py` module with focused domain-model modules, then add pure service functions that calculate allocations, detect violations, build a draft rebalance plan, and evaluate risk. Existing mock tools remain temporarily compatible during this checkpoint; later plans replace their data source with Binance MCP.

**Tech Stack:** Python 3.12, Pydantic 2, `Decimal`, pytest

---

## File map

```text
app/models/portfolio.py  Portfolio asset and portfolio values
app/models/policy.py     Policy, patch, and policy-violation values
app/models/market.py     Market data and volatility
app/models/trade.py      Proposed action and plan values
app/models/risk.py       Deterministic risk decision
app/services/portfolio_service.py  Portfolio arithmetic
app/services/policy_service.py     Patch merge and violation checks
app/services/rebalance_service.py  Draft corrective proposal
app/services/risk_service.py       Blocking/approval priority
```

`models` contain data and field validation. `services` contain business rules. Neither package imports the Agents SDK, LiteLLM, FastAPI, or MCP.

### Task 1: Split and strengthen domain models

**Files:**
- Delete: `app/models.py`
- Create: `app/models/__init__.py`
- Create: `app/models/portfolio.py`
- Create: `app/models/market.py`
- Create: `app/models/policy.py`
- Create: `app/models/trade.py`
- Create: `app/models/risk.py`
- Modify: `app/tools/portfolio.py`
- Modify: `app/tools/market.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_domain_models.py`

- [x] **Step 1: Write failing model tests**

Create tests that prove symbols normalize to uppercase, negative financial values are rejected, policy weights must be between zero and one, and the new models import from focused modules:

```python
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy
from app.models.portfolio import PortfolioAsset


def test_asset_symbol_is_normalized() -> None:
    asset = PortfolioAsset(symbol=" btc ", amount=Decimal("0.05"), usd_value=Decimal("5500"))
    assert asset.symbol == "BTC"


def test_negative_asset_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PortfolioAsset(symbol="BTC", amount=Decimal("0.05"), usd_value=Decimal("-1"))


def test_policy_weight_outside_zero_to_one_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PortfolioPolicy(max_asset_weight=Decimal("1.1"))


def test_market_data_requires_supported_fields() -> None:
    market = MarketData(
        symbol="btcusdt",
        price=Decimal("110000"),
        change_24h_percent=Decimal("-4.2"),
        volatility=Volatility.HIGH,
        estimated_slippage_percent=Decimal("0.05"),
    )
    assert market.symbol == "BTCUSDT"
```

- [x] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_domain_models.py -q
```

Expected: collection fails because `app.models` is still a module rather than the new package.

- [x] **Step 3: Implement focused Pydantic models**

Use a shared symbol normalizer within each model that accepts a symbol. Define:

```python
class PortfolioAsset(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    amount: Decimal = Field(ge=0)
    usd_value: Decimal = Field(ge=0)
    weight: Decimal = Field(default=Decimal("0"), ge=0, le=1)


class Portfolio(BaseModel):
    model_config = ConfigDict(frozen=True)
    assets: list[PortfolioAsset]
    total_usd_value: Decimal = Field(ge=0)
```

Define the exact model surface below. Use `str, Enum` for every enum and frozen Pydantic models for data:

```text
Volatility: LOW, MEDIUM, HIGH
MarketData: symbol, price, change_24h_percent, volatility, estimated_slippage_percent
MarketDataError: symbol, error
MarketDataResult: MarketData | MarketDataError

PortfolioPolicy:
  min_stablecoin_weight: Decimal | None = None (0..1)
  max_asset_weight: Decimal | None = None (0..1)
  block_high_volatility: bool = False
  max_trade_usd_without_approval: Decimal | None = None (>= 0)

PolicyPatch: the same nullable field types and defaults; model_fields_set distinguishes
an absent field from an explicit null

ViolationType: MAX_ASSET_WEIGHT, MIN_STABLECOIN_WEIGHT
ViolationSeverity: INFO, WARNING, CRITICAL
PolicyViolation: type, asset, current_value, allowed_value, severity, explanation

TradeSide: BUY, SELL
TradeAction: symbol, side, amount, estimated_usd_value, reason
PlanStatus: DRAFT, BLOCKED, REQUIRES_APPROVAL, SAFE_TO_PROPOSE, APPROVED,
            REJECTED, EXECUTED, FAILED
RebalancePlan: violations, actions, status=DRAFT, explanation

RiskStatus: BLOCKED, REQUIRES_APPROVAL, SAFE_TO_PROPOSE
RiskReasonCode: HIGH_VOLATILITY, APPROVAL_THRESHOLD_EXCEEDED,
                NO_RESTRICTION_TRIGGERED
RiskDecision: status, reason_codes, reasons
```

Use `Decimal` for all authoritative amounts, values, percentages, and weights. Validate normalized symbols as non-empty after trimming.

Keep `app/models/__init__.py` empty. Update mock-tool imports to their exact source modules. Update the temporary fixtures to the SRD scenario:

```text
BTC  0.05       $5,500
ETH  0.58139535 $2,500
USDT 2,000      $2,000
```

Add BTC/ETH slippage to mock market values. Preserve unsupported-symbol behavior by returning `MarketDataError`; annotate the tool function with the `MarketDataResult` union. Do not represent a failed lookup as a partially empty successful `MarketData`.

- [x] **Step 4: Update existing tool tests for the typed models**

Update `tests/test_portfolio.py` to expect `Decimal("10000")` and 55/25/20 fixture values. Update `tests/test_market.py` to expect `Decimal` fields, slippage, and the explicit unsupported result type.

- [x] **Step 5: Run model and existing tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_domain_models.py tests/test_portfolio.py tests/test_market.py tests/test_agent.py -q
```

Expected: all selected tests pass.

- [x] **Step 6: Commit**

```bash
git add app/models app/models.py app/tools tests/unit tests/test_portfolio.py tests/test_market.py
git commit -m "refactor: split Sentinel domain models"
```

### Task 2: Deterministic portfolio calculation

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/portfolio_service.py`
- Create: `tests/unit/test_portfolio_service.py`

- [x] **Step 1: Write failing calculation tests**

Cover total value, weights, and invalid empty/zero portfolios:

```python
from decimal import Decimal

import pytest

from app.models.portfolio import PortfolioAsset
from app.services.portfolio_service import calculate_portfolio


def test_calculates_total_and_asset_weights() -> None:
    portfolio = calculate_portfolio([
        PortfolioAsset(symbol="BTC", amount=Decimal("0.05"), usd_value=Decimal("5500")),
        PortfolioAsset(symbol="ETH", amount=Decimal("0.58"), usd_value=Decimal("2500")),
        PortfolioAsset(symbol="USDT", amount=Decimal("2000"), usd_value=Decimal("2000")),
    ])
    assert portfolio.total_usd_value == Decimal("10000")
    assert {asset.symbol: asset.weight for asset in portfolio.assets} == {
        "BTC": Decimal("0.55"),
        "ETH": Decimal("0.25"),
        "USDT": Decimal("0.20"),
    }


def test_rejects_portfolio_with_zero_total() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_portfolio([])
```

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_portfolio_service.py -q
```

Expected: import fails because the service does not exist.

- [x] **Step 3: Implement `calculate_portfolio`**

Sum `usd_value` with `Decimal`, reject non-positive totals, and return copied immutable assets with deterministic weights. Do not use `float` or trust an externally supplied total.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_portfolio_service.py -q
```

Expected: two tests pass.

- [x] **Step 5: Commit**

```bash
git add app/services tests/unit/test_portfolio_service.py
git commit -m "feat: calculate portfolio allocations deterministically"
```

### Task 3: Policy patching and violation detection

**Files:**
- Create: `app/services/policy_service.py`
- Create: `tests/unit/test_policy_service.py`

- [ ] **Step 1: Write failing patch tests**

Verify absent fields remain unchanged and explicit `None` removes an optional rule:

```python
def test_patch_changes_only_explicit_fields() -> None:
    current = PortfolioPolicy(
        min_stablecoin_weight=Decimal("0.30"),
        max_asset_weight=Decimal("0.40"),
        block_high_volatility=True,
        max_trade_usd_without_approval=Decimal("1000"),
    )
    updated = apply_policy_patch(current, PolicyPatch(max_asset_weight=Decimal("0.45")))
    assert updated.max_asset_weight == Decimal("0.45")
    assert updated.min_stablecoin_weight == Decimal("0.30")


def test_explicit_null_removes_optional_rule() -> None:
    current = PortfolioPolicy(min_stablecoin_weight=Decimal("0.30"))
    updated = apply_policy_patch(current, PolicyPatch(min_stablecoin_weight=None))
    assert updated.min_stablecoin_weight is None
```

- [ ] **Step 2: Write failing violation tests**

Using the 55/25/20 portfolio and 30/40 policy, assert exactly:

- one `MAX_ASSET_WEIGHT` violation for BTC at 0.55 versus 0.40;
- one `MIN_STABLECOIN_WEIGHT` violation for USDT at 0.20 versus 0.30;
- no violation for a compliant 40/30/30 portfolio.

- [ ] **Step 3: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_service.py -q
```

Expected: import fails because `policy_service.py` does not exist.

- [ ] **Step 4: Implement patching and detection**

Create two public functions with these exact typed signatures:

- `apply_policy_patch(current: PortfolioPolicy, patch: PolicyPatch) -> PortfolioPolicy`
- `find_policy_violations(portfolio: Portfolio, policy: PortfolioPolicy, stablecoin_symbols: frozenset[str] = frozenset({"USDT"})) -> list[PolicyViolation]`

Use `patch.model_fields_set` for merge semantics. Sum all configured stablecoin weights for the minimum rule. Exclude configured stablecoins from the maximum crypto-asset rule. Return violations in portfolio order, with the stablecoin minimum violation last.

- [ ] **Step 5: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_service.py -q
```

Expected: all patch and violation tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/services/policy_service.py tests/unit/test_policy_service.py
git commit -m "feat: apply portfolio policies deterministically"
```

### Task 4: Deterministic rebalance proposal

**Files:**
- Create: `app/services/rebalance_service.py`
- Create: `tests/unit/test_rebalance_service.py`

- [ ] **Step 1: Write failing proposal tests**

For BTC 55%, max 40%, total $10,000, and BTC price $110,000, assert one SELL proposal:

```python
assert action.symbol == "BTCUSDT"
assert action.side is TradeSide.SELL
assert action.estimated_usd_value == Decimal("1500.00")
assert action.amount == Decimal("0.01363636")
assert plan.status is PlanStatus.DRAFT
```

Also assert that no action is created for only a stablecoin-shortfall violation when no overweight asset exists, and that missing BTC market data raises a typed `MissingMarketDataError` rather than fabricating a price.

- [ ] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_rebalance_service.py -q
```

Expected: import fails because the rebalance service does not exist.

- [ ] **Step 3: Implement proposal building**

Create `build_rebalance_plan(portfolio: Portfolio, violations: list[PolicyViolation], market_data: dict[str, MarketData]) -> RebalancePlan`.

For each maximum-weight violation, calculate:

```text
excess USD = (current weight - allowed weight) × portfolio total
amount = excess USD / current market price
```

Quantize USD to `0.01` and asset amount to `0.00000001` using `ROUND_HALF_UP`. A corresponding stablecoin-shortfall violation is explained by the same sell proceeds; it must not create a duplicate trade.

- [ ] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_rebalance_service.py -q
```

Expected: all proposal tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/rebalance_service.py tests/unit/test_rebalance_service.py
git commit -m "feat: build deterministic rebalance proposals"
```

### Task 5: Deterministic RiskEngine

**Files:**
- Create: `app/services/risk_service.py`
- Create: `tests/unit/test_risk_service.py`

- [ ] **Step 1: Write failing risk-priority tests**

Cover the SRD-required cases:

```text
HIGH volatility + blocking policy → BLOCKED
MEDIUM volatility + blocking policy → not BLOCKED
$1,500 action + $1,000 threshold → REQUIRES_APPROVAL
HIGH volatility + $1,500 action → BLOCKED (blocking wins)
$500 action + $1,000 threshold + non-HIGH market → SAFE_TO_PROPOSE
```

Assert machine-readable reason codes as well as statuses.

- [ ] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_risk_service.py -q
```

Expected: import fails because the risk service does not exist.

- [ ] **Step 3: Implement risk evaluation**

Create `evaluate_rebalance_risk(policy: PortfolioPolicy, plan: RebalancePlan, market_data: dict[str, MarketData]) -> RiskDecision`.

Evaluate all applicable market records for proposed actions. Return immediately with `HIGH_VOLATILITY` if blocking conditions exist. Only then return `APPROVAL_THRESHOLD_EXCEEDED` when necessary. Otherwise return `SAFE_TO_PROPOSE` with `NO_RESTRICTION_TRIGGERED`. Do not mutate the input plan and do not use the LLM.

- [ ] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_risk_service.py -q
```

Expected: all five risk cases pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/risk_service.py tests/unit/test_risk_service.py
git commit -m "feat: enforce deterministic portfolio risk rules"
```

### Task 6: Domain-core documentation and verification

**Files:**
- Create: `docs/architecture.md`
- Create: `docs/development-guidelines.md`
- Create: `docs/testing.md`
- Modify: `README.md`

- [ ] **Step 1: Document the implemented boundary**

Document:

- module responsibility and dependency direction;
- why domain services cannot import agent/MCP/API packages;
- `Decimal`, Pydantic, enum, import, `__init__.py`, side-effect, and typed-error rules;
- TDD commands and external-call prohibition in unit tests;
- the fact that this checkpoint implements the deterministic core while the existing mock runtime remains temporary until the Binance MCP plan is completed.

- [ ] **Step 2: Run complete verification**

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: all Python and JavaScript tests pass, compilation succeeds, and no whitespace error is reported.

- [ ] **Step 3: Verify dependency boundaries**

```bash
rg -n 'from (agents|fastapi|mcp)|import (agents|fastapi|mcp)' app/models app/services
```

Expected: no matches.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md docs/architecture.md docs/development-guidelines.md docs/testing.md
git commit -m "docs: explain Sentinel domain development rules"
```

## Completion boundary

This plan ends when the deterministic core and its documentation pass locally. It does not implement LLM policy parsing, Binance MCP, FastAPI, or UI integration. Those are separate plans so their integration failures cannot obscure financial-rule correctness.
