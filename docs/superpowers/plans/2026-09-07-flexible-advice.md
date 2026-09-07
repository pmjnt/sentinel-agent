# Flexible Advice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop repetitive profile questions once Sentinel has enough core information and let the LLM present useful alternatives.

**Architecture:** A deterministic helper classifies the validated profile as ready or incomplete. The Agent input exposes that status, while the prompt gives the LLM flexibility to present 2–4 grounded choices without weakening financial safety controls.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, Pydantic, pytest

---

### Task 1: Classify advice profile readiness

**Files:**
- Modify: `app/services/profile_service.py`
- Test: `tests/unit/test_profile.py`

- [ ] **Step 1: Add failing readiness tests**

```python
def test_advice_profile_is_ready_with_objective_horizon_and_acceptable_loss():
    profile = InvestorProfile(
        objective=InvestmentObjective.GROWTH,
        time_horizon_months=12,
        acceptable_loss_percent=Decimal("20"),
    )
    assert is_advice_profile_ready(profile) is True


def test_advice_profile_is_incomplete_without_risk_measure():
    profile = InvestorProfile(
        objective=InvestmentObjective.GROWTH,
        time_horizon_months=12,
    )
    assert is_advice_profile_ready(profile) is False
```

- [ ] **Step 2: Run tests and observe failure**

Run: `.venv/bin/python -m pytest tests/unit/test_profile.py -q`

Expected: import failure because `is_advice_profile_ready` does not exist.

- [ ] **Step 3: Implement the readiness helper**

```python
def is_advice_profile_ready(profile: InvestorProfile) -> bool:
    has_risk_measure = (
        profile.acceptable_loss_percent is not None
        or profile.risk_tolerance is not None
    )
    return (
        profile.objective is not None
        and profile.time_horizon_months is not None
        and has_risk_measure
    )
```

- [ ] **Step 4: Run profile tests**

Run: `.venv/bin/python -m pytest tests/unit/test_profile.py -q`

Expected: all profile tests pass.

### Task 2: Tell the LLM when it can advise without more questions

**Files:**
- Modify: `app/agent/tool_loop.py:84-99`
- Modify: `app/agent/prompts.py:90-105`
- Test: `tests/unit/test_tool_loop.py`

- [ ] **Step 1: Add failing input and instruction assertions**

```python
assert "Advice profile readiness:\nREADY" in build_tool_loop_input(
    "Give me advice",
    PortfolioPolicy(),
    InvestorProfile(
        objective=InvestmentObjective.GROWTH,
        time_horizon_months=12,
        acceptable_loss_percent=Decimal("20"),
    ),
)
assert "2 to 4" in instructions
assert "Do not ask for optional profile fields" in instructions
```

- [ ] **Step 2: Run tests and observe failure**

Run: `.venv/bin/python -m pytest tests/unit/test_tool_loop.py -q`

Expected: assertions fail because readiness and flexible-choice instructions are absent.

- [ ] **Step 3: Add readiness to Agent input**

Import `is_advice_profile_ready`, calculate `READY` or `INCOMPLETE`, and add:

```python
"Advice profile readiness:\n"
f"{readiness}\n\n"
```

before the user message.

- [ ] **Step 4: Update advice instructions**

Require the LLM to avoid optional questions when readiness is `READY`, offer 2–4 distinct grounded choices, recommend one with a short rationale, and clearly state that choices are not executed trades.

- [ ] **Step 5: Run focused tests**

Run: `.venv/bin/python -m pytest tests/unit/test_profile.py tests/unit/test_tool_loop.py -q`

Expected: all focused tests pass.

### Task 3: Verify and commit

**Files:**
- Modify: `app/services/profile_service.py`
- Modify: `app/agent/tool_loop.py`
- Modify: `app/agent/prompts.py`
- Modify: `tests/unit/test_profile.py`
- Modify: `tests/unit/test_tool_loop.py`

- [ ] **Step 1: Run the full test suite**

Run: `.venv/bin/python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Run static and UI validation**

Run: `.venv/bin/python -m compileall -q app main.py`, `node --test tests/test_ui.js`, and `git diff --check`.

Expected: all commands exit successfully.

- [ ] **Step 3: Run the two-turn advice workflow**

First request portfolio advice, then submit growth, 12 months, and 20% acceptable loss in the same session.

Expected: Agent analyzes immediately and presents multiple choices without another profile question.

- [ ] **Step 4: Commit**

```text
git add app/services/profile_service.py app/agent/tool_loop.py app/agent/prompts.py tests/unit/test_profile.py tests/unit/test_tool_loop.py
git commit -m "feat: make portfolio advice more flexible"
```
