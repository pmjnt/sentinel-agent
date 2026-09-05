# Console Prompt and Diagnostics Design

**Goal:** Prevent duplicate console prompts and expose safe provider diagnostics
when local LiteLLM debug mode is enabled.

## Design

- Print `Sentinel > ` explicitly, then call `input()` without a prompt argument.
  This avoids terminal integrations that echo `input(prompt)` themselves.
- Keep the existing generic failure message.
- When `LITELLM_DEBUG=true`, additionally print the exception type and message.
- Redact configured OpenAI, Gemini, and Binance credentials before printing.
- Do not print a traceback or local variables.

## Tests

- The input reader receives no prompt argument while stdout receives one prompt.
- Debug mode prints the exception type/message but not configured secrets.
- Non-debug mode does not print technical exception details.
