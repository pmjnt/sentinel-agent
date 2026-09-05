# Request Interpreter Rename — Design

**Date:** 2026-09-05

## Problem

The component named `PolicyParser` does more than parse policy fields. It
interprets an entire chat request and can return ordered actions for updating a
policy, viewing a policy, analyzing a portfolio, or requesting clarification.
The current name therefore hides its routing responsibility.

## Decision

Rename the component to `Request Interpreter` without changing its behavior or
adding another LLM call.

The new vocabulary is:

- `app/agent/request_interpreter.py` instead of `policy_parser.py`;
- `AgentRequestInterpreter` instead of `AgentPolicyParser`;
- `create_request_interpreter_agent()` instead of
  `create_policy_parser_agent()`;
- `build_interpreter_input()` instead of `build_parser_input()`;
- `REQUEST_INTERPRETER_INSTRUCTIONS` instead of
  `POLICY_PARSER_INSTRUCTIONS`;
- `RequestInterpreter` protocol with `interpret()` instead of `RequestParser`
  with `parse()`;
- `StaticInterpreter` in tests instead of `StaticParser`.

`ParsedRequest` and its typed actions remain unchanged. The model still
represents a validated structured interpretation of one request.

## Runtime behavior

The interpreter remains a tool-free LLM Agent. It receives the current validated
policy and the user's message, then returns ordered `ParsedRequest.actions`.
`PolicyConversationService` executes those actions; it does not allow the LLM to
mutate session state directly.

There is no compatibility alias for the old names. All active imports and current
documentation must use the accurate vocabulary so obsolete names cannot keep
spreading.

## Scope

This is a naming and responsibility-clarification refactor only. It does not wire
the interpreter into `main.py`, add an orchestrator, change prompts' safety rules,
change the Pydantic schema, or add an LLM call.

## Verification

- Update tests first so imports of `request_interpreter` fail before production
  code is renamed.
- Preserve retry, structured-output, blank-input, action-order, session, and
  natural-language response tests.
- Update the current HTML handbook and its contract test.
- Confirm no active code or current guide references `PolicyParser`,
  `policy_parser`, `POLICY_PARSER_INSTRUCTIONS`, or `RequestParser`.
- Run the full Python suite, UI tests, compilation, and whitespace validation.
