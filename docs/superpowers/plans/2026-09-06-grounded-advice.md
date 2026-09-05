# Grounded Advice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add evidence-linked advice instructions and expand short conversation memory to 16 messages.

**Architecture:** Authoritative evidence remains typed Python output. The LLM receives a stricter qualitative response contract and asks for missing suitability information before concrete recommendations.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, pytest

---

### Task 1: Expand memory

**Files:** `app/agent/conversation_memory.py`, `tests/unit/test_conversation_memory.py`

- [ ] Change the test to require the latest 16 conversational messages and verify it fails.
- [ ] Set the limit to 16 and verify the focused test passes.

### Task 2: Ground advice

**Files:** `app/agent/prompts.py`, `tests/unit/test_tool_loop.py`

- [ ] Add a failing instruction-contract test.
- [ ] Require Assessment, Rationale, Recommendation, and Limitations after analysis.
- [ ] Require current-analysis grounding and clarification before concrete allocations when objective, time horizon, or risk tolerance is missing.
- [ ] Verify focused tests pass.

### Task 3: Verify

- [ ] Run all Python tests, UI tests, compileall, and `git diff --check`.
- [ ] Commit the implementation.
