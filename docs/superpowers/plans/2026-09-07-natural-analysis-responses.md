# Natural Analysis Responses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove Sentinel's mandatory four-heading answer template while preserving evidence grounding and disclosure rules.

**Architecture:** Change only the active controlled Agent prompt and its contract test. Deterministic facts and execution state remain outside model prose.

**Tech Stack:** Python 3.12, pytest, OpenAI Agents SDK prompt instructions

---

### Task 1: Allow natural response structure

**Files:**
- Modify: `tests/unit/test_tool_loop.py`
- Modify: `app/agent/prompts.py`

- [ ] **Step 1: Write the failing prompt-contract test**

Replace assertions requiring four fixed headings with assertions that the prompt
contains `Choose a natural response structure` and does not contain
`organize your response with localized headings equivalent to Assessment`.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/test_tool_loop.py -q`

Expected: fail because the active prompt still requires the fixed headings.

- [ ] **Step 3: Update the active prompt**

Tell the Agent to choose paragraphs, short headings, bullets, or numbered choices
according to content and length. Require material uncertainty to be disclosed
naturally and retain all evidence-grounding and safety instructions.

- [ ] **Step 4: Run complete verification**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py
git diff --check
```

Expected: every command exits successfully.

- [ ] **Step 5: Commit both approved response improvements**

```bash
git add app/agent/prompts.py tests/unit/test_tool_loop.py web/app.js web/styles.css tests/test_ui.js docs/superpowers/plans
git commit -m "fix: improve response readability"
```
