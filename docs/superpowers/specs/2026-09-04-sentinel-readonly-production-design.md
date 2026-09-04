# Sentinel Read-only Production Flow Design

## 1. Goal

Evolve the existing Sentinel learning MVP into a real, read-only portfolio-policy application:

- users create, update, remove, and view portfolio policy through natural-language chat;
- Sentinel reads live portfolio and market data from the official Binance Agentic MCP Server;
- deterministic Python code calculates allocations, detects violations, builds a proposal, and evaluates risk;
- an LLM interprets language, selects relevant read operations, and explains validated results;
- FastAPI connects the current web interface to the backend and emits real activity events;
- no order, cancel, transfer, withdrawal, or other write capability is exposed.

Mocks and fakes may exist in tests only. The normal application flow must never silently fall back to fake financial data.

## 2. Scope

### Included

- Domain models from the SRD.
- Chat intent/action parsing with schema-constrained output.
- In-memory policy sessions.
- Deterministic allocation, violation, rebalance, and risk logic.
- Official Binance Agentic MCP connection over Streamable HTTP.
- OAuth authorization-code flow suitable for local development.
- MCP tool discovery and read-only filtering.
- FastAPI chat and health endpoints.
- Real backend activity events rendered by the existing vintage UI.
- OpenAI/Gemini model selection through the existing LiteLLM route.
- Unit and integration tests that do not call an LLM or Binance.
- Developer, agent, MCP, and testing guidelines.

The first release is a single-user local application. Multi-user token isolation, durable sessions, and deployment hardening are deferred until database-backed identity is designed.

### Excluded

- Order placement or cancellation.
- Transfers or withdrawals.
- Approve/Reject execution controls.
- Post-trade verification.
- Database persistence.
- Docker, queues, microservices, LangChain, LangGraph, or CrewAI.
- Silent mock-data fallback.

## 3. Programming Rules

- Prefer clear Python over framework-heavy abstractions.
- Keep domain code independent from FastAPI, the Agents SDK, LiteLLM, and MCP.
- Use Pydantic at input/output boundaries.
- Use `Decimal` for authoritative financial values and weights.
- Use enums for bounded statuses and reason codes.
- Keep functions small and typed.
- Do not perform network calls, settings loading, or object construction as import side effects.
- Keep `__init__.py` files empty unless a small, stable public package API is valuable.
- Introduce a `Protocol` only at a boundary with a real replacement need.
- Raise typed application errors and translate them into API responses at the API boundary.
- Test deterministic behavior before integration behavior.

## 4. Project Structure

```text
sentinel-agent/
├── app/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── sentinel.py
│   │   ├── policy_parser.py
│   │   └── prompts.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── portfolio.py
│   │   ├── policy.py
│   │   ├── market.py
│   │   ├── trade.py
│   │   └── risk.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── portfolio_service.py
│   │   ├── policy_service.py
│   │   ├── rebalance_service.py
│   │   └── risk_service.py
│   ├── ports/
│   │   ├── __init__.py
│   │   └── portfolio_market_gateway.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── binance.py
│   │   └── oauth.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── routes.py
│   │   └── dependencies.py
│   ├── sessions.py
│   └── config.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── web/
├── docs/
│   ├── architecture.md
│   ├── development-guidelines.md
│   ├── agent-guidelines.md
│   ├── binance-mcp.md
│   └── testing.md
├── main.py
└── requirements.txt
```

The structure is a target, not a reason to create empty abstraction layers. A file is added only when its responsibility is implemented.

## 5. Dependency Direction

```text
models
  ↑
services
  ↑
agent orchestration / MCP adapter / FastAPI
```

- `models` imports no application framework.
- `services` imports domain models only.
- `agent` may call services and consume their structured results.
- `mcp` implements the external-data port and maps provider payloads into domain models.
- `api` coordinates application use cases and translates errors; it contains no financial rules.
- `web` talks only to FastAPI and never receives provider credentials.

