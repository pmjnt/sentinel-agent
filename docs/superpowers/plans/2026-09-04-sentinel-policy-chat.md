# Sentinel Policy Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Sentinel interpret natural-language policy requests as validated actions, keep policy per in-memory session, and return deterministic natural-language confirmations without calling external data sources.

**Architecture:** A structured-output Agent converts text into typed actions. A small parser boundary makes that external LLM dependency replaceable in tests. `PolicyConversationService` executes validated actions against an in-memory store; analysis actions are reported to the later portfolio workflow but do not perform analysis in this checkpoint.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, LiteLLM, Pydantic 2, pytest

---

### Task 1: Typed chat actions

**Files:**
- Create: `app/models/chat.py`
- Create: `tests/unit/test_chat_models.py`

- [x] **Step 1: Write failing schema tests**

Test that a combined update-and-analyze request validates in order, an empty action list is rejected, and action-specific data cannot appear on the wrong action type.

Use the exact model surface:

```text
ActionType: UPDATE_POLICY, VIEW_POLICY, ANALYZE_PORTFOLIO, NEEDS_CLARIFICATION
UpdatePolicyAction: type literal UPDATE_POLICY, patch PolicyPatch
ViewPolicyAction: type literal VIEW_POLICY
AnalyzePortfolioAction: type literal ANALYZE_PORTFOLIO, focus_symbols list[str]
ClarificationAction: type literal NEEDS_CLARIFICATION, question non-empty string
RequestedAction: discriminated union on type
ParsedRequest: actions list with min_length=1
```

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_chat_models.py -q
```

Expected: import fails because `app.models.chat` does not exist.

- [x] **Step 3: Implement the models**

Use `Literal` values and `Annotated[union, Field(discriminator="type")]`. Freeze every model. Normalize `focus_symbols` to uppercase and reject an empty clarification question.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_chat_models.py -q
```

- [x] **Step 5: Commit**

```bash
git add app/models/chat.py tests/unit/test_chat_models.py
git commit -m "feat: model validated policy chat actions"
```

### Task 2: In-memory policy sessions

**Files:**
- Create: `app/sessions.py`
- Create: `tests/unit/test_sessions.py`

- [x] **Step 1: Write failing store tests**

Test:

- unknown session returns an empty `PortfolioPolicy`;
- applying a patch changes only that session;
- two session IDs remain isolated;
- blank session IDs are rejected;
- clearing a session removes its policy.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_sessions.py -q
```

Expected: import fails because `app.sessions` does not exist.

- [x] **Step 3: Implement `InMemoryPolicySessionStore`**

Public methods:

```text
get(session_id: str) -> PortfolioPolicy
apply(session_id: str, patch: PolicyPatch) -> PortfolioPolicy
clear(session_id: str) -> None
```

Normalize a session ID by trimming it and rejecting an empty value. Use `apply_policy_patch` rather than duplicating merge logic. Do not add a protocol or persistence layer in this checkpoint.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_sessions.py -q
```

- [x] **Step 5: Commit**

```bash
git add app/sessions.py tests/unit/test_sessions.py
git commit -m "feat: keep portfolio policy by session"
```

### Task 3: Natural-language policy confirmations

**Files:**
- Create: `app/services/policy_response_service.py`
- Create: `tests/unit/test_policy_response_service.py`

- [x] **Step 1: Write failing response tests**

Test Vietnamese responses for:

- setting maximum asset weight to 40%;
- removing minimum stablecoin weight with explicit null;
- enabling and disabling high-volatility blocking;
- setting the approval threshold;
- viewing an empty policy and a configured policy.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_response_service.py -q
```

- [x] **Step 3: Implement deterministic formatters**

Create:

- `format_policy_update(patch: PolicyPatch, updated: PortfolioPolicy) -> str`
- `format_current_policy(policy: PortfolioPolicy) -> str`

Format weights as percentages without float conversion and USD with comma separators. Mention only explicitly patched fields in an update response. Do not call an LLM.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_response_service.py -q
```

- [x] **Step 5: Commit**

```bash
git add app/services/policy_response_service.py tests/unit/test_policy_response_service.py
git commit -m "feat: explain policy changes in natural language"
```

### Task 4: Structured-output LLM parser

