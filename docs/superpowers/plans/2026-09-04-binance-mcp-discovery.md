# Binance MCP Read-only Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Authenticate to the official Binance Agentic MCP Server and print its real tool catalog without invoking any Binance tool.

**Architecture:** A small OAuth component owns an in-memory token store and loopback callback. A Binance MCP discovery client uses the installed MCP v2 Streamable HTTP transport to initialize a session and call only `list_tools()`. The catalog is converted to safe application metadata for review; no tool is exposed to the LLM or invoked.

**Tech Stack:** Python 3.12, MCP Python SDK 2, httpx2, Pydantic 2, pytest

---

### Task 1: Pin direct MCP client dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `tests/unit/test_mcp_dependencies.py`

- [x] **Step 1: Write a failing dependency/API test**

Import `OAuthClientProvider`, `TokenStorage`, `streamable_http_client`, `httpx2`, and assert the configured Binance endpoint constant equals `https://agent.binance.com/mcp/agentic`.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_dependencies.py -q
```

Expected: import of `app.mcp.binance` fails because the package does not exist.

- [x] **Step 3: Add direct dependencies and endpoint module**

Add exact compatible ranges:

```text
mcp>=2.1,<3
httpx2>=2.12,<3
```

Create empty `app/mcp/__init__.py` and `app/mcp/binance.py` containing only:

```python
BINANCE_MCP_ENDPOINT = "https://agent.binance.com/mcp/agentic"
```

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_dependencies.py -q
```

- [x] **Step 5: Commit**

```bash
git add requirements.txt app/mcp tests/unit/test_mcp_dependencies.py docs/superpowers/plans/2026-09-04-binance-mcp-discovery.md
git commit -m "build: add Binance MCP client dependencies"
```

### Task 2: In-memory OAuth token storage

**Files:**
- Create: `app/mcp/oauth.py`
- Create: `tests/unit/test_mcp_oauth.py`

- [x] **Step 1: Write failing storage tests**

Test that a new store has no tokens/client information, values round-trip through all four async `TokenStorage` methods, and `clear()` removes both values. Construct SDK values with `OAuthToken` and `OAuthClientInformationFull` so the test tracks the installed MCP API.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_oauth.py -q
```

- [x] **Step 3: Implement `InMemoryOAuthStorage`**

Implement the MCP `TokenStorage` protocol methods:

```text
get_tokens() -> OAuthToken | None
set_tokens(tokens: OAuthToken) -> None
get_client_info() -> OAuthClientInformationFull | None
set_client_info(client_info: OAuthClientInformationFull) -> None
clear() -> None
```

The object has no file I/O and its representation must not reveal tokens.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_oauth.py -q
```

- [x] **Step 5: Commit**

```bash
git add app/mcp/oauth.py tests/unit/test_mcp_oauth.py
git commit -m "feat: hold Binance OAuth state in memory"
```

### Task 3: Loopback OAuth callback

**Files:**
- Modify: `app/mcp/oauth.py`
- Create: `tests/unit/test_mcp_callback.py`

- [x] **Step 1: Write failing callback parsing tests**

Test a pure `parse_authorization_callback(url)` function:

- returns `AuthorizationCodeResult` for `code`, `state`, and `iss`;
- rejects missing code;
- rejects an OAuth `error` parameter with its description.

Also test that `open_authorization_url(url, opener=fake)` sends the exact URL to the injected browser opener.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_callback.py -q
```

- [x] **Step 3: Implement callback helpers**

Use `urllib.parse` and `webbrowser.open`. Create `LoopbackCallbackServer` backed by `HTTPServer` bound to `127.0.0.1` on a configured port before authorization begins. Its async `wait_for_callback()` uses `asyncio.to_thread`, returns the parsed SDK result, sends a minimal UTF-8 success/error HTML page, handles one request, and always supports explicit `close()`.

Do not log the callback URL, code, state, issuer, or token.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_callback.py -q
```

- [x] **Step 5: Commit**

```bash
git add app/mcp/oauth.py tests/unit/test_mcp_callback.py
git commit -m "feat: handle Binance OAuth loopback callback"
```

### Task 4: Safe MCP tool catalog

**Files:**
- Create: `app/models/mcp.py`
- Modify: `app/mcp/binance.py`
- Create: `tests/unit/test_mcp_catalog.py`

