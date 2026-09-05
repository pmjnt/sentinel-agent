# Policy Analysis Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect natural-language request interpretation, policy state, Binance Demo observations, deterministic analysis, RiskEngine, and LLM explanation into the console application.

**Architecture:** `SentinelApplication` coordinates the already validated `PolicyConversationService`, a new deterministic `PortfolioAnalysisService`, and a tool-free `AgentAnalysisReporter`. The Reporter receives the original question plus validated `PortfolioAnalysis`; Python separately renders authoritative facts and risk status.

**Tech Stack:** Python 3.12, OpenAI Agents SDK with LiteLLM, Pydantic, asyncio, pytest.

---

### Task 1: Deterministic portfolio analysis use case

**Files:**
- Create: `app/models/analysis.py`
- Create: `app/services/portfolio_analysis_service.py`
- Create: `tests/unit/test_portfolio_analysis_service.py`

- [x] **Step 1: Write failing service tests**

Define fake gateways and assert:

1. policy `max_asset_weight=0.40`, portfolio BTC 55%/ETH 25%/USDT 20%,
   and BTC HIGH market produce one $1,500 BTC SELL proposal and `BLOCKED`;
2. focus symbol `BTC` becomes one `BTCUSDT` market request even without a
   concentration rule;
3. duplicate focus/violation symbols result in one market request;
4. `USDT` focus does not create `USDTUSDT`;
5. `MarketDataError` raises sanitized `AnalysisDataError` and no analysis model
   is returned.

- [x] **Step 2: Run tests to verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_portfolio_analysis_service.py -q
```

Expected: collection fails because the analysis model/service do not exist.

- [x] **Step 3: Implement model and service**

Define immutable `PortfolioAnalysis` with:

```python
policy: PortfolioPolicy
portfolio: Portfolio
violations: list[PolicyViolation]
market_data: list[MarketData]
plan: RebalancePlan
risk_decision: RiskDecision
```

`PortfolioAnalysisService.analyze(policy, focus_symbols)` must retrieve portfolio,
derive unique market symbols, use `asyncio.gather`, reject every
`MarketDataError`, build the plan, evaluate risk, copy the risk status to matching
`PlanStatus`, and return the aggregate.

- [x] **Step 4: Run targeted tests to verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_portfolio_analysis_service.py -q
```

Expected: all service tests pass.

- [x] **Step 5: Commit**

```bash
git add app/models/analysis.py app/services/portfolio_analysis_service.py tests/unit/test_portfolio_analysis_service.py docs/superpowers/plans/2026-09-05-policy-analysis-orchestrator.md
git commit -m "feat: add deterministic portfolio analysis"
```

### Task 2: Tool-free analysis Reporter

**Files:**
- Create: `app/agent/analysis_reporter.py`
- Modify: `app/agent/prompts.py`
- Create: `tests/unit/test_analysis_reporter.py`

- [x] **Step 1: Write failing Reporter tests**

Assert that:

- `create_analysis_reporter_agent()` uses the configured LiteLLM route,
  has no tools, and returns text output;
- Reporter input contains the user question and serialized validated analysis;
- `AgentAnalysisReporter.report()` returns only `final_output` from an injected
  fake runner;
- an unexpected non-string final output raises `ModelBehaviorError`.

- [x] **Step 2: Run tests to verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_analysis_reporter.py -q
```

Expected: collection fails because `app.agent.analysis_reporter` does not exist.

- [x] **Step 3: Implement Reporter**

Add `ANALYSIS_REPORTER_INSTRUCTIONS` requiring factual tool data and AI
interpretation to be separated, Binance Demo labeling, concise language matching
the user, deterministic risk status preservation, and no trade-execution claim.
Build explicit input from `message` and `PortfolioAnalysis.model_dump_json()`.

- [x] **Step 4: Run targeted tests to verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_analysis_reporter.py -q
```

Expected: all Reporter tests pass.

- [x] **Step 5: Commit**

```bash
git add app/agent/analysis_reporter.py app/agent/prompts.py tests/unit/test_analysis_reporter.py docs/superpowers/plans/2026-09-05-policy-analysis-orchestrator.md
git commit -m "feat: explain validated Sentinel analysis"
```

