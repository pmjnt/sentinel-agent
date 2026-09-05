# Grounded Advice Design

## Goal

Make Sentinel explain the evidence and rationale behind qualitative advice, and retain up to 16 recent conversational messages.

## Behavior

- Python continues to render authoritative evidence from validated domain models.
- After analysis, the LLM organizes its prose as Assessment, Rationale, Recommendation, and Limitations in the user's language.
- Every assessment and recommendation must be grounded in the current `PortfolioAnalysis`; the LLM may not invent numeric evidence.
- A concrete allocation or asset recommendation requires the user's objective, time horizon, and acceptable loss/risk tolerance. When any is missing, Sentinel asks one concise clarification question instead of inventing it.
- General educational guidance may remain non-specific and must not imply execution.
- Hidden chain-of-thought is never requested or displayed; rationale means concise, user-verifiable reasons.
- Conversation filtering keeps the latest 16 user/assistant messages. Historical tool data remains excluded.

## Testing

- Verify the 16-message history limit.
- Verify the active Agent instructions contain the advice structure, grounding rule, and suitability clarification rule.
- Keep all existing deterministic safety and tool-loop tests passing.
