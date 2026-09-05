# Safe Conversation Memory Design

## Goal

Let Sentinel understand follow-up messages such as "tăng trưởng hơn" without treating old portfolio, market, or risk results as current facts.

## Design

- Use an in-memory Agents SDK `SQLiteSession` per application session ID. No database file is created, and history is lost when the process stops.
- Pass the same conversation session to each `Runner.run` call for that user.
- Use `RunConfig.session_input_callback` to include only recent user and assistant messages in the next run.
- Remove old function calls, function outputs, and reasoning items from model input.
- Keep at most eight conversational messages.
- Strip the injected policy wrapper from historical user items so old policy snapshots are not replayed as current policy.
- Continue creating a new `SentinelRunContext` for every request.
- The current validated policy injected by Python is authoritative.
- Any current financial analysis must still call fresh read-only tools and deterministic evaluation.

## Boundaries

Conversation memory helps resolve references, preferences, and follow-up intent. It is never an authoritative source for current balances, prices, volatility, calculations, plan status, or execution state.

## Testing

- The same session ID reuses one Agents SDK session.
- Different session IDs do not share history.
- Historical tool calls and outputs are filtered.
- Historical user messages retain only their original user text, not prior policy snapshots.
- The current input remains unchanged and contains the latest validated policy.
- Existing Agent-loop safety tests remain green.