## 6. Domain Models

### Portfolio

- `PortfolioAsset`: symbol, amount, USD value, weight.
- `Portfolio`: assets and total USD value.
- Weight is calculated by Python, never accepted as authoritative external or LLM input.

### Policy

- `PortfolioPolicy`: complete policy state.
- `PolicyPatch`: fields explicitly requested for change in one chat message.
- `PolicyViolation`: type, asset, current value, allowed value, severity, explanation.

Initial policy fields:

```text
min_stablecoin_weight
max_asset_weight
block_high_volatility
max_trade_usd_without_approval
```

Per-asset overrides are excluded from the first implementation. The phrase “set BTC to 45%” is interpreted as changing the global maximum only after clarification; Sentinel must not invent a new unsupported policy field.

### Market, plan, and risk

- `MarketData`: symbol, price, 24-hour change, volatility, estimated slippage.
- `TradeAction`: symbol, side, amount, estimated USD value, reason.
- `RebalancePlan`: violations, proposed actions, status, explanation.
- `RiskDecision`: status, reason codes, human-readable reasons.

Risk statuses:

```text
BLOCKED
REQUIRES_APPROVAL
SAFE_TO_PROPOSE
```

`SAFE_TO_PROPOSE` never means execution in this read-only version.

## 7. Chat Actions and Policy State

The LLM converts a message into a validated list of actions:

```text
UPDATE_POLICY
VIEW_POLICY
ANALYZE_PORTFOLIO
NEEDS_CLARIFICATION
```

A message may contain ordered actions. Example:

```text
“Set the maximum asset weight to 40%, then analyze my portfolio.”
→ UPDATE_POLICY
→ ANALYZE_PORTFOLIO
```

Python validates action consistency before executing them:

- only `UPDATE_POLICY` may contain a `PolicyPatch`;
- `VIEW_POLICY` never calls Binance;
- `ANALYZE_PORTFOLIO` never changes policy;
- ambiguous numeric rules produce `NEEDS_CLARIFICATION`;
- no action type can request execution.

### Patch semantics

- Field absent from the structured output: keep the existing value.
- Field explicitly set to `null`: remove the rule.
- Invalid ranges are rejected by Pydantic.
- Python performs the merge using the set of fields explicitly supplied by the model.

Policy is stored in memory by `session_id`. Restarting the server clears sessions. A `PolicyStore` protocol is unnecessary until persistent storage is introduced; an `InMemoryPolicyStore` class with a small explicit API is sufficient.

### User-facing response

Chat responses remain natural language. JSON is internal. The UI also renders the current policy as labeled fields. Simple policy-update confirmations are generated deterministically by Python; complex portfolio explanations use the LLM.

## 8. Deterministic Services

### Portfolio service

- Validates total value and asset values.
- Calculates weights using `asset.usd_value / portfolio.total_usd_value`.
- Rejects an empty or non-positive portfolio total.

### Policy service

- Applies validated patches.
- Detects maximum-asset and minimum-stablecoin violations.
- Uses explicit stablecoin symbols configured by the application; the first list contains only `USDT`.

### Rebalance service

- Builds a draft corrective plan from violations.
- For excess asset weight, proposes a deterministic reduction to the configured maximum.
- For a stablecoin shortfall, pairs the required stablecoin increase with sell actions from assets that exceed their allowed maximum.
- Produces no action when there is no valid deterministic funding source.

### Risk service

Rules run in strict priority:

1. Any applicable HIGH-volatility block returns `BLOCKED`.
2. Otherwise, a proposed action above the approval threshold returns `REQUIRES_APPROVAL`.
3. Otherwise, the result is `SAFE_TO_PROPOSE`.

The service returns reason codes and text. The LLM cannot override its status.

## 9. Agent Responsibilities

The LLM is responsible for:

