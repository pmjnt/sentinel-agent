# Sentinel SRD Guide HTML Design

## Purpose

Create a self-contained Vietnamese HTML guide that helps a Java/Spring Boot backend developer understand:

- how the current Sentinel implementation compares with the new SRD;
- why the current project is a useful foundation but does not yet satisfy the new Phase 1 acceptance criteria;
- how chat-editable portfolio policy, deterministic Python engines, FastAPI, and the official Binance MCP Server fit together;
- what should be implemented next and in which order.

This task produces documentation only. The production integration will be specified and implemented as a separate follow-up project after the architecture in this guide is reviewed.

## Output

Create:

```text
docs/sentinel-srd-guide.html
```

The document must work when opened directly from the filesystem. It uses embedded CSS, no JavaScript, no external fonts, and no runtime server.

## Audience and teaching style

The primary reader is a Java/Spring Boot developer learning Python and AI Agents.

Each major component answers:

1. What is it?
2. Why is it needed?
3. How does it work in Sentinel?

Use Spring Boot comparisons only when they clarify the concept, such as comparing Pydantic models with validated DTOs or FastAPI routes with controllers. Avoid forcing controller/service/repository layers into the Python design.

Use one policy throughout the document:

```text
Keep at least 30% in USDT reserve.
No crypto asset may exceed 40%.
Block rebalancing during high volatility.
Trades above $1,000 require approval.
```

## Document structure

### 1. Executive conclusion

State prominently that the current repository satisfies the earlier tool-calling prototype but does not yet satisfy the new SRD Phase 1. Summarize the missing Policy Engine, Rebalance Planner, and RiskEngine.

### 2. Current-state map

Explain the existing Agent, LiteLLM provider selection, local mock tools, console runner, and static UI. Clearly label which paths are real and which UI behavior is simulated.

### 3. Acceptance-criteria audit

Present AC-001 through AC-010 in a scannable table using three statuses: met, partial, and missing. Include specific code evidence and the portfolio-data mismatch.

### 4. Responsibility boundaries

Explain this rule:

```text
LLM understands language and chooses tools.
Python calculates and validates.
RiskEngine authorizes or blocks proposals.
The human explicitly approves when required.
Binance provides data and, in a later write-enabled scope, executes.
```

Include examples of incorrect and correct responsibility allocation.

### 5. Chat-editable policy

Show how multi-turn chat commands create, update, remove, and inspect a `PortfolioPolicy`. Explain session state, schema validation, clarification for ambiguous fields, and why the LLM cannot bypass deterministic enforcement.

### 6. End-to-end real request flow

Walk through what happens after the user selects a model and submits a policy in the connected UI:

1. Frontend sends the message to FastAPI.
2. FastAPI resumes the user session.
3. The LLM parses a structured policy update.
4. Pydantic validates it.
5. Binance MCP supplies account and market information.
6. Python calculates weights and violations.
7. Rebalance Planner produces deterministic actions.
8. RiskEngine returns `BLOCKED`, `REQUIRES_APPROVAL`, or `SAFE_TO_PROPOSE`.
9. The LLM explains structured results.
10. FastAPI streams observable events to the UI without exposing hidden chain-of-thought.

### 7. Binance MCP integration

Document the official endpoint:

```text
https://agent.binance.com/mcp/agentic
```

Explain Streamable HTTP, browser authorization, Account scope, Agentic sub-account isolation, and regional/account eligibility. The Sentinel integration is read-only:

- allow market-data tools;
- allow balance/account-reading tools;
- reject trade, transfer, cancel, and other write-capable tools through an application-level tool filter;
- do not guess tool names before discovery from the authenticated server;
- fail closed if required market or account data cannot be retrieved.

Make clear that prompt instructions are not a security boundary. The MCP tool allow-list is the actual application boundary.

### 8. Target architecture

Provide an accessible text diagram covering Frontend, FastAPI, Agent/LLM, session policy, MCP adapter, deterministic engines, and the response event stream.

### 9. Current code: retain, replace, add

Show three concrete lists:

- retain: provider configuration, Agent instructions as a base, Pydantic approach, tool-testing pattern;
- replace: hard-coded portfolio/market data and JavaScript timer simulation;
- add: policy models, policy parser, allocation service, violation engine, planner, RiskEngine, Binance MCP client lifecycle, FastAPI endpoint, session state, real event renderer.

### 10. Implementation roadmap

Split future production work into independently testable milestones:

1. deterministic domain core;
2. structured policy parsing and chat state;
3. Binance MCP read-only adapter and tool discovery;
4. FastAPI orchestration and event streaming;
5. connect the existing UI and remove simulation.

No milestone enables order placement.

### 11. Security and failure behavior

Explain least privilege, explicit scopes, secrets, no API credentials in the frontend, fail-closed behavior, no fabricated fallback, and audit-event requirements.

### 12. Reader checklist and glossary

End with an SRD implementation checklist and concise definitions for Agent, LLM, tool, MCP, policy, deterministic code, schema validation, session, SSE, and RiskEngine.

## Visual design

- Use a clean technical-document layout rather than the application dashboard.
- Provide a sticky table of contents on desktop and a normal top index on mobile.
- Use high-contrast paper, ink, muted blue, green, amber, and red status colors.
- Use semantic HTML: `main`, `nav`, `section`, tables, lists, code blocks, and callouts.
- Keep body text at least 16px with a comfortable line height and maximum reading width.
- Ensure horizontal overflow is contained for diagrams, tables, and code samples.
- Use print CSS so the guide can be saved as PDF cleanly.

## Sources

Link directly to:

- Binance MCP Server documentation: `https://developers.binance.com/en/docs/agent-native/mcp-server/agentic`
- OpenAI Agents SDK MCP documentation: `https://openai.github.io/openai-agents-python/mcp/`

Do not claim exact Binance tool names because the official documentation instructs clients to discover the server's capabilities after connecting and authorization.

## Verification

- Confirm the HTML parses without obvious structural errors.
- Confirm all internal table-of-contents links target existing section IDs.
- Confirm no external asset is required.
- Confirm the document distinguishes current behavior from target behavior.
- Confirm the document never implies trading capability is enabled.
- Confirm the repository remains unchanged outside the new guide and its tests/documentation plan.
