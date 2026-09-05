# General Chat Action — Design

**Date:** 2026-09-05

## Goal

Allow Sentinel's Request Interpreter to handle greetings, help questions, and
other non-portfolio conversation without forcing them into a policy action.

## Contract

Add a fifth typed action:

```json
{
  "type": "GENERAL_CHAT",
  "response": "Xin chào! Tôi là Sentinel..."
}
```

`response` must be a non-empty string. The Request Interpreter must match the
user's language and keep the response concise.

## Runtime behavior

`PolicyConversationService` converts `GeneralChatAction.response` into a
`PolicyMessageEvent`. It does not mutate the policy, request portfolio analysis,
call a gateway, or call Binance.

For a request that is only casual conversation, `GENERAL_CHAT` should be the
only action. Messages that request policy or portfolio work must use the
existing typed actions instead.

## Safety

A general-chat response must not invent portfolio or market data, provide a
personalized portfolio conclusion without observations, create a trade action,
or claim that an order was executed. It may briefly explain what Sentinel can
do and ask the user for a policy or analysis request.

## Diagnosis sequence

After offline tests pass, run the real `xin chào` Request Interpreter smoke test
using the configured OpenAI route. This change is tested before changing
`max_tokens`, so the source of the original output-limit failure remains clear.

If the real call still reaches the model output limit, token configuration is a
separate follow-up fix supported by that evidence.

## Tests

- Pydantic accepts and discriminates `GENERAL_CHAT`.
- Blank responses are rejected.
- Conversation service returns the natural-language response with unchanged
  policy and no analysis event.
- Application returns the response without analysis or Reporter calls.
- No unit test calls a real LLM or Binance.
