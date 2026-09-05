# Agent Model Settings Design

**Goal:** Ensure every LiteLLM-backed Agent sends an explicit, provider-aware
output budget instead of relying on defaults that cannot recognize a prefixed
`litellm/...` model route.

## Configuration

- Add `LLM_MAX_TOKENS`, defaulting to `4096` and requiring a positive integer.
- Apply `max_tokens` to every Sentinel Agent.
- For OpenAI models whose ID starts with `gpt-5`, explicitly set reasoning
  effort to `none`, matching the installed Agents SDK default for
  `gpt-5.4-mini`.
- Do not send OpenAI reasoning settings to Gemini.

## Structure

`app/agent/model_settings.py` builds the SDK `ModelSettings`. Request
Interpreter, Analysis Reporter, and the educational tool-calling Sentinel Agent
all use this one builder so provider switching cannot leave their settings out
of sync.

## Verification

Unit tests assert OpenAI/Gemini settings, environment parsing, and all Agent
factories. An isolated real Request Interpreter smoke test validates the
configured OpenAI request without calling Binance.
