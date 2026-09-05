# General Chat Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Request Interpreter return a safe natural-language response for greetings and non-portfolio conversation.

**Architecture:** Add `GeneralChatAction(response)` to the existing discriminated union. `PolicyConversationService` converts it to a text event only, so the application skips analysis, Reporter, gateway, and Binance through its existing event behavior.

**Tech Stack:** Python 3.12, Pydantic, OpenAI Agents SDK through LiteLLM, pytest.

---

### Task 1: Typed general-chat contract

**Files:**
- Modify: `tests/unit/test_chat_models.py`
- Modify: `app/models/chat.py`

- [x] **Step 1: Write failing model tests**

Test that `ParsedRequest.model_validate()` maps `{"type": "GENERAL_CHAT", "response": "Xin chào!"}` to `GeneralChatAction`, strips surrounding response whitespace, and rejects a blank response.

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/unit/test_chat_models.py -q`

Expected: import or validation fails because `GeneralChatAction` and its discriminator mapping do not exist.

- [x] **Step 3: Implement the Pydantic model**

Add `GENERAL_CHAT` to `ActionType`, define a frozen/forbid-extra `GeneralChatAction` with a non-blank response validator, and add it to `RequestedAction`.

- [x] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/unit/test_chat_models.py -q`

Expected: all chat-model tests pass.

### Task 2: Interpreter and conversation behavior

**Files:**
- Modify: `tests/unit/test_policy_conversation_service.py`
- Modify: `tests/unit/test_request_interpreter.py`
- Modify: `app/services/policy_conversation_service.py`
- Modify: `app/agent/prompts.py`
- Modify: `README.md`
- Modify: `docs/agent-guidelines.md`

- [x] **Step 1: Write failing service tests**

Pass `ParsedRequest(actions=[GeneralChatAction(response="Xin chào!")])` through the real conversation service. Assert the message is returned, policy remains unchanged, and `analysis_requested` is false. Extend the Interpreter construction test to require `GENERAL_CHAT` safety instructions.

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/unit/test_policy_conversation_service.py tests/unit/test_request_interpreter.py -q`

Expected: service produces no message because it does not handle the new action.

- [x] **Step 3: Implement service and prompt behavior**

Convert `GeneralChatAction.response` to `PolicyMessageEvent`. Add prompt rules that use it only for non-portfolio conversation, match the user's language, and forbid invented financial data, advice without observations, trade creation, and execution claims.

- [x] **Step 4: Update active documentation**

Document the fifth action and clarify that general chat performs no portfolio, policy, gateway, or Binance work.

- [x] **Step 5: Verify offline suite**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: all tests and validation pass without external calls.

- [x] **Step 6: Run isolated real smoke test**

Call `AgentRequestInterpreter.interpret("xin chào", PortfolioPolicy())` once with `LITELLM_DEBUG=false`. Expected result is one validated `GeneralChatAction`. If OpenAI still returns the same output-limit error, report that evidence and leave token configuration for a separate change.

Result: OpenAI returned HTTP 400, `max_tokens or model output limit was reached`.
No token setting was changed as part of this feature.
