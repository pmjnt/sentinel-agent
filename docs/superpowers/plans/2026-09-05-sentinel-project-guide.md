# Sentinel Project Guide HTML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Vietnamese HTML handbook that accurately explains Sentinel's implementation, architecture, file relationships, runtime flows, security boundaries, current gaps, and next steps.

**Architecture:** Add one documentation artifact with embedded CSS and minimal JavaScript, plus one contract test that parses the document without network access. Keep runtime code unchanged and link the new guide from the existing README.

**Tech Stack:** HTML5, CSS3, minimal vanilla JavaScript, Python 3.12 standard-library `html.parser`, pytest.

---

## File map

- Create `docs/sentinel-project-guide.html`: the complete self-contained handbook.
- Create `tests/test_project_guide.py`: structural and accuracy contract for the handbook.
- Modify `README.md`: add the guide to the documentation index.

### Task 1: Define the documentation contract

**Files:**
- Create: `tests/test_project_guide.py`
- Test: `tests/test_project_guide.py`

- [x] **Step 1: Write the failing document test**

Create a test that:

- loads `docs/sentinel-project-guide.html`;
- parses it with `html.parser.HTMLParser` and asserts there is exactly one
  `<main>` and at least one `<nav>`;
- checks for the three exact status labels `ĐÃ HOẠT ĐỘNG`,
  `ĐÃ VIẾT — CHƯA NỐI END-TO-END`, and `TƯƠNG LAI`;
- checks for the runtime chain `main.py`, `app/agent/sentinel.py`,
  `app/tools/portfolio.py`, `app/tools/market.py`,
  `app/binance/gateway.py`, `app/binance/runner.py`, and `binance-cli`;
- checks for the policy files `app/agent/policy_parser.py`,
  `app/services/policy_conversation_service.py`,
  `app/services/policy_service.py`, `app/services/rebalance_service.py`, and
  `app/services/risk_service.py`;
- checks for explicit statements that the web UI is static/simulated, policy
  orchestration is not connected to `main.py`, MCP is inactive, and trading is
  unavailable;
- verifies that no secret-looking assignment such as
  `BINANCE_SECRET_KEY=<non-placeholder value>` appears.

- [x] **Step 2: Run the test to verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_project_guide.py -q
```

Expected: FAIL because `docs/sentinel-project-guide.html` does not exist.

- [x] **Step 3: Commit the RED contract**

```bash
git add tests/test_project_guide.py
git commit -m "test: define Sentinel project guide contract"
```

### Task 2: Build the self-contained HTML handbook

**Files:**
- Create: `docs/sentinel-project-guide.html`
- Test: `tests/test_project_guide.py`

- [x] **Step 1: Create the semantic page shell**

Add:

- a masthead with the current project status;
- a sticky `<nav>` linked to every major section;
- one `<main>` containing overview, implementation journey, architecture,
  runtime flow, policy flow, file map, configuration, security, tests, Java
  analogy, and next steps;
- a footer with the document date and scope boundary.

Use only relative repository links such as `../app/config.py` and
`../main.py`; do not add external scripts, stylesheets, fonts, or analytics.

- [x] **Step 2: Add accurate project content**

Describe the current repository with these boundaries:

```text
Current runtime:
User → Sentinel LLM → application tools → BinanceCliGateway
→ BinanceCliRunner → binance-cli → Binance Demo

Implemented but not connected end-to-end:
policy parser → policy conversation → deterministic policy checks
→ rebalance planner → RiskEngine

Future:
FastAPI → live UI activity stream → approval → execution verification
```

For each source file, include its purpose, inputs/outputs, imports or
dependencies, and consumers. Explain `__init__.py`, Pydantic transport/domain
models, LiteLLM routing, the fixed read-only command list, credential boundary,
schema validation, deterministic calculations, and fail-closed errors.

- [x] **Step 3: Apply the approved visual system**

Use embedded CSS variables for the approved paper, ink, muted ink, olive, rust,
and rule colors. Build the signature vertical system rail, status chips, file
relationship cards, responsive layout, print styles, visible focus states, and
reduced-motion handling. Keep prose typography readable and file paths
monospaced.

- [x] **Step 4: Add minimal progressive enhancement**

Use a short inline script only to:

- update the active navigation link based on visible sections;
- provide “expand all / collapse all” controls for native `<details>` file
  groups.

The document must remain fully readable when JavaScript is disabled.

- [x] **Step 5: Run the guide test to verify GREEN**

```bash
.venv/bin/python -m pytest tests/test_project_guide.py -q
```

Expected: PASS.

- [x] **Step 6: Commit the handbook**

```bash
git add docs/sentinel-project-guide.html tests/test_project_guide.py
git commit -m "docs: add Sentinel project handbook"
```

### Task 3: Link and validate the handbook

**Files:**
- Modify: `README.md`
- Test: `tests/test_project_guide.py`

- [ ] **Step 1: Add the README documentation link**

Add `docs/sentinel-project-guide.html` to the “More detail” list with a clear
Vietnamese label identifying it as the current implementation handbook.

- [ ] **Step 2: Validate HTML and repository checks**

Run:

```bash
.venv/bin/python -m pytest tests/test_project_guide.py -q
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: all tests pass, compile exits 0, and `git diff --check` has no output.

- [ ] **Step 3: Check documentation accuracy**

Compare the guide's current-state claims against `main.py`, `app/agent`,
`app/tools`, `app/binance`, `app/services`, `.env.example`, and the current test
tree. Confirm every inactive or future capability is visibly labeled and that
no credentials or real account values appear.

- [ ] **Step 4: Commit the README link and final verification record**

```bash
git add README.md docs/superpowers/plans/2026-09-05-sentinel-project-guide.md
git commit -m "docs: link Sentinel implementation handbook"
```
