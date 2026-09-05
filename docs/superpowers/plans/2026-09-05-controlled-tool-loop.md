# Controlled Tool-Calling Agent Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the main structured-output request router with a controlled Agent loop in which the LLM reads trusted portfolio/market observations through tools, invokes deterministic risk evaluation, and explains the result.

**Architecture:** A per-run `SentinelRunContext` owns trusted observations, a staged working policy, ordered events, and completed analyses. Agent tools operate only on that context; no tool can execute a financial action. `SentinelApplication` commits staged policy patches only after a successful Agent run and renders authoritative Python output before the Agent's qualitative interpretation.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, LiteLLM, Pydantic, pytest.

---

### Task 1: Finish explicit provider-aware model settings

**Files:**
- Create: `app/agent/model_settings.py`
- Create: `tests/unit/test_model_settings.py`
- Modify: `app/config.py`
- Modify: `app/agent/request_interpreter.py`
- Modify: `app/agent/analysis_reporter.py`
- Modify: `app/agent/sentinel.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_agent.py`
- Modify: `tests/unit/test_request_interpreter.py`
- Modify: `tests/unit/test_analysis_reporter.py`
- Modify: `.env.example`
- Modify: `README.md`

- [x] **Step 1: Retain the existing RED/GREEN tests and implementation**

Keep the current working-tree changes that add `Settings.llm_max_tokens`, parse
`LLM_MAX_TOKENS`, and build SDK `ModelSettings` centrally. The builder must
produce:

```python
ModelSettings(max_tokens=4096, reasoning=Reasoning(effort="none"))
```

for OpenAI GPT-5, and omit `reasoning` for Gemini.

- [x] **Step 2: Add sequential tool-call configuration**

Extend `build_agent_model_settings()` with:

```python
parallel_tool_calls=False
```

and assert it in `tests/unit/test_model_settings.py` so policy and observation
ordering cannot be made concurrent by provider defaults.

- [x] **Step 3: Verify model configuration**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_model_settings.py tests/test_config.py tests/test_agent.py tests/unit/test_request_interpreter.py tests/unit/test_analysis_reporter.py -q
```

Expected: all model-setting tests pass.

### Task 2: Evaluate trusted observations without fetching them again

**Files:**
- Modify: `app/services/portfolio_analysis_service.py`
- Modify: `tests/unit/test_portfolio_analysis_service.py`

- [x] **Step 1: Write failing pure-evaluation tests**

Add tests for public functions:

```python
required_market_symbols(portfolio, policy, focus_symbols)
evaluate_portfolio_observations(policy, portfolio, market_by_symbol)
```

Assert that the SRD portfolio requires `BTCUSDT`, missing BTC market data is
rejected, and verified HIGH-volatility data returns a BLOCKED
`PortfolioAnalysis` without gateway access.

- [x] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_portfolio_analysis_service.py -q
```

Expected: imports fail because the public observation functions do not exist.

- [x] **Step 3: Extract deterministic observation evaluation**

Refactor `PortfolioAnalysisService.analyze()` to fetch through its gateway and
then delegate to the two public functions. `evaluate_portfolio_observations()`
must call only existing deterministic functions:

```text
find_policy_violations
build_rebalance_plan
evaluate_rebalance_risk
```

It must never accept LLM-calculated allocations, violations, plan status, or
risk status.

- [x] **Step 4: Verify GREEN**

Run the portfolio-analysis tests again and expect all to pass.

### Task 3: Add controlled tools and per-run context

**Files:**
- Create: `app/agent/run_context.py`
- Create: `app/agent/controlled_tools.py`
- Create: `tests/unit/test_controlled_tools.py`
- Modify: `app/models/policy.py`

- [x] **Step 1: Write failing context/tool tests**

Cover these behaviors with fake gateways:

- `read_portfolio()` stores the exact gateway `Portfolio` in context.
- `read_market_data()` stores only a successful `MarketData` by normalized symbol.
- `stage_policy_update()` applies a validated `PolicyPatch` to `working_policy`
  and records it without touching the session store.
- `evaluate_cached_portfolio()` requests `get_portfolio` when absent.
- It lists missing market symbols when required observations are absent.
- It stores and returns `PortfolioAnalysis` after all observations exist.

