# Request Interpreter Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the misleading Policy Parser vocabulary to Request Interpreter everywhere without changing behavior.

**Architecture:** Preserve the existing tool-free structured-output Agent and `ParsedRequest` schema. Rename the module, public functions/classes, conversation protocol/method, tests, and current handbook together so there is one consistent vocabulary and no compatibility aliases.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, Pydantic, pytest, HTML documentation.

---

### Task 1: Move tests to the Request Interpreter contract

**Files:**
- Create: `tests/unit/test_request_interpreter.py`
- Delete: `tests/unit/test_policy_parser.py`
- Modify: `tests/unit/test_policy_conversation_service.py`
- Modify: `tests/test_project_guide.py`

- [x] **Step 1: Rename test imports and vocabulary**

Use these exact new APIs:

```python
from app.agent.request_interpreter import (
    AgentRequestInterpreter,
    build_interpreter_input,
    create_request_interpreter_agent,
)
from app.agent.prompts import REQUEST_INTERPRETER_INSTRUCTIONS
```

Rename fake `StaticParser.parse()` to `StaticInterpreter.interpret()` and pass it
as `interpreter=`. Update the guide contract to require
`app/agent/request_interpreter.py` and reject active old vocabulary.

- [x] **Step 2: Run tests to verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_request_interpreter.py tests/unit/test_policy_conversation_service.py tests/test_project_guide.py -q
```

Expected: collection fails because `app.agent.request_interpreter` does not exist.

### Task 2: Rename production APIs and documentation

**Files:**
- Create: `app/agent/request_interpreter.py`
- Delete: `app/agent/policy_parser.py`
- Modify: `app/agent/prompts.py`
- Modify: `app/services/policy_conversation_service.py`
- Modify: `docs/sentinel-project-guide.html`

- [x] **Step 1: Implement the new production vocabulary**

Move existing behavior to the new module and names. Define
`RequestInterpreter.interpret(message, current_policy)` in the conversation
service and call it from `handle()`. Do not add aliases for old names.

- [x] **Step 2: Update the current handbook**

Replace active `Policy Parser` terminology with `Request Interpreter`, explain
that policy patch extraction is one part of request interpretation, and update
all local links.

- [x] **Step 3: Run targeted tests to verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_request_interpreter.py tests/unit/test_policy_conversation_service.py tests/test_project_guide.py -q
```

Expected: all targeted tests pass.

- [x] **Step 4: Verify no active old vocabulary remains**

```bash
rg -n "PolicyParser|policy_parser|POLICY_PARSER_INSTRUCTIONS|RequestParser" app docs/sentinel-project-guide.html
test ! -e app/agent/policy_parser.py
test ! -e tests/unit/test_policy_parser.py
```

Expected: no output.

- [x] **Step 5: Run full verification and commit**

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
git add app tests docs/sentinel-project-guide.html docs/superpowers/plans/2026-09-05-request-interpreter-rename.md
git commit -m "refactor: rename policy parser to request interpreter"
```
