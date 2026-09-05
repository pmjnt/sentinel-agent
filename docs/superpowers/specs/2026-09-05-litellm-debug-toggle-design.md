# LiteLLM Debug Toggle — Design

**Date:** 2026-09-05

## Goal

Allow local troubleshooting with `litellm._turn_on_debug()` without enabling
verbose request logging by default.

## Behavior

- `LITELLM_DEBUG` is an optional boolean environment variable.
- It defaults to `false`.
- `Settings` validates the value through Pydantic.
- During startup, Sentinel calls `litellm._turn_on_debug()` only when the flag is
  true.
- Startup prints a warning that prompts, policy context, and request bodies may
  appear in terminal output.
- `.env.example` documents the flag as disabled.

## Security boundary

Debug mode is intended only for short-lived local diagnosis. It must not print
API key values itself, must not be enabled by default, and its warning must tell
the developer not to share logs publicly.

## Tests

Offline tests verify the default, environment parsing, conditional activation,
and warning. Tests inject a fake debug function and never call an LLM.