- understanding natural-language intent;
- producing schema-constrained actions and policy patches;
- determining which relevant read-only observations are required;
- asking focused clarification questions;
- explaining portfolio, market, plan, and risk results in context.

The Agent sees two stable application tools: `get_portfolio()` and `get_market_data(symbol)`. These are local Agents SDK function-tool wrappers. The wrappers call `PortfolioMarketGateway`; production routes that call to Binance MCP, while tests inject a fake gateway. The LLM therefore chooses the information it needs without seeing Binance's entire raw tool catalog.

The LLM is not authoritative for:

- allocation arithmetic;
- violation thresholds;
- trade quantity/value calculations;
- volatility blocking;
- approval requirements;
- execution authorization.

The agent receives structured deterministic results and must clearly distinguish source facts from interpretation.

## 10. External Data Port

One boundary supports external portfolio and market reads:

```python
class PortfolioMarketGateway(Protocol):
    async def get_portfolio(self) -> Portfolio: ...
    async def get_market_data(self, symbol: str) -> MarketData: ...
```

The production implementation uses Binance MCP. Tests use a small fake implementation. Domain services remain unaware of MCP payload formats.

## 11. Binance MCP Integration

Official endpoint:

```text
https://agent.binance.com/mcp/agentic
```

The integration uses the MCP Python SDK Streamable HTTP client underneath the OpenAI Agents SDK function-tool wrappers. Binance requires user authorization for Account scope; market data is public. OAuth follows authorization code + PKCE with a loopback callback in local development.

Token and registered-client information are held in backend memory for the first local version. Restarting the backend requires authorization again. Tokens must never be placed in URLs, prompts, frontend state, or logs.

### Tool discovery

The client connects and lists tools after authorization. Exact Binance tool names are not guessed in code or documentation. The adapter identifies candidate read operations from server-provided names, descriptions, and schemas, then requires an explicit reviewed mapping before normal account analysis is enabled.

Raw Binance MCP tools are not attached directly to the Agent. The reviewed mapping is used only inside the gateway implementation behind `get_portfolio()` and `get_market_data()`. This makes the model-facing contract stable and prevents accidental exposure when Binance adds a new server tool.

If required mappings are missing, the API reports that Binance capabilities are unavailable and exposes the discovered metadata for local developer review without calling the unknown tools.

### Read-only boundary

Two controls are required:

1. Binance authorization grants only Market Data and Account scope. Trade and Transfer scopes are not granted.
2. The gateway can invoke only explicitly allow-listed read tool names after discovery and mapping; raw MCP tools are never exposed to the LLM.

Unknown tools and any tool related to orders, trading, cancellation, conversion, transfer, or withdrawal are denied. Prompt instructions are not a security boundary.

There is no mock fallback when MCP connection, authorization, portfolio reading, or market reading fails.

## 12. FastAPI Contract

### `GET /api/health`

Returns backend, LLM configuration, and Binance connection readiness without exposing credentials.

### `POST /api/chat`

Request:

```json
{
  "session_id": "browser-generated-id",
  "message": "Keep at least 30% in USDT, then analyze my portfolio.",
  "provider": "gemini",
  "model": "provider-model-id"
}
```

Response:

```json
{
  "session_id": "...",
  "message": "Natural-language response",
  "policy": {},
  "portfolio": {},
  "violations": [],
  "market_checks": [],
  "plan": null,
  "risk_decision": null,
  "activities": []
}
```

The first implementation returns the completed activity list in one response. Server-Sent Events are added only if real end-to-end latency makes progressive updates necessary; this avoids adding two API paths prematurely.

### OAuth endpoints

- `GET /api/binance/connect`: starts the authorization flow and redirects to Binance.
- `GET /api/binance/callback`: validates state/issuer, completes token exchange, and returns to the UI.
- `POST /api/binance/disconnect`: clears local token/client state and closes the MCP connection.

Exact callback behavior will follow capabilities verified against the installed MCP SDK and Binance authorization metadata during implementation.

## 13. UI Changes

