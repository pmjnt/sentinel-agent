# Sentinel Project Guide HTML — Design

**Date:** 2026-09-05  
**Output:** `docs/sentinel-project-guide.html`

## Purpose

Create a self-contained Vietnamese handbook that helps a Java/Spring Boot
developer understand what Sentinel currently contains, why its boundaries were
chosen, how data moves through the system, and how individual files depend on
one another.

The guide must distinguish implemented runtime behavior from domain code that
exists but is not yet connected end-to-end, and from future work.

## Content structure

The page will contain:

1. A concise current-state summary and status legend.
2. The implementation journey from mock tools, through the rejected custom MCP
   route, to official Binance Skills Hub and `binance-cli`.
3. Responsibility boundaries for the LLM, tools, gateway, deterministic Python,
   RiskEngine, and user.
4. Two end-to-end flows:
   - current BTC analysis runtime;
   - policy-driven target workflow, with unconnected steps marked clearly.
5. A folder tree and a file relationship catalog. Each entry states its role,
   input/output, dependencies, and consumers.
6. Configuration and LiteLLM model routing.
7. Binance Demo integration, CLI allowlist, credential flow, validation, and
   fail-closed behavior.
8. Testing strategy and verified project status.
9. A clearly separated next-steps section.
10. A Java/Spring Boot analogy table for orientation.

## Accuracy rules

- Derive descriptions from the current repository rather than the historical
  SRD alone.
- Label content as `ĐÃ HOẠT ĐỘNG`, `ĐÃ VIẾT — CHƯA NỐI END-TO-END`, or `TƯƠNG LAI`.
- State that the current web UI is static and its activity animation is simulated.
- State that policy parsing and deterministic services exist, but `main.py`
  currently runs the simpler two-tool analysis Agent rather than the complete
  policy orchestration workflow.
- Never claim that trading, FastAPI, persistence, production Binance, or MCP is
  active.
- Do not expose secrets, `.env` contents, hidden chain-of-thought, or real account
  data.

## Visual direction

Use a restrained vintage technical-field-manual style:

- paper: `#eee8d8`;
- ink: `#25231f`;
- muted ink: `#686155`;
- olive: `#435744`;
- rust: `#9a4f36`;
- rule: `#b8ad98`.

Use local/system serif typography for headings, readable sans-serif for prose,
and monospace for code and file paths. No external fonts or libraries.

The signature element is a layered “system rail”: a vertical visual path that
connects User → LLM → Tools → Gateway → CLI → Binance Demo, with status labels
and file references attached to each stop.

## Interaction and accessibility

- Self-contained HTML, CSS, and minimal JavaScript.
- Sticky desktop navigation; compact mobile navigation.
- Collapsible file groups to keep the catalog manageable.
- Visible keyboard focus, semantic landmarks, sufficient contrast, and
  `prefers-reduced-motion` support.
- Print styles so the document can be exported to PDF cleanly.

## Scope boundary

This task creates documentation only. It does not change Sentinel runtime,
connect the policy orchestration flow, add backend APIs, enable trading, or add
new dependencies.

## Validation

- Parse the HTML using Python's standard-library HTML parser.
- Add a lightweight test that checks required headings, status labels, file
  references, and explicit current/future distinctions.
- Run the related test, full pytest suite, UI test, compile check, and
  `git diff --check`.
