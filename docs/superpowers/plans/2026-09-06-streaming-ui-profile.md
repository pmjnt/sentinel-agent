# Streaming UI, Structured Response, and Investor Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a real vintage chat UI backed by safe SSE activity, structured results, and chat-managed investor profile state.

**Architecture:** Extend the existing controlled Agent state with validated profile patches. Map SDK semantic tool events to public activity events, buffer model prose until validation, and expose the resulting stream through one FastAPI endpoint whose terminal event contains typed domain JSON.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, Pydantic, FastAPI, SSE, vanilla HTML/CSS/JavaScript, pytest, Node test runner

---

### Task 1: Investor profile domain and store

**Files:** `app/models/profile.py`, `app/sessions.py`, `tests/unit/test_profile.py`, `tests/unit/test_sessions.py`

- [ ] Write failing tests for profile validation, patch application, session isolation, and compare-and-set commit.
- [ ] Implement immutable profile models and deterministic patch application.
- [ ] Implement the in-memory profile session store.
- [ ] Run focused tests.

### Task 2: Controlled profile tools

**Files:** `app/agent/run_context.py`, `app/agent/controlled_tools.py`, `app/agent/prompts.py`, `tests/unit/test_controlled_tools.py`, `tests/unit/test_tool_loop.py`

- [ ] Write failing tests for simple LLM-facing schemas, staging, viewing, and exposed tool names.
- [ ] Add profile state/events to the run context.
- [ ] Add `update_investor_profile` and `view_investor_profile` without execution capabilities.
- [ ] Update instructions and run focused tests.

### Task 3: Application profile commit and structured response

**Files:** `app/application.py`, `app/models/api.py`, `tests/unit/test_tool_loop_application.py`, `tests/unit/test_api_models.py`

- [ ] Write failing tests for successful atomic profile commit and typed final snapshots.
- [ ] Pass profile through the Agent loop and commit only validated staged patches.
- [ ] Add structured response fields without removing terminal compatibility.
- [ ] Run focused tests.

### Task 4: Real Agent activity stream

**Files:** `app/agent/streaming.py`, `app/agent/tool_loop.py`, `tests/unit/test_agent_streaming.py`

- [ ] Write failing tests for allowlisted STARTED/COMPLETED activity mapping and redaction.
- [ ] Add the `Runner.run_streamed` path and collect validated final state.
- [ ] Buffer LLM prose until safety validation, then emit safe display deltas.
- [ ] Run focused tests.

### Task 5: FastAPI SSE endpoint

**Files:** `requirements.txt`, `app/api.py`, `tests/unit/test_api.py`

- [ ] Add FastAPI dependencies and install them in the local environment.
- [ ] Write failing endpoint tests using a fake streaming application.
- [ ] Implement `/api/chat/stream`, `/api/config`, health, and static web serving.
- [ ] Encode named SSE events with Pydantic JSON and safe errors.
- [ ] Run focused tests.

### Task 6: Connect the vintage UI

**Files:** `web/index.html`, `web/app.js`, `web/styles.css`, `tests/test_ui.js`

- [ ] Replace simulation assertions with SSE parsing and structured rendering tests.
- [ ] Replace mock notices/data and timer logic with real fetch streaming.
- [ ] Render real activity, profile, evidence, risk status, and validated interpretation.
- [ ] Preserve responsive behavior, focus states, and reduced motion.
- [ ] Run Node tests and inspect the rendered page locally.

### Task 7: Documentation and verification

**Files:** `README.md`, `docs/architecture.md`, `docs/agent-guidelines.md`

- [ ] Document the API, SSE contract, profile boundary, startup command, and UI mapping.
- [ ] Run all Python tests, Node tests, compileall, and `git diff --check`.
- [ ] Commit the implementation.