- Replace JavaScript timers and hard-coded evidence with `POST /api/chat`.
- Keep the compact provider/model selector.
- Add connection state and a “Connect Binance” action.
- Keep chat responses in natural language.
- Render current policy in a readable policy panel.
- Render activities returned by the backend; do not show hidden chain-of-thought.
- Render portfolio, violations, market checks, proposal, and risk decision only when returned.
- Explain connection and validation failures without substituting mock results.
- Never store API keys or Binance tokens in browser storage.

## 14. Error Handling

- Invalid message or model choice: HTTP 422 with a clear field error.
- Provider and model values are checked against a backend allow-list; API keys continue to come only from environment variables.
- Invalid LLM structured output: retry once; then return a safe parsing failure.
- Ambiguous policy: return a clarification question without changing session policy.
- Binance not connected: return a connect-required state.
- Missing required read tool mapping: return capability-unavailable state.
- Portfolio read failure: produce no recommendation.
- Market read failure: plan cannot be considered safe.
- Unexpected application failure: return a request ID and generic message; log the typed cause without secrets.

## 15. Testing Strategy

### Unit tests

- Portfolio totals and weight calculation.
- Policy patch semantics and validation.
- Maximum asset and stablecoin violations.
- No violations for compliant portfolio.
- Rebalance calculations.
- Risk priority and all three statuses.
- Action consistency validation.
- Deterministic natural-language policy confirmations.

### Integration tests

- FastAPI routes with dependency overrides.
- Chat workflow using a fake parser and fake portfolio/market gateway.
- Binance adapter payload mapping using saved sanitized fixtures.
- Read-only tool filter accepts reviewed reads and denies unknown/write tools.
- Failure paths never fall back to mock data.

No automated unit or integration test calls OpenAI, Gemini, or Binance. A separate opt-in smoke command verifies the real MCP connection after interactive OAuth.

## 16. Documentation Deliverables

- `README.md`: setup, run, connect, analyze, and test.
- `docs/architecture.md`: modules, dependency direction, and request flow.
- `docs/development-guidelines.md`: style, typing, errors, imports, side effects, and review checklist.
- `docs/agent-guidelines.md`: LLM responsibilities, structured output, tools, clarification, and forbidden behavior.
- `docs/binance-mcp.md`: OAuth, scopes, discovery/mapping, read-only filtering, and troubleshooting.
- `docs/testing.md`: test layers, fake boundaries, smoke tests, and commands.

## 17. Implementation Order

1. Domain models and deterministic services.
2. Structured action/policy parsing and in-memory sessions.
3. Binance MCP OAuth, discovery, read-only filter, and gateway adapter.
4. FastAPI application and chat orchestration.
5. Connect the vintage UI and remove simulation.
6. Finish documentation and run complete verification.

Each checkpoint must pass its tests before the next begins. This is an implementation order, not a sequence of disposable demo phases.

## 18. Acceptance Conditions

- A user can create, change, remove, and view policy using natural-language chat.
- A combined update-and-analyze message executes actions in validated order.
- Live analysis requires a working Binance MCP connection; it never uses mock financial data.
- Portfolio weights and violations are deterministic.
- Relevant market data is retrieved for assets requiring investigation.
- A deterministic rebalance proposal is generated when possible.
- RiskEngine implements blocking priority over approval.
- The final answer explains data, violation, proposal, and risk status.
- Browser activity comes from backend workflow events, not timers.
- The application cannot see or call Binance write tools.
- All deterministic and integration tests run without external API calls.

## 19. Primary References

- Binance Agentic MCP Server: <https://developers.binance.com/en/docs/agent-native/mcp-server/agentic>
- OpenAI Agents SDK MCP: <https://openai.github.io/openai-agents-python/mcp/>
- MCP Python SDK OAuth client example: <https://github.com/modelcontextprotocol/python-sdk/blob/main/examples/snippets/clients/oauth_client.py>
