# Sentinel Project Documentation Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish an English GitHub introduction and an accurate Vietnamese reference for Sentinel's current capabilities.

**Architecture:** `README.md` is the concise public entry point; `docs/current-capabilities.md` is the detailed current-state reference. Both documents derive claims from the existing source, tests, configuration example, and established safety boundaries rather than describing planned features as complete.

**Tech Stack:** Markdown, Python 3.12 project tests, Git, GitHub remote

---

### Task 1: Write the detailed current-capabilities reference

**Files:**
- Create: `docs/current-capabilities.md`
- Read: `app/agent/controlled_tools.py`
- Read: `app/agent/tool_loop.py`
- Read: `app/application.py`
- Read: `app/services/risk_service.py`
- Read: `app/services/execution_service.py`
- Read: `app/binance/gateway.py`

- [ ] **Step 1: Build an evidence checklist from current code**

Confirm the active tool names, Agent loop, policy/profile fields, research limits,
Risk Engine decisions, Demo execution guards, SSE fields, storage lifetime, model
routing, and unsupported capabilities directly from source.

- [ ] **Step 2: Write the Vietnamese document**

Create `docs/current-capabilities.md` with these concrete sections:

```text
Tổng quan
Sentinel đang làm được gì
Vai trò của LLM và Python
12 Agent tools
Luồng phân tích portfolio
Policy và investor profile qua chat
Adaptive Binance market research
Risk Engine
Trade proposal, approval và Binance Demo execution
Conversation memory, API, streaming và UI
Model switching qua LiteLLM
File map
Giới hạn hiện tại
Câu lệnh chạy và prompt mẫu
```

Use concise Vietnamese explanations, small flow diagrams, and exact limits from
the code. Mark production trading, database persistence, Binance MCP, news data,
and unrestricted autonomous execution as unsupported.

- [ ] **Step 3: Validate content mechanically**

Run:

```bash
grep -n -E 'TODO|TBD|OPENAI_API_KEY=[^y]|GEMINI_API_KEY=[^y]|BINANCE_SECRET_KEY=[^y]' docs/current-capabilities.md
```

Expected: no output.

### Task 2: Rewrite README as an English project introduction

**Files:**
- Modify: `README.md`
- Read: `.env.example`
- Read: `requirements.txt`

- [ ] **Step 1: Replace the long-form README structure**

Write an English README containing:

```text
Project pitch and hackathon positioning
Why Sentinel is an AI Agent
Current feature highlights
Architecture and safety boundary
Quick start and configuration
Console and web usage
Example prompts
Testing
Project structure
Documentation links
Current limitations
Disclaimer
```

Keep it scannable. Link `docs/current-capabilities.md` as the detailed Vietnamese
reference. Do not expose credentials, claim production execution, or describe
Binance MCP as active.

- [ ] **Step 2: Check documented commands and links**

Verify every relative Markdown link resolves to an existing path and every setup
variable named in README exists in `.env.example` or is explicitly described as
optional.

### Task 3: Verify and publish

**Files:**
- Test: `tests/test_project_guide.py`
- Test: `tests/test_srd_guide.py`

- [ ] **Step 1: Run documentation and full project validation**

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app main.py
node --test tests/test_ui.js
git diff --check
```

Expected: all tests pass, compilation succeeds, and diff-check prints nothing.

- [ ] **Step 2: Review the documentation diff**

Run:

```bash
git diff -- README.md docs/current-capabilities.md
```

Expected: README is English, the detailed guide is Vietnamese, and both describe
only implemented behavior.

- [ ] **Step 3: Commit the documentation**

```bash
git add README.md docs/current-capabilities.md
git commit -m "docs: summarize current Sentinel capabilities"
```

- [ ] **Step 4: Configure and verify the GitHub target**

If `git remote -v` is empty, obtain the GitHub repository URL and visibility from
the user. Add only that confirmed remote, then verify it with `git remote -v`.

- [ ] **Step 5: Push the current branch**

```bash
git push -u origin main
```

Expected: GitHub accepts the current `main` branch without force-pushing.
