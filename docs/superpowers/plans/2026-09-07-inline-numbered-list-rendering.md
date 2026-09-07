# Inline Numbered List Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render inline numbered choices as a readable ordered list without misclassifying decimal values.

**Architecture:** Extend the existing safe Markdown block parser with ordered-list recognition and reuse the DOM-based inline renderer. No raw model HTML is accepted.

**Tech Stack:** Vanilla JavaScript, Node test runner

---

### Task 1: Parse and render ordered lists

**Files:**
- Modify: `tests/test_ui.js`
- Modify: `web/app.js`

- [ ] **Step 1: Write failing parser tests**

Add one test expecting:

```javascript
parseMarkdownBlocks("1. ETH: cân bằng 2. BTC: an toàn 3. SOL: biến động")
```

to return:

```javascript
[{ type: "ordered-list", items: [
  "ETH: cân bằng",
  "BTC: an toàn",
  "SOL: biến động",
] }]
```

Add a regression assertion that `Lợi nhuận 1.5% trong 2.5 năm.` remains one
paragraph.

- [ ] **Step 2: Verify the tests fail**

Run: `node --test tests/test_ui.js`

Expected: the inline numbered response remains a paragraph.

- [ ] **Step 3: Implement minimal safe parsing and rendering**

In `parseMarkdownBlocks`, recognize a numbered sequence only when it starts with
`1.` and contains `2.`, with every marker followed by whitespace. Emit an
`ordered-list` block. In the DOM renderer, create an `<ol>` and one `<li>` per
item, passing item text through the existing safe inline Markdown renderer.

- [ ] **Step 4: Verify focused and full tests**

Run:

```bash
node --test tests/test_ui.js
.venv/bin/python -m pytest -q
git diff --check
```

Expected: all commands exit successfully.

- [ ] **Step 5: Commit**

```bash
git add web/app.js tests/test_ui.js docs/superpowers/plans/2026-09-07-inline-numbered-list-rendering.md
git commit -m "fix: render inline numbered choices"
```
