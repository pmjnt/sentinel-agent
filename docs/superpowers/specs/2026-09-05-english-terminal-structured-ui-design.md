# English Terminal Output and Structured UI Design

## Goal

Make every fixed, user-facing runtime message in the current terminal application English while preserving Sentinel's ability to understand Vietnamese and English input.

## Scope

- Translate fixed terminal output produced by Python services and `main.py` to English.
- Keep Vietnamese intent-detection and safety patterns because they validate user input and model output rather than render fixed UI copy.
- Keep domain models and deterministic calculations unchanged.
- Update tests that assert fixed runtime copy.
- Do not add FastAPI or a frontend in this change.

## Output boundary

The terminal remains a presentation adapter. It renders trusted structured values from `PortfolioAnalysis`, `PortfolioPolicy`, `RebalancePlan`, and `RiskDecision`, then appends the LLM's separate qualitative interpretation.

The future UI must not parse terminal text. A future API should serialize structured response fields such as:

```json
{
  "portfolio": {},
  "policy": {},
  "violations": [],
  "market_data": [],
  "plan": {},
  "risk_decision": {},
  "execution_status": "NOT_EXECUTED",
  "ai_interpretation": "..."
}
```

The existing `SentinelResponse.analyses` and policy data already preserve most of this structured information. API-specific response models will be introduced only when the API phase begins.

## Data flow

1. Tools and deterministic services build validated domain objects.
2. Python formatters produce English terminal text from those objects.
3. The LLM produces only the qualitative interpretation.
4. `SentinelApplication` joins the two sections for the console.
5. A future API maps the same domain objects to JSON instead of reusing or parsing console text.

## Safety

Risk status, execution status, portfolio values, violations, and plan actions remain authoritative Python data. Translating fixed labels must not move formatting or decision authority to the LLM.

## Testing

- Tests assert English fixed output for analysis, policy updates, policy views, configuration/debug warnings, and data failures.
- Vietnamese user-input and safety-recognition tests remain in place.
- The complete Python and UI test suites must pass.
