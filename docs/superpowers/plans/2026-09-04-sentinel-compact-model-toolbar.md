# Sentinel Compact Model Toolbar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the large provider/model configuration block with a compact, accessible one-line toolbar.

**Architecture:** Keep existing provider/model JavaScript behavior unchanged. Adjust semantic HTML to group both labeled selects and a free-tier marker in one toolbar, then use responsive CSS to keep it compact on desktop and wrap safely on mobile.

**Tech Stack:** HTML5, CSS3, Node built-in test runner

---

### Task 1: Compact toolbar structure

**Files:**
- Modify: `tests/test_ui.js`
- Modify: `web/index.html`

- [ ] **Step 1: Write the failing static-markup test**

Add a test that reads `web/index.html`, requires `class="model-toolbar"`, and rejects the old `route-preview` and `model-note` blocks.

```javascript
test("uses a compact model toolbar without verbose route help", () => {
  const html = readFileSync(join(__dirname, "../web/index.html"), "utf8");
  assert.match(html, /class="model-toolbar"/);
  assert.doesNotMatch(html, /class="route-preview"/);
  assert.doesNotMatch(html, /class="model-note"/);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test tests/test_ui.js`

Expected: FAIL because the current markup still uses `selector-grid`, `route-preview`, and `model-note`.

- [ ] **Step 3: Implement the compact markup**

Change the configuration wrapper to `model-toolbar`, keep both explicit labels and selects, add a visible `FREE TIER` marker, and delete both verbose paragraphs. Remove the now-unused `#agent-model-route` lookup and assignment from `web/app.js` while retaining the pure `getAgentModelRoute` function used by tests and documentation.

- [ ] **Step 4: Run the test and verify GREEN**

Run: `node --test tests/test_ui.js`

Expected: all six JavaScript tests pass.

### Task 2: Compact responsive styling

**Files:**
- Modify: `web/styles.css`

- [ ] **Step 1: Replace the field-block layout**

Make `.model-toolbar` an inline grid containing label/select pairs, retain 44px control height, constrain the provider and model widths, and style the free-tier marker as a small square stamp. Remove obsolete `.selector-grid`, `.route-preview`, and `.model-note` rules.

- [ ] **Step 2: Add mobile wrapping**

At `max-width: 600px`, allow the toolbar to use the full width and wrap provider and model groups without horizontal overflow.

- [ ] **Step 3: Run full verification**

Run:

```bash
node --test tests/test_ui.js
.venv/bin/python -m pytest -q
node --check web/app.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: every command exits successfully; JavaScript reports six passing tests and Python reports nine passing tests.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ui.js web/index.html web/styles.css web/app.js
git commit -m "fix: compact model selection toolbar"
```
