# Binance Demo Controlled Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicitly approved, deterministic, idempotent Binance Demo Spot execution path without exposing order execution to the LLM.

**Architecture:** The Agent may create a validated immutable proposal through a controlled tool. A separate application service owns approval, fresh-data revalidation, execution, verification, and lifecycle persistence. The Binance adapter exposes fixed typed order methods rather than arbitrary CLI arguments.

**Tech Stack:** Python 3.12, Pydantic, OpenAI Agents SDK tools, Binance CLI Demo environment, FastAPI, vanilla JavaScript, pytest, Node test runner.

---

### Task 1: Execution policy fields

**Files:**
- Modify: `app/models/policy.py`
- Modify: `app/services/policy_service.py`
- Modify: `app/services/policy_response_service.py`
- Test: `tests/unit/test_policy_service.py`
- Test: `tests/unit/test_controlled_tools.py`

- [ ] Add failing tests for maximum trade USD, maximum slippage, and allowed symbols.
- [ ] Run focused tests and confirm failures are caused by missing fields.
- [ ] Add validated optional policy fields and LLM-facing field parsing.
- [ ] Update natural-language policy rendering.
- [ ] Run focused tests until green.

### Task 2: Immutable plan and store

**Files:**
- Create: `app/models/execution.py`
- Create: `app/execution/store.py`
- Create: `app/execution/__init__.py`
- Test: `tests/unit/test_execution_store.py`

- [ ] Write failing lifecycle tests for pending, rejection, approval, expiry, and idempotent terminal reads.
- [ ] Run focused tests and verify expected failures.
- [ ] Implement frozen Pydantic plan/result models and an in-memory store with guarded transitions.
- [ ] Run focused tests until green.

### Task 3: Deterministic proposal validation

**Files:**
- Create: `app/services/trade_proposal_service.py`
- Test: `tests/unit/test_trade_proposal_service.py`

- [ ] Write failing tests for hard symbol/value limits, policy limits, slippage, and balances.
- [ ] Confirm tests fail because the service is absent.
- [ ] Implement validation and plan construction with a five-minute expiry.
- [ ] Run focused tests until green.

### Task 4: Controlled proposal tool

**Files:**
- Modify: `app/agent/run_context.py`
- Modify: `app/agent/controlled_tools.py`
- Modify: `app/agent/prompts.py`
- Modify: `app/agent/tool_loop.py`
- Test: `tests/unit/test_controlled_tools.py`
- Test: `tests/unit/test_tool_loop.py`

- [ ] Add failing tests proving the tool requires fresh portfolio/market observations and only stages a proposal.
- [ ] Run focused tests and verify failures.
- [ ] Add `propose_trade`; do not add any execution tool.
- [ ] Include created proposals in the tool-loop result.
- [ ] Update instructions so the Agent asks for approval but cannot claim execution.
- [ ] Run focused tests until green.

### Task 5: Typed Binance Demo order adapter

**Files:**
- Modify: `app/gateways.py`
- Modify: `app/binance/schemas.py`
- Modify: `app/binance/gateway.py`
- Test: `tests/unit/test_binance_execution_gateway.py`

- [ ] Write failing tests for MARKET BUY/SELL CLI arguments, payload validation, and order lookup.
- [ ] Run focused tests and confirm failures.
- [ ] Add a narrow execution protocol and fixed Binance CLI commands using argument arrays.
- [ ] Validate all returned JSON with Pydantic and keep errors credential-safe.
- [ ] Run focused tests until green.

### Task 6: Approval and execution service

**Files:**
- Create: `app/services/execution_service.py`
- Test: `tests/unit/test_execution_service.py`

- [ ] Add failing tests for explicit approval, revalidation, rejection, successful verification, ambiguous failure, expiry, and duplicate approval.
- [ ] Confirm tests fail for missing behavior.
- [ ] Implement approval outside the LLM loop, fresh data checks, atomic state transitions, one order submission, order query, and portfolio refresh.
- [ ] Run focused tests until green.

### Task 7: Application/API integration

**Files:**
- Modify: `app/models/api.py`
- Modify: `app/application.py`
- Modify: `app/bootstrap.py`
- Modify: `app/api.py`
- Test: `tests/unit/test_application.py`
- Test: `tests/unit/test_api.py`

- [ ] Write failing tests for returning a pending plan and for approve/reject endpoints.
- [ ] Verify focused failures.
- [ ] Add the structured plan to completed chat events and dedicated plan endpoints.
- [ ] Wire one shared plan store and execution service in bootstrap.
- [ ] Run focused tests until green.

### Task 8: Compact approval UI

**Files:**
- Modify: `web/app.js`
- Modify: `web/styles.css`
- Test: `tests/test_ui.js`

- [ ] Write failing UI tests for proposal rendering and approve/reject request construction.
- [ ] Confirm Node tests fail.
- [ ] Render a compact Binance-yellow proposal card and dedicated approval buttons.
- [ ] Disable buttons during the request and render the verified result without implying success early.
- [ ] Run UI tests until green.

### Task 9: Configuration, documentation, and full verification

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/development-guidelines.md`
- Modify: `docs/sentinel-project-guide.html`
- Test: existing documentation/configuration tests

- [ ] Document Demo-only credentials, API-key TRADE permission, hard safety limits, approval flow, and how to disable execution.
- [ ] Run all Python and UI tests.
- [ ] Run `python -m compileall app main.py`, `node --check web/app.js`, and `git diff --check`.
- [ ] Review the final diff for secret leakage and accidental production endpoints.
