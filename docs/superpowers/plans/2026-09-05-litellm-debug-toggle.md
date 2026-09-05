# LiteLLM Debug Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable LiteLLM debug logging only through an explicit, validated local environment flag.

**Architecture:** `Settings` owns the boolean flag. A small composition-root helper receives an injected debug callable, activates it only when enabled, and prints the privacy warning; Agent and domain code remain unchanged.

**Tech Stack:** Python 3.12, Pydantic Settings model, python-dotenv, LiteLLM, pytest.

---

### Task 1: Validated debug setting

**Files:**
- Modify: `tests/test_config.py`
- Modify: `app/config.py`

- [x] **Step 1: Write failing config tests**

Add tests proving an omitted `LITELLM_DEBUG` yields `False`, `true` yields `True`, and an invalid value raises a Pydantic validation error. Add the variable to the test environment cleanup list.

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`

Expected: tests fail because `Settings.litellm_debug` does not exist.

- [x] **Step 3: Implement the setting**

Add `litellm_debug: bool = False` to `Settings` and pass `os.getenv("LITELLM_DEBUG", "false")` from `load_settings()`.

- [x] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_config.py -q`

Expected: all config tests pass.

### Task 2: Conditional startup activation

**Files:**
- Modify: `tests/test_agent.py`
- Modify: `main.py`
- Modify: `.env.example`
- Modify: `.env` (local only, ignored by Git)
- Modify: `README.md`

- [x] **Step 1: Write failing activation tests**

Test `configure_litellm_debug(settings, enable_debug)` with a fake callable. Disabled settings must not call it or print a warning; enabled settings must call it once and warn that request bodies may be logged and logs must not be shared.

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_agent.py -q`

Expected: import fails because the helper does not exist.

- [x] **Step 3: Implement and document activation**

Add the helper in `main.py`, call it immediately after `load_settings()`, document `LITELLM_DEBUG=false` in `.env.example` and README, and set `LITELLM_DEBUG=true` only in the ignored local `.env` for the requested debugging session.

- [x] **Step 4: Verify all checks**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: all tests and checks pass; `.env` remains ignored and no secret is staged.