**Files:**
- Create: `app/agent/__init__.py`
- Create: `app/agent/prompts.py`
- Create: `app/agent/policy_parser.py`
- Modify: `app/agent.py`
- Create: `tests/unit/test_policy_parser.py`
- Modify: `tests/test_agent.py`

- [x] **Step 1: Write failing construction and input tests**

Assert:

- the parser Agent uses `settings.agents_model`;
- its `output_type` represents `ParsedRequest`;
- parser instructions prohibit execution and invented thresholds;
- `build_parser_input(message, policy)` includes the user message and current validated policy JSON;
- blank messages are rejected before an LLM call.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_parser.py -q
```

- [x] **Step 3: Implement parser construction**

`create_policy_parser_agent(settings: Settings) -> Agent` creates a tool-free Agent with `output_type=ParsedRequest`. Instructions define all four actions, multi-action ordering, patch semantics, and clarification behavior. The parser never receives financial tools.

`build_parser_input(message: str, current_policy: PortfolioPolicy) -> str` rejects blank input and includes current policy using `model_dump_json()`.

`AgentPolicyParser.parse(message, current_policy) -> ParsedRequest` calls `Runner.run` and returns `result.final_output`. Retry exactly once only for `ModelBehaviorError`; propagate provider/network failures without converting them into a guessed action.

- [x] **Step 4: Preserve the existing Sentinel import**

Move the existing risk-analysis Agent implementation to `app/agent/sentinel.py`. Keep `app/agent/__init__.py` empty. Update `main.py` and tests to import from `app.agent.sentinel`. Delete the conflicting `app/agent.py` module.

- [x] **Step 5: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_parser.py tests/test_agent.py -q
```

- [x] **Step 6: Commit**

```bash
git add app/agent app/agent.py main.py tests/unit/test_policy_parser.py tests/test_agent.py
git commit -m "feat: parse policy chat into structured actions"
```

### Task 5: Policy conversation orchestration

**Files:**
- Create: `app/services/policy_conversation_service.py`
- Create: `tests/unit/test_policy_conversation_service.py`

- [ ] **Step 1: Write failing orchestration tests**

Use a fake parser returning `ParsedRequest`. Test:

- update returns a natural-language message and new policy;
- view returns policy without changing it;
- clarification returns its question without changing policy;
- update followed by analyze applies the update first and returns `analysis_requested=True`;
- analyze alone returns the existing policy and `analysis_requested=True`;
- no test calls `Runner`, OpenAI, Gemini, or Binance.

- [ ] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_conversation_service.py -q
```

- [ ] **Step 3: Implement the conversation service**

Define a local `RequestParser` protocol with one async `parse(message, current_policy)` method because production and test have real alternative implementations.

Define frozen `PolicyConversationResult` with:

```text
message: str
policy: PortfolioPolicy
analysis_requested: bool
focus_symbols: list[str]
```

Execute actions in order. Stop immediately on clarification. Join multiple deterministic response messages with newlines. Never call portfolio or market tools in this service.

- [ ] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_conversation_service.py -q
```

- [ ] **Step 5: Commit**

```bash
git add app/services/policy_conversation_service.py tests/unit/test_policy_conversation_service.py
git commit -m "feat: orchestrate policy chat actions"
```

### Task 6: Agent guideline and verification

**Files:**
- Create: `docs/agent-guidelines.md`
- Modify: `README.md`

- [ ] **Step 1: Document the policy parser boundary**

Explain action types, structured output, current-policy context, patch validation, one retry, deterministic confirmation, session lifetime, and why policy parsing is separate from risk analysis.

- [ ] **Step 2: Run complete verification**

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

- [ ] **Step 3: Verify dependency boundaries**

```bash
rg -n 'from (agents|fastapi|mcp)|import (agents|fastapi|mcp)' app/models app/services
```

Expected: the only allowed match is the `RequestParser` protocol's own module name containing “parser”; there must be no framework import.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/agent-guidelines.md docs/superpowers/plans/2026-09-04-sentinel-policy-chat.md
git commit -m "docs: explain Sentinel policy chat rules"
```

## Completion boundary

This plan ends with a tested policy-chat application service and real structured-output parser implementation. It does not call Binance or expose HTTP routes; those belong to the next checkpoints.