### Task 3: Conversational application orchestrator

**Files:**
- Create: `app/application.py`
- Modify: `app/services/policy_conversation_service.py`
- Modify: `tests/unit/test_policy_conversation_service.py`
- Create: `tests/unit/test_application.py`

- [x] **Step 1: Change analyze-only conversation expectation to RED**

Update the conversation-service test so analyze-only produces an empty message
plus `analysis_requested=True`; policy messages continue producing deterministic
text. Run the test and confirm it fails on the obsolete acknowledgement.

- [x] **Step 2: Remove the placeholder acknowledgement**

Delete the `"Đã ghi nhận yêu cầu phân tích portfolio."` fallback from
`PolicyConversationService`, then rerun its tests and confirm GREEN.

- [x] **Step 3: Write failing application tests**

Use fake conversation, analysis, and Reporter collaborators to assert:

- update/view-only returns deterministic conversation text and calls neither
  analysis nor Reporter;
- clarification returns its question and calls neither downstream collaborator;
- analysis-only calls analysis with the interpreted policy/focus and returns
  Python-rendered facts plus Reporter interpretation;
- update-then-analyze joins policy update text and Reporter text in order;
- `AnalysisDataError` returns a safe message saying required Binance Demo data
  could not be verified, while retaining any preceding policy update text.

- [x] **Step 4: Run application tests to verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_application.py -q
```

Expected: collection fails because `app.application` does not exist.

- [x] **Step 5: Implement SentinelApplication**

Define collaborator protocols, immutable `SentinelResponse(message, policy,
analyses)`, and `handle(session_id, message)`. The application must not import
Binance CLI classes or perform arithmetic itself; presentation arithmetic belongs
in the deterministic response formatter.

- [x] **Step 6: Run targeted tests to verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_policy_conversation_service.py tests/unit/test_application.py -q
```

Expected: all tests pass.

- [x] **Step 7: Commit**

```bash
git add app/application.py app/services/policy_conversation_service.py tests/unit/test_policy_conversation_service.py tests/unit/test_application.py docs/superpowers/plans/2026-09-05-policy-analysis-orchestrator.md
git commit -m "feat: orchestrate policy analysis requests"
```

### Task 4: Wire console and update current documentation

**Files:**
- Modify: `main.py`
- Modify: `tests/test_agent.py`
- Modify: `tests/test_project_guide.py`
- Modify: `README.md`
- Modify: `docs/sentinel-project-guide.html`

- [x] **Step 1: Write failing composition test**

Extract `create_application(settings, gateway)` in `main.py`. Assert the returned
object is `SentinelApplication` without calling a real LLM or gateway during
construction.

- [x] **Step 2: Run composition test to verify RED**

```bash
.venv/bin/python -m pytest tests/test_agent.py -q
```

Expected: import fails because `create_application` is missing.

- [x] **Step 3: Wire runtime composition**

Construct one `AgentRequestInterpreter`, `InMemoryPolicySessionStore`,
`PolicyConversationService`, `PortfolioAnalysisService`, and
`AgentAnalysisReporter`. Replace direct `Runner.run(sentinel, user_input)` with
`application.handle("console-user", user_input)` and print its message.

- [x] **Step 4: Update documentation truth markers**

Update README and the HTML handbook so policy orchestration is labeled
`ĐÃ HOẠT ĐỘNG` for console use. Keep FastAPI, connected web UI, persistence,
approval, execution, production Binance, and MCP labeled inactive/future. Update
the guide contract test to require the new runtime chain and remove the obsolete
“not connected to main.py” assertion.

- [x] **Step 5: Run full verification**

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
rg -n 'from (agents|fastapi|mcp)|import (agents|fastapi|mcp)' app/models app/services
git diff --check
```

Expected: all tests pass; compile succeeds; dependency boundary and whitespace
checks have no output.

- [x] **Step 6: Commit**

```bash
git add main.py tests/test_agent.py tests/test_project_guide.py README.md docs/sentinel-project-guide.html docs/superpowers/plans/2026-09-05-policy-analysis-orchestrator.md
git commit -m "feat: run policy-driven Sentinel console"
```
