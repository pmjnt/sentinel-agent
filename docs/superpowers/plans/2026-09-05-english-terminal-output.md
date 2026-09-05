# English Terminal Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fixed Vietnamese runtime output with English without changing Sentinel's bilingual input handling or deterministic domain data.

**Architecture:** Keep the console as a presentation adapter over typed domain models. Translate only Python-owned display strings; the future UI will serialize the same structured models to JSON rather than parse console text.

**Tech Stack:** Python 3.12, Pydantic, pytest

---

### Task 1: Translate deterministic analysis output

**Files:**
- Modify: `tests/unit/test_tool_loop_application.py`
- Modify: `app/services/analysis_response_service.py`
- Modify: `app/application.py`

- [x] **Step 1: Update tests to require English labels and safe data-error text**

Assert `Verified facts`, `Total portfolio`, `Estimated slippage`, `No policy violations`, `No proposed actions`, and `Required Binance Demo data could not be verified`.

- [x] **Step 2: Run focused tests and verify they fail on the current Vietnamese text**

Run: `.venv/bin/python -m pytest tests/unit/test_tool_loop_application.py -q`

Expected: FAIL on English text assertions.

- [x] **Step 3: Translate the fixed formatter and application error message**

Keep every interpolated value sourced from `PortfolioAnalysis`; change labels only.

- [x] **Step 4: Run focused tests and verify they pass**

Run: `.venv/bin/python -m pytest tests/unit/test_tool_loop_application.py -q`

Expected: PASS.

### Task 2: Translate policy and console output

**Files:**
- Modify: `tests/unit/test_policy_response_service.py`
- Modify: `tests/unit/test_tool_loop_application.py`
- Modify: `tests/test_agent.py`
- Modify: `app/services/policy_response_service.py`
- Modify: `main.py`

- [x] **Step 1: Update tests to require English policy summaries and debug warning**

Assert `Policy updated`, `Current policy`, `minimum stablecoin allocation`, `maximum allocation`, `blocked`, `requires approval`, and `do not share these logs publicly`.

- [x] **Step 2: Run focused tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/unit/test_policy_response_service.py tests/unit/test_tool_loop_application.py tests/test_agent.py -q`

Expected: FAIL on English text assertions.

- [x] **Step 3: Translate the fixed runtime strings**

Do not alter Vietnamese request examples, intent regexes, or output-safety patterns.

- [x] **Step 4: Run focused tests and verify they pass**

Run: `.venv/bin/python -m pytest tests/unit/test_policy_response_service.py tests/unit/test_tool_loop_application.py tests/test_agent.py -q`

Expected: PASS.

### Task 3: Verify and commit

**Files:**
- Verify all modified runtime and test files

- [x] **Step 1: Confirm no fixed Vietnamese runtime output remains**

Run: `rg -n "[À-ỹ]" app main.py -g '*.py'`

Expected: only bilingual input/safety regexes and comments, with no fixed user-facing output.

- [x] **Step 2: Run complete verification**

Run: `.venv/bin/python -m pytest -q`

Run: `node --test tests/test_ui.js`

Run: `.venv/bin/python -m compileall -q app main.py`

Run: `git diff --check`

Expected: all commands pass.

- [x] **Step 3: Commit the implementation**

```bash
git add app main.py tests docs/superpowers/plans/2026-09-05-english-terminal-output.md
git commit -m "fix: use English terminal output"
```
