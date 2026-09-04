# Sentinel Vintage UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static vintage web interface that demonstrates provider/model selection and Sentinel's mocked tool-calling progress.

**Architecture:** Use one semantic HTML document, one CSS stylesheet, and one plain JavaScript file. Keep model selection, prompt validation, and activity-step definitions as pure CommonJS-compatible functions for Node tests; browser-only code renders the same data and simulates the Agent run without calling a backend.

**Tech Stack:** HTML5, CSS3, plain JavaScript, Node built-in test runner, existing Python 3.12 test suite

---

### Task 1: Testable UI domain logic

**Files:**
- Create: `web/app.js`
- Create: `tests/test_ui.js`

- [ ] **Step 1: Write failing Node tests**

Test that `getModelsForProvider("openai")` returns `gpt-5.6-luna` and `gpt-5.4-mini`; Gemini returns `gemini-3.8-flash` and `gemini-3.1-pro-preview`; `isValidPrompt` rejects whitespace; and `buildActivitySteps()` contains `get_portfolio()` before `get_market_data("BTCUSDT")` and ends with `Report ready`.

- [ ] **Step 2: Run tests and verify RED**

Run: `node --test tests/test_ui.js`
Expected: FAIL because `web/app.js` is missing.

- [ ] **Step 3: Implement minimal pure functions**

Define a frozen `MODEL_OPTIONS`, `getModelsForProvider`, `isValidPrompt`, and `buildActivitySteps`. Export them with `module.exports` when Node is present; guard browser initialization with `typeof document !== "undefined"`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `node --test tests/test_ui.js`
Expected: all JavaScript tests pass.

### Task 2: Semantic analysis desk markup

**Files:**
- Create: `web/index.html`

- [ ] **Step 1: Build the document structure**

Create a masthead, mocked-data notice, provider/model controls, labeled request textarea, submit button, run metadata, activity log with `aria-live`, tool evidence area, and report sections for facts and interpretation. Use a normal deferred `<script src="app.js">` and no external fonts/assets.

- [ ] **Step 2: Confirm static references**

Run: `test -f web/index.html && test -f web/app.js`
Expected: exit code 0.

### Task 3: Vintage visual system

**Files:**
- Create: `web/styles.css`
- Modify: `web/index.html`

- [ ] **Step 1: Implement the paper-and-ink design**

Use CSS custom properties for paper, ink, muted ink, stamp red, brass, borders and shadows. Build paper texture with layered CSS backgrounds; use local serif/monospace font stacks, square controls, double rules, stamped labels, a two-column desktop grid and single-column mobile layout.

- [ ] **Step 2: Add accessible states**

Style keyboard focus, disabled submit, pending/active/complete log rows, negative market values, tool evidence, validation error, and `prefers-reduced-motion` behavior.

### Task 4: Simulated Agent interaction

**Files:**
- Modify: `web/app.js`

- [ ] **Step 1: Wire provider/model selection**

Populate model options on load and replace them when provider changes. Display selected provider/model in the run metadata.

- [ ] **Step 2: Implement the simulation state machine**

On valid form submission, clear previous output, disable the button, render nine pending steps, advance them one by one with timers, reveal portfolio and market evidence at their return steps, then reveal the final report. Track a run token and clear prior timers so re-running cannot mix events.

- [ ] **Step 3: Implement validation and accessibility announcements**

Reject whitespace-only prompts, show an inline message, focus the textarea, and update a visually hidden `aria-live` status throughout the run.

- [ ] **Step 4: Re-run JavaScript tests**

Run: `node --test tests/test_ui.js`
Expected: all tests still pass.

### Task 5: Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the static UI**

Add the `web/` files to the project tree, explain that progress and output are simulated, and provide `python -m http.server 8000 -d web` with `http://localhost:8000` as the preview URL.

- [ ] **Step 2: Document the future seam**

Explain that a future FastAPI SSE/WebSocket stream replaces the JavaScript timer while the event renderer and UI remain.

### Task 6: Verification and visual QA

**Files:**
- Review: `web/index.html`, `web/styles.css`, `web/app.js`, `tests/test_ui.js`, `README.md`

- [ ] **Step 1: Run automated verification**

Run: `node --test tests/test_ui.js`, `.venv/bin/python -m pytest -q`, `.venv/bin/python -m compileall -q app main.py tests`, and `git diff --check`.
Expected: every command exits 0.

- [ ] **Step 2: Serve the UI locally**

Run: `.venv/bin/python -m http.server 8000 -d web`.
Expected: the server responds successfully at `http://127.0.0.1:8000`.

- [ ] **Step 3: Inspect desktop and mobile layouts**

Open the local page in the in-app browser, capture desktop and narrow-width screenshots, run the simulated analysis, and verify progress states, evidence reveal, report layout, keyboard focus, overflow and contrast.

- [ ] **Step 4: Fix visual defects and repeat checks**

Apply only defects found during QA, rerun automated verification, and repeat screenshots until the layout is clean at both widths.

