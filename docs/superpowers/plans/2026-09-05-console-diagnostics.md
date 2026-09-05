# Console Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent duplicated console prompts and show redacted technical errors in opt-in debug mode.

**Architecture:** Small pure helpers in `main.py` own prompt rendering and error redaction. The console loop uses them without changing application behavior.

**Tech Stack:** Python 3.12, pytest.

---

### Task 1: Console prompt and safe diagnostics

**Files:**
- Modify: `tests/test_agent.py`
- Modify: `main.py`

- [x] **Step 1: Write failing tests**

Test that `read_console_input()` prints one prompt and invokes its reader with no
prompt argument. Test that `format_debug_error()` includes exception type/message
but replaces every configured credential with `[REDACTED]`.

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_agent.py -q`

Expected: imports fail because the helpers do not exist.

- [x] **Step 3: Implement minimal helpers and console integration**

Add `read_console_input(reader)` using `print(..., end="", flush=True)` followed
by `reader()`. Add `format_debug_error(error, settings)` that replaces non-empty
OpenAI, Gemini, Binance API and Binance secret values. Print it only when
`settings.litellm_debug` is true inside the existing exception handler.

- [x] **Step 4: Verify**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: all commands pass.
