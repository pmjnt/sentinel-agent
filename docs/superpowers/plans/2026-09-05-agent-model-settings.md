# Agent Model Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send an explicit output budget and provider-compatible reasoning setting from every Sentinel Agent.

**Architecture:** `Settings` owns the configurable token limit. A single agent-layer builder converts application configuration into SDK `ModelSettings`, avoiding duplicated provider rules across Agent factories.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, LiteLLM, Pydantic, pytest.

> Runtime note: this plan originally covered three Agent factories. The active
> console runtime now uses `app/agent/tool_loop.py`; the Interpreter, Reporter,
> and two-tool `sentinel.py` factories remain legacy/educational consumers of
> the same model-settings builder.

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
rejects invalid values, omits provider-specific reasoning, and attaches the
result to every Agent factory.

- [x] **Step 2: Verify RED**

Run the changed unit-test files and confirm they fail because the setting and
builder do not exist.

- [x] **Step 3: Implement configuration and builder**

Add `llm_max_tokens` to `Settings`; parse it from the environment. Implement
`build_agent_model_settings(settings)` with `ModelSettings(max_tokens=...)`.
OpenAI and Gemini use no explicit reasoning option. Pass it as
`model_settings` to every Agent constructor.

- [x] **Step 4: Document configuration**

Add `LLM_MAX_TOKENS=4096` to `.env.example` and explain its provider-aware use
in README.

- [x] **Step 5: Verify offline and real request**

Run all Python/UI tests, compileall, and diff validation. Then call the Request
controlled tool-loop once with `xin chào`; it must return a natural-language
answer without calling Binance.
