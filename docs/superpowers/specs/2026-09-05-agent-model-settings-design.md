# Agent Model Settings Design

**Goal:** Ensure every LiteLLM-backed Agent sends an explicit, provider-aware
output budget instead of relying on defaults that cannot recognize a prefixed
`litellm/...` model route.

## Configuration

- Add `LLM_MAX_TOKENS`, defaulting to `4096` and requiring a positive integer.
- Apply `max_tokens` to every Sentinel Agent.
- Omit provider-specific reasoning effort. GPT-5.4 Mini already defaults to
  `none`; the redundant setting can make LiteLLM bridge tool calls to a less
  stable request path.

## Structure

`app/agent/model_settings.py` builds the SDK `ModelSettings`. Request
The active tool-loop Agent and legacy Agent factories all use this one builder
so provider switching cannot leave their settings out of sync.

## Verification

Unit tests assert OpenAI/Gemini settings, environment parsing, and Agent
factories. An isolated real controlled-loop smoke test validates the configured
OpenAI request without calling Binance for general chat.
