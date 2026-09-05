# Streaming UI, Structured Response, and Investor Profile Design

## Goal

Turn the static vintage prototype into a real Sentinel chat client with safe streaming activity, structured final data, and a chat-managed investor profile.

## Scope

- Add `InvestorProfile` as validated session state.
- Add controlled `update_investor_profile` and `view_investor_profile` tools.
- Add real activity events sourced from Agents SDK tool-call/tool-output events.
- Add a structured response snapshot for UI rendering.
- Add a FastAPI SSE chat endpoint and serve the existing web assets.
- Replace simulated frontend timers and mock evidence with the real stream.
- Keep all Binance operations read-only; add no execution, transfer, or withdrawal tools.

## Investor profile

The profile stores explicit user preferences only:

- objective: `CAPITAL_PRESERVATION`, `BALANCED`, or `GROWTH`;
- time horizon in months;
- risk tolerance: `LOW`, `MEDIUM`, or `HIGH`;
- acceptable loss percent;
- liquidity need: `LOW`, `MEDIUM`, or `HIGH`;
- excluded assets.

The LLM may stage profile changes through a simple string-valued tool schema. Python parses and validates values. Changes commit only after a successful Agent run, using the same compare-and-set pattern as policy state.

## Streaming contract

`POST /api/chat/stream` accepts:

```json
{"session_id":"user-123","message":"Analyze my portfolio"}
```

It returns `text/event-stream` with these public events:

- `activity`: high-level real progress (`STARTED`, `COMPLETED`, or `FAILED`);
- `text_delta`: validated AI interpretation split into display chunks;
- `completed`: the authoritative structured response snapshot;
- `error`: a redacted, safe failure message.

Tool arguments, raw tool outputs, prompts, credentials, reasoning items, and hidden chain-of-thought are never streamed.

Raw LLM deltas are buffered until the existing output-safety validation succeeds. The UI receives live tool activity immediately, then validated prose chunks, then the final snapshot.

## Structured final snapshot

The `completed` event contains:

```json
{
  "session_id": "user-123",
  "message": "rendered console-compatible response",
  "policy": {},
  "profile": {},
  "analysis": null,
  "activity": [],
  "ai_interpretation": "",
  "execution_status": "NOT_EXECUTED"
}
```

The UI maps domain fields directly and never parses terminal prose to recover values.

## Activity mapping

Agents SDK semantic stream events are mapped through a fixed allowlist:

- `get_portfolio` → `PORTFOLIO_READ`;
- `get_market_data` → `MARKET_DATA_READ`;
- `update_policy` / `view_policy` → policy activity;
- `update_investor_profile` / `view_investor_profile` → profile activity;
- `evaluate_portfolio_risk` → `RISK_EVALUATION`.

Unknown tool names are not exposed. A call produces `STARTED`; its matching output produces `COMPLETED`. Failures produce only a safe `FAILED` event.

## Frontend

The existing paper-ledger visual identity remains. The fake timer simulation and hardcoded evidence are removed. The form posts to the SSE endpoint with `fetch`, decodes events incrementally, renders activity in order, and renders the final structured portfolio, market, risk, profile, and interpretation data.

The model route remains controlled by server `.env` in this change. The UI shows the configured route instead of pretending the static selector changes the backend model.

## Testing

- Unit tests cover profile parsing, validation, staged commit, and session isolation.
- Stream mapping tests prove no raw tool data is exposed.
- API tests use a fake streaming application and never call an LLM or Binance.
- UI tests cover SSE decoding/event rendering helpers without a browser or network.
- Existing deterministic, security, and gateway tests remain green.