- [x] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_controlled_tools.py -q
```

Expected: imports fail because the run context and controlled tools do not exist.

- [x] **Step 3: Implement the run context**

Define a mutable dataclass containing:

```text
gateway
starting_policy
working_policy
policy_patches
ordered_events
portfolio
market_by_symbol
data_errors
analyses
```

No API key or Binance secret may be placed in this context or returned to the
LLM.

- [x] **Step 4: Implement pure handlers and SDK wrappers**

Expose five `FunctionTool` objects named exactly:

```text
get_portfolio
get_market_data
update_policy
view_policy
evaluate_portfolio_risk
```

`update_policy` accepts `changes: list[PolicyChange]`, where every change has a
known policy field and a string/boolean/null value. Null explicitly removes a
rule. Duplicate fields are rejected. The SDK wrappers delegate to independently
testable handler functions.

`evaluate_portfolio_risk` reads portfolio and market objects only from context.
When observations are missing it returns a structured requirement result rather
than guessing.

- [x] **Step 5: Verify GREEN and tool allowlist**

Assert the exact five public tool names and assert that none contains `order`,
`trade`, `transfer`, `withdraw`, generic CLI, or execution capabilities.

### Task 4: Run the LLM inside the observation loop

**Files:**
- Create: `app/agent/tool_loop.py`
- Create: `tests/unit/test_tool_loop.py`
- Modify: `app/agent/prompts.py`

- [x] **Step 1: Write failing Agent-loop tests**

Using an injected fake `Runner.run`, assert:

- the Agent has the exact controlled-tool allowlist and no `output_type`;
- the current validated policy is present in the input;
- `SentinelRunContext` is passed to the Runner;
- general chat returns text with no events or staged patches;
- a provider exception returns no result and leaves the external store untouched;
- non-text final output is rejected;
- analysis interpretation using reserved execution/formal-risk language is
  rejected while the stored deterministic analysis remains available.

- [x] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_tool_loop.py -q
```

Expected: imports fail because the tool-loop service does not exist.

- [x] **Step 3: Implement the Agent and instructions**

Create one text-output Agent with the five tools and explicit model settings.
Instructions must enforce this sequence for risk requests:

```text
get_portfolio
→ inspect returned holdings
→ get_market_data for relevant non-stablecoin symbols
→ evaluate_portfolio_risk
→ explain only the returned validated result
```

The prompt must also require `update_policy` before analysis when the same user
message changes a rule, forbid invented observations, and forbid any execution
claim or unsupported financial guarantee.

- [x] **Step 4: Implement the loop service**

Run the Agent with a fresh `SentinelRunContext` and `max_turns` sufficient for
portfolio, market, evaluation, and final response. Return an immutable result
containing final text, ordered events, staged patches, final policy, analyses,
and data errors. Do not commit session state in this layer.

- [x] **Step 5: Verify GREEN**

Run the tool-loop unit tests and expect all to pass without external calls.

### Task 5: Make the controlled loop the main runtime

**Files:**
- Modify: `app/application.py`
- Modify: `main.py`
- Modify: `app/sessions.py`
- Modify: `tests/unit/test_application.py`
- Modify: `tests/unit/test_policy_analysis_workflow.py`
- Modify: `tests/test_agent.py`

- [x] **Step 1: Write failing application tests**

Test that:

- staged patches commit only after a successful loop result;
- events render in tool-call order;
- authoritative analysis facts and `Execution: NOT_EXECUTED` are rendered by
  Python before `AI interpretation`;
- general chat uses the Agent's text directly;
- missing portfolio/market observations produce the existing safe data message;
- a failed Agent run leaves policy unchanged.

- [x] **Step 2: Verify RED**

Run application and SRD workflow tests. Expected: constructor/result mismatches
until the new loop is integrated.

- [x] **Step 3: Add atomic policy commit support**

Add an explicit store method that applies an ordered tuple of validated patches.
Call it only after the tool-loop run succeeds. Do not expose the store or commit
method as an Agent tool.

- [x] **Step 4: Refactor SentinelApplication composition**

Replace the main runtime's structured-output Interpreter and separate Reporter
with the controlled tool loop. Render policy and analysis events through the
existing deterministic response-formatting services. Append the validated Agent
interpretation only after authoritative output.

- [x] **Step 5: Verify GREEN**

Run application, SRD workflow, and composition tests. Assert `main.py` constructs
the controlled loop and no longer constructs `AgentRequestInterpreter` or
`AgentAnalysisReporter` for runtime use.

### Task 6: Documentation, full validation, and real smoke test

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/agent-guidelines.md`
- Modify: `docs/sentinel-project-guide.html`
- Modify: `docs/superpowers/plans/2026-09-05-agent-model-settings.md`

- [ ] **Step 1: Update active documentation**

Describe the actual five-tool loop, staged policy updates, deterministic
evaluation boundary, qualitative LLM judgment, and absence of execution tools.
Mark the previous structured-output Interpreter/Reporter path as legacy rather
than the active runtime.

- [ ] **Step 2: Run full offline verification**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: all commands pass without network calls.

- [ ] **Step 3: Run one isolated real OpenAI smoke test**

With debug disabled, send `xin chào` and verify no tool call is made. Then send
the sample BTC-risk request and verify the visible loop calls portfolio before
market data and evaluation. Use Binance Demo only; never enable an execution
capability.

- [ ] **Step 4: Final safety inspection**

Search active Agent tool names and runtime imports. Confirm there is no order,
transfer, withdrawal, arbitrary CLI, or direct credential exposure reachable by
the Agent.
