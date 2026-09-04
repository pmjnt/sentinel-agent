# Sentinel LiteLLM Provider Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Sentinel select OpenAI or Gemini and an explicit model through `.env`, routing both providers through LiteLLM.

**Architecture:** Extend the existing immutable `Settings` model with a provider enum, model name, provider keys, and a derived Agents SDK model ID. Pass Settings into the existing Agent factory and use the SDK's `litellm/` model prefix; portfolio and market tools remain unchanged.

**Tech Stack:** Python 3.12, OpenAI Agents SDK 0.22, LiteLLM integration, python-dotenv, Pydantic, pytest

---

### Task 1: Provider-aware configuration

**Files:**
- Modify: `app/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Replace configuration tests with provider-specific failing tests**

Add tests that set `LLM_PROVIDER`, `LLM_MODEL`, and only the active provider key. Assert OpenAI produces `litellm/openai/gpt-5.6-luna`, Gemini produces `litellm/gemini/gemini-3.8-flash`, invalid providers and empty models raise `ValueError`, and missing active keys name the required environment variable.

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: FAIL because the current Settings has no provider, model, or `agents_model`.

- [ ] **Step 3: Implement the minimum provider-aware Settings**

Add:

```python
class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)
    llm_provider: LLMProvider
    llm_model: str
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    @property
    def agents_model(self) -> str:
        return f"litellm/{self.llm_provider.value}/{self.llm_model}"
```

Update `load_settings()` to require provider and model, normalize provider, read both keys, and validate only the active provider key.

- [ ] **Step 4: Run configuration tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: all configuration tests pass without loading a real `.env`.

### Task 2: Configure Sentinel with LiteLLM

**Files:**
- Modify: `app/agent.py`
- Create: `tests/test_agent.py`
- Modify: `main.py`

- [ ] **Step 1: Write a failing Agent configuration test**

```python
def test_create_sentinel_agent_uses_configured_litellm_model() -> None:
    settings = Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.8-flash",
        gemini_api_key="test-gemini-key",
    )

    agent = create_sentinel_agent(settings)

    assert agent.model == "litellm/gemini/gemini-3.8-flash"
    assert [tool.name for tool in agent.tools] == ["get_portfolio", "get_market_data"]
```

- [ ] **Step 2: Run the Agent test and verify RED**

Run: `.venv/bin/python -m pytest tests/test_agent.py -v`
Expected: FAIL because `create_sentinel_agent` does not accept Settings.

- [ ] **Step 3: Pass Settings into the Agent and console**

Change the factory to `create_sentinel_agent(settings: Settings) -> Agent`, call `set_tracing_disabled(True)`, and set `model=settings.agents_model`. In `main.py`, assign `settings = load_settings()` and pass it into the factory.

- [ ] **Step 4: Run all tests and verify GREEN**

Run: `.venv/bin/python -m pytest -v`
Expected: all tests pass without API calls.

### Task 3: Install the supported LiteLLM integration

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Replace the base SDK requirement**

Use:

```text
openai-agents[litellm]
pydantic
python-dotenv
pytest
```

- [ ] **Step 2: Install and check dependencies**

Run: `.venv/bin/python -m pip install -r requirements.txt`
Expected: LiteLLM installs successfully.

Run: `.venv/bin/python -m pip check`
Expected: `No broken requirements found.`

- [ ] **Step 3: Validate model resolution without calling a provider**

Instantiate OpenAI and Gemini Settings and Agents locally; assert the model strings and tool names. Import `agents.extensions.models.litellm_model` to prove the optional integration is installed.

### Task 4: Environment example and documentation

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Document OpenAI and Gemini configuration**

Set the example default to OpenAI with `LLM_PROVIDER`, `LLM_MODEL`, both key variables, and an empty inactive Gemini key. Explain how to switch to Gemini, edit a model, use model IDs without LiteLLM prefixes, and require only the active provider key.

- [ ] **Step 2: Preserve the learning boundary**

Explain that OpenAI Agents SDK still owns the Agent/tool loop while LiteLLM routes model calls. State that fallback, proxy server, cost tracking, Binance and trading remain outside this change.

### Task 5: Final verification

**Files:**
- Review: all modified and created files

- [ ] **Step 1: Run fresh tests**

Run: `.venv/bin/python -m pytest -v`
Expected: all tests pass with no network/API request.

- [ ] **Step 2: Run syntax and dependency checks**

Run: `.venv/bin/python -m compileall -q app main.py tests`

Run: `.venv/bin/python -m pip check`

Expected: both exit 0.

- [ ] **Step 3: Smoke-test both console configurations without an LLM request**

Run the console once with OpenAI variables and EOF, then once with Gemini variables and EOF. Expected: both display the prompt and exit cleanly without contacting either provider.

- [ ] **Step 4: Inspect the final diff and working tree**

Run: `git diff --check` and `git status --short`.
Expected: only intentional LiteLLM provider-switching changes are present.

