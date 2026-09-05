# Safe Conversation Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add short, filtered conversation continuity without reusing historical financial tool data.

**Architecture:** A small session store owns one in-memory Agents SDK session per Sentinel session ID. A session input callback keeps recent conversational messages, removes old tool traffic, and strips historical policy wrappers; each request still receives a fresh run context and current tool data.

**Tech Stack:** Python 3.12, OpenAI Agents SDK 0.22.0, pytest

---

### Task 1: Conversation session boundary

**Files:**
- Create: `app/agent/conversation_memory.py`
- Create: `tests/unit/test_conversation_memory.py`

- [x] Write failing tests for session isolation/reuse and history filtering.
- [x] Run the focused tests and confirm they fail because the module is absent.
- [x] Implement the in-memory session store and filtering callback.
- [x] Run the focused tests and confirm they pass.

### Task 2: Connect memory to the Agent loop

**Files:**
- Modify: `app/agent/tool_loop.py`
- Modify: `app/application.py`
- Modify: `tests/unit/test_tool_loop.py`
- Modify: `tests/unit/test_tool_loop_application.py`
- Modify: `tests/unit/test_policy_analysis_workflow.py`

- [x] Write failing tests that require `session` and filtered `run_config` in `Runner.run`.
- [x] Pass `session_id` through the application boundary into the Agent loop.
- [x] Resolve and pass the per-user session plus run configuration.
- [x] Confirm focused tests pass.

### Task 3: Safety instructions and verification

**Files:**
- Modify: `app/agent/prompts.py`
- Modify: `README.md`

- [x] State that history is only for references/preferences and current financial facts require fresh tools.
- [x] Run all Python tests, UI tests, compileall, and `git diff --check`.
- [x] Commit the implementation.
