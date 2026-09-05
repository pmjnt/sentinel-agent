# Policy Analysis Orchestrator — Design

**Date:** 2026-09-05

## Goal

Connect the implemented Request Interpreter, policy session, Binance Demo
gateway, deterministic policy/planning/risk services, and LLM explanation into
one console workflow.

## Request flow

Every console message enters `SentinelApplication`:

```text
message + current session policy
  → AgentRequestInterpreter
  → validated ordered actions
  → PolicyConversationService
      ├─ UPDATE_POLICY → session store
      ├─ VIEW_POLICY → natural-language formatter
      ├─ NEEDS_CLARIFICATION → focused question
      └─ ANALYZE_PORTFOLIO → analysis_requested
```

When analysis is requested, `PortfolioAnalysisService` deterministically:

1. reads the Binance Demo portfolio through `PortfolioMarketGateway`;
2. calculates policy violations;
3. derives required market symbols from focus symbols and concentration
   violations;
4. retrieves those markets concurrently through the gateway;
5. creates a rebalance proposal;
6. runs RiskEngine and copies its status onto the proposal;
7. returns one validated `PortfolioAnalysis` model.

A tool-free `Sentinel Analysis Reporter` LLM receives only the user's question
and the validated analysis model. It explains facts and interpretation in
natural language but cannot call Binance or alter the decision.

## AI responsibility

The Request Interpreter autonomously selects ordered application actions from
natural language. The Reporter performs qualitative explanation. Python remains
authoritative for state mutation, required data retrieval, arithmetic, policy
violations, proposal construction, and risk status.

This uses two LLM calls for an analysis request and one for update/view requests.
It avoids a second Policy Parser Agent and prevents the explanatory LLM from
controlling financial state.

## Files

- `app/models/analysis.py`: validated aggregate passed between deterministic
  analysis and the Reporter.
- `app/services/portfolio_analysis_service.py`: deterministic analysis use case.
- `app/agent/analysis_reporter.py`: tool-free natural-language Reporter.
- `app/application.py`: top-level conversational orchestrator.
- `main.py`: constructs the application once and sends every console message to
  it using one in-memory session ID.

Existing `get_portfolio` and `get_market_data` AI tool wrappers remain in the
repository as the simple tool-use example, but the policy-driven console flow
uses the gateway through `PortfolioAnalysisService` so mandatory safety checks
cannot be skipped by the Reporter.

## Market selection

- `BTC` becomes `BTCUSDT`;
- `BTCUSDT` remains unchanged;
- `USDT` requires no market pair;
- every `MAX_ASSET_WEIGHT` violation adds `<ASSET>USDT`;
- duplicates are removed while preserving order.

Any required market error stops plan/risk production. Sentinel reports that
market conditions could not be verified and never falls back to mock data.

## Response behavior

- update-only and view-only messages return deterministic Vietnamese text;
- clarification returns the Interpreter's focused question without analysis;
- analysis-only messages return the Reporter output;
- update/view followed by analysis returns the deterministic policy response,
  then the Reporter output;
- no response contains raw credentials or claims a trade occurred.

## Scope boundary

This completes the local console policy-analysis loop. It does not add FastAPI,
connect the static UI, persist sessions, enable production Binance, request
approval, or execute trades.

## Tests

All new tests use fake gateways, fake interpreters, and fake LLM runners. Required
coverage includes update-only, view-only, update-then-analyze ordering, focus
market selection, violation-driven market selection, high-volatility blocking,
market failure, Reporter input, and no real external calls.