- [x] **Step 1: Write failing catalog tests**

Build `mcp.types.Tool` fixtures and assert conversion preserves only:

```text
name
title
description
input_schema
output_schema
read_only_hint
destructive_hint
```

Assert `_meta`, icons, and any other provider object are absent from serialized application metadata. Catalog order must match server order.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_catalog.py -q
```

- [x] **Step 3: Implement catalog conversion**

Create frozen `McpToolCatalogEntry` in `app/models/mcp.py`. Implement `to_catalog_entries(tools: list[Tool]) -> list[McpToolCatalogEntry]` in `app/mcp/binance.py`.

Annotations are untrusted hints. Missing hints remain `None`; the conversion must not infer read-only status from a name or description.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_catalog.py -q
```

- [x] **Step 5: Commit**

```bash
git add app/models/mcp.py app/mcp/binance.py tests/unit/test_mcp_catalog.py
git commit -m "feat: normalize Binance MCP tool catalog"
```

### Task 5: Discovery client and CLI

**Files:**
- Modify: `app/mcp/binance.py`
- Create: `app/mcp/discover.py`
- Create: `tests/unit/test_mcp_discovery.py`

- [x] **Step 1: Write failing discovery boundary tests**

Test a fake MCP session whose `list_tools()` returns fixtures. Assert `BinanceMcpDiscovery.discover_with_session(session)` calls `list_tools()` exactly once, returns normalized entries, and never calls `call_tool()`.

Test CLI JSON rendering from catalog entries separately; serialized output must not contain token-like fields.

- [x] **Step 2: Run and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_discovery.py -q
```

- [x] **Step 3: Implement network discovery**

`BinanceMcpDiscovery.discover()` must:

1. Create and bind `LoopbackCallbackServer`.
2. Create `OAuthClientProvider` with the exact endpoint, native application metadata, authorization-code + refresh-token grants, and no guessed scope string.
3. Create `httpx2.AsyncClient(auth=provider, follow_redirects=True)`.
4. Open `streamable_http_client(endpoint, http_client=client)`.
5. Initialize `ClientSession`.
6. Call only `list_tools()`.
7. Normalize and return the catalog.
8. Close session, HTTP client, callback server in all paths.

`app/mcp/discover.py` runs this flow with `python -m app.mcp.discover`, opens the authorization URL, and prints formatted catalog JSON after success. It must not call any discovered tool.

- [x] **Step 4: Run and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_mcp_discovery.py -q
```

- [x] **Step 5: Commit**

```bash
git add app/mcp/binance.py app/mcp/discover.py tests/unit/test_mcp_discovery.py
git commit -m "feat: discover Binance MCP tools safely"
```

### Task 6: Documentation and local verification

**Files:**
- Create: `docs/binance-mcp.md`
- Modify: `README.md`

- [x] **Step 1: Document discovery and security**

Explain endpoint, OAuth browser requirement, Market Data/Account scope selection, in-memory token lifetime, discovery-only behavior, no tool invocation, no mock fallback, and the command to run.

- [x] **Step 2: Run all offline verification**

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

- [ ] **Step 3: Run real discovery with user OAuth**

```bash
.venv/bin/python -m app.mcp.discover
```

Expected: browser authorization completes and the command prints the real Binance MCP tool catalog. It must show no `tools/call` activity.

Observed on the first run: Binance advertised Client ID Metadata Documents but no
dynamic registration endpoint. The client now requires
`BINANCE_MCP_CLIENT_METADATA_URL` and fails before connecting when it is absent.
Real discovery remains pending until that public HTTPS document is hosted.

- [ ] **Step 4: Review and record mapping inputs**

Review the returned names, descriptions, input schemas, output schemas, and annotations. Do not commit tokens or account data. The next Binance adapter plan must reference only the actual discovered read capabilities.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md docs/binance-mcp.md docs/superpowers/plans/2026-09-04-binance-mcp-discovery.md
git commit -m "docs: explain safe Binance MCP discovery"
```

## Completion boundary

This plan ends after real schema discovery. It deliberately does not call portfolio, market, trade, transfer, cancel, or withdrawal tools. The reviewed catalog is the required input for the next adapter plan.
