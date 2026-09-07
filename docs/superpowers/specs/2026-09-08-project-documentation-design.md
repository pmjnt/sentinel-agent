# Sentinel Project Documentation Design

## Goal

Provide a clear GitHub entry page in English and a separate Vietnamese reference
that accurately summarizes what Sentinel can do today.

## Deliverables

### `README.md`

The README is an English project introduction for GitHub visitors. It will lead
with Sentinel's purpose, explain why the project is an AI Agent rather than a
chatbot, summarize the architecture and current capabilities, show the safety
boundary, provide setup/run/test instructions, and link to detailed documents.
It will stay scannable and avoid duplicating every implementation detail.

### `docs/current-capabilities.md`

This Vietnamese document is the detailed current-state reference. It will cover:

- the LLM, deterministic Python, Risk Engine, Binance gateway, and UI roles;
- all twelve controlled Agent tools;
- portfolio analysis, policy chat, investor profile, adaptive market research,
  conversation memory, streaming activity, model selection, trade proposal,
  approval, and Binance Demo execution;
- important data flows and file relationships;
- safety constraints, in-memory limitations, and features not implemented;
- practical example prompts and ways to verify the project.

## Accuracy Rules

- Describe only functionality present in the current source tree.
- Clearly distinguish recommendations, trade plans, approval, and execution.
- Label financial account and execution functionality as Binance Demo.
- Do not claim production trading, persistent storage, unrestricted autonomy,
  news research, arbitrary token execution, or MCP integration.
- Do not include credentials or local `.env` values.

## Verification

- Check every referenced path exists.
- Check README links point to existing files.
- Run project documentation tests and `git diff --check`.
- Review the final Git diff before committing and pushing.

## GitHub Publishing

Commit both documentation files to the current `main` branch. Push only after a
GitHub remote is configured and its target is confirmed; do not invent a remote
or choose repository visibility on the user's behalf.
