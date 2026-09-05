# Controlled Tool-Calling Agent Loop Design

**Date:** 2026-09-05

## Goal

Make Sentinel a real agent loop: the LLM chooses a tool, receives its result,
uses that observation to choose the next tool, and then explains the validated
outcome. Python remains authoritative for calculations, policy state, and risk.

## Chosen approach

Use one tool-calling Sentinel Agent with a per-run Python context. Read-only
tools execute during the loop and return structured observations to the LLM.
Policy updates are staged in the context and committed only after the Agent run
finishes successfully.

The Agent receives these tools:

```text
get_portfolio()
get_market_data(symbol)
update_policy(changes=[{field, value_as_text}])
view_policy()
evaluate_portfolio_risk(focus_symbols)
```

No order, transfer, withdrawal, generic CLI, or arbitrary Binance tool is
available.

## Agent loop

```text
User request
  ↓
Sentinel LLM
  ↓ get_portfolio()
Trusted Portfolio stored in run context and returned to LLM
  ↓ get_market_data("BTCUSDT")
Trusted MarketData stored in run context and returned to LLM
  ↓ evaluate_portfolio_risk(["BTC"])
Python calculates violations, plan, and RiskDecision from cached trusted data
  ↓
Validated PortfolioAnalysis returned to LLM and retained by Python
  ↓
LLM writes a concise qualitative explanation
  ↓
Python renders authoritative facts and execution state
```

The evaluation tool never accepts portfolio values, market prices, allocation
percentages, plan status, or risk status from the LLM. It reads only Pydantic
objects previously produced by the gateway and stored in the run context.

If required data is missing, it returns a structured missing-observation result
that names the next read-only tool call required. It does not fabricate a safe
result.

## Policy behavior

`update_policy` accepts field names and simple text values. Python parses each
value as decimal, boolean, or `null`, then validates the resulting patch. It
updates only the run's working policy and records a patch. Later
tool calls in the same message see the working policy, so “update then analyze”
uses the new rule.

The session store is updated only after the complete Agent run succeeds. A
provider failure cannot leave a half-applied policy update. `view_policy`
returns the current working policy to the LLM and records a deterministic view
event for the final response.

## User-facing output

- With no tool call, only general chat or clarification may complete. A request
  for financial observations must produce deterministic analysis or fail closed.
- Policy confirmations and policy views are rendered by deterministic Python.
- Analysis facts, proposals, RiskDecision, and `NOT_EXECUTED` are rendered by
  deterministic Python.
- The Agent adds qualitative judgment when the user asks whether exposure is
  risky, why it matters, or what they should consider doing next. It may compare
  concentration, volatility, liquidity, and the user's policy; explain
  trade-offs; and suggest non-executing next steps grounded in tool results.
- Agent judgment is labeled as AI interpretation. It cannot invent facts,
  perform authoritative arithmetic, guarantee outcomes, replace the RiskEngine
  status, or claim that an action was executed. Reserved execution/risk claims
  are rejected.

Example:

```text
Python facts: BTC is 55%; policy maximum is 40%; volatility is HIGH.
RiskEngine: BLOCKED.
AI interpretation: BTC concentration currently creates elevated downside risk.
Because volatility is high and your policy blocks rebalancing, consider waiting
and reassessing when verified volatility falls rather than acting now.
```

## Model configuration

Every Agent request sends an explicit output budget. The default is
`LLM_MAX_TOKENS=4096`. Provider-specific reasoning options are omitted. Tool calls are sequential with
`parallel_tool_calls=false` so observation and policy order are deterministic.
One analysis is capped at 20 market observations, with a derived 28-turn Agent
budget; larger scopes fail closed instead of exhausting the loop unpredictably.

## Migration

The current `ParsedRequest` action models remain useful as internal typed
commands, but are removed from the Agent's `output_type`. The existing
structured-output Request Interpreter and separate Reporter are removed from
the main runtime after equivalent tool-loop tests pass. Deterministic portfolio,
policy, rebalance, risk, gateway, and response-formatting code is retained.

## Failure handling

- Portfolio or market failure produces a structured tool error and a safe
  deterministic final message.
- Missing observations prevent risk evaluation.
- Invalid tool arguments are rejected by Pydantic/tool schema.
- LLM/provider failure commits no staged policy change.
- No failure path implies that a trade or transfer happened.

## Required tests

- General chat invokes no tools.
- Portfolio analysis calls portfolio, relevant market, then evaluation.
- Tool results are visible to the next LLM turn.
- Evaluation rejects missing portfolio or market observations.
- Risk output comes from deterministic services.
- Policy updates are staged, ordered, and committed only after success.
- Provider failure leaves session policy unchanged.
- No execution-capable tool is exposed.
- OpenAI and Gemini receive compatible model settings.
- Unit tests make no external LLM or Binance calls.
- One isolated OpenAI smoke test proves the real loop after offline tests pass.
