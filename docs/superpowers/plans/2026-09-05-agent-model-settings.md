# Agent Model Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send an explicit output budget and provider-compatible reasoning setting from every Sentinel Agent.

**Architecture:** `Settings` owns the configurable token limit. A single agent-layer builder converts application configuration into SDK `ModelSettings`, avoiding duplicated provider rules across Agent factories.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, LiteLLM, Pydantic, pytest.

---

### Task 1: Provider-aware Agent settings

**Files:**
- Create: `app/agent/model_settings.py`
- Create: `tests/unit/test_model_settings.py`
- Modify: `app/config.py`
- Modify: `app/agent/request_interpreter.py`
- Modify: `app/agent/analysis_reporter.py`
- Modify: `app/agent/sentinel.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_agent.py`
- Modify: `tests/unit/test_request_interpreter.py`
- Modify: `tests/unit/test_analysis_reporter.py`
- Modify: `.env.example`
- Modify: `README.md`

- [x] **Step 1: Write failing tests**

Assert that configuration defaults to 4096 tokens, accepts `LLM_MAX_TOKENS`,
rejects invalid values, sets OpenAI GPT-5 reasoning to `none`, omits reasoning
for Gemini, and attaches the result to all three Agent factories.

- [x] **Step 2: Verify RED**

Run the changed unit-test files and confirm they fail because the setting and
builder do not exist.

- [x] **Step 3: Implement configuration and builder**

Add `llm_max_tokens` to `Settings`; parse it from the environment. Implement
`build_agent_model_settings(settings)` with `ModelSettings(max_tokens=...)` and
OpenAI GPT-5 `Reasoning(effort="none")`. Pass it as `model_settings` to every
Agent constructor.

- [x] **Step 4: Document configuration**

Add `LLM_MAX_TOKENS=4096` to `.env.example` and explain its provider-aware use
in README.

- [ ] **Step 5: Verify offline and real request**

Run all Python/UI tests, compileall, and diff validation. Then call the Request
Interpreter once with `xin chào`; it must return a validated GENERAL_CHAT action.
