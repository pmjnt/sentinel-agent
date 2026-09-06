# Chat-First Agent Pulse UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current dashboard with a soft Binance-inspired chat UI, compact expandable Agent Pulse, and a backend-validated model selector that preserves session state when switching routes.

**Architecture:** Add a small backend `ModelCatalog` that owns the model allowlist and produces route-specific Settings. Keep one `SentinelToolLoop` and one shared `ConversationSessionStore`, but cache an Agents SDK Agent per validated route. Extend the SSE request/final response with the selected route, then rebuild the vanilla UI around per-turn chat components so activity never leaks into another turn.

**Tech Stack:** Python 3.12, OpenAI Agents SDK, LiteLLM, Pydantic, FastAPI, SSE, vanilla HTML/CSS/JavaScript, pytest, Node test runner

---

## File map

- Create `app/model_catalog.py`: parse, filter and validate safe model routes.
- Create `tests/unit/test_model_catalog.py`: catalog/key/allowlist tests.
- Modify `app/config.py`: load `LLM_ALLOWED_MODELS`.
- Modify `.env.example`: show the explicit route allowlist.
- Modify `app/agent/tool_loop.py`: cache an Agent per validated route while sharing conversation memory.
- Modify `app/application.py`: accept and pass a validated route to the Agent loop.
- Modify `app/bootstrap.py`: compose one catalog and one routed tool loop.
- Modify `app/models/api.py`: route fields in request/catalog/completed DTOs.
- Modify `app/api.py`: `/api/models` and pre-stream route validation.
- Replace `web/index.html`: chat-first semantic shell.
- Replace `web/styles.css`: aligned soft graphite/yellow design system.
- Replace `web/app.js`: model popover, per-turn SSE, Agent Pulse and evidence rendering.
- Modify Python/Node tests and project documentation.

### Task 1: Parse the configured model allowlist

**Files:**
- Modify: `app/config.py`
- Modify: `.env.example`
- Modify: `tests/test_config.py`

- [x] **Step 1: Write failing config tests**

Add `LLM_ALLOWED_MODELS` to `_clear_llm_environment`, then add:

```python
def test_load_settings_parses_model_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv(
        "LLM_ALLOWED_MODELS",
        "gemini/gemini-3.5-flash-lite, openai/gpt-5.4-mini",
    )

    assert config.load_settings().llm_allowed_models == (
        "gemini/gemini-3.5-flash-lite",
        "openai/gpt-5.4-mini",
    )


def test_default_model_is_allowed_when_allowlist_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert config.load_settings().llm_allowed_models == (
        "openai/gpt-5.4-mini",
    )
```

- [x] **Step 2: Run the tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_config.py -q
```

Expected: FAIL because `Settings.llm_allowed_models` does not exist.

- [x] **Step 3: Implement minimal parsing**

Add to `Settings`:

```python
llm_allowed_models: tuple[str, ...] = ()
```

In `load_settings`, derive a non-empty default and remove duplicates without
changing order:

```python
default_route = f"{provider.value}/{model}"
configured_routes = os.getenv("LLM_ALLOWED_MODELS", default_route).split(",")
allowed_models = tuple(
    dict.fromkeys(route.strip() for route in configured_routes if route.strip())
)
if default_route not in allowed_models:
    raise ValueError("The configured default model must be in LLM_ALLOWED_MODELS.")
```

Pass `llm_allowed_models=allowed_models` to `Settings(...)`.

Add to `.env.example`:

```dotenv
# Backend allowlist exposed to the UI; no live provider model fetch.
LLM_ALLOWED_MODELS=gemini/gemini-3.5-flash-lite,openai/gpt-5.4-mini
```

- [x] **Step 4: Run config tests and verify GREEN**

```bash
.venv/bin/python -m pytest tests/test_config.py -q
```

Expected: all config tests PASS.

- [x] **Step 5: Commit**

```bash
git add app/config.py .env.example tests/test_config.py
git commit -m "feat: configure allowed LLM routes"
```

### Task 2: Add the safe model catalog

**Files:**
- Create: `app/model_catalog.py`
- Create: `tests/unit/test_model_catalog.py`

- [x] **Step 1: Write failing catalog tests**

```python
import pytest

from app.config import LLMProvider, Settings
from app.model_catalog import ModelCatalog


def _settings() -> Settings:
    return Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        llm_allowed_models=(
            "gemini/gemini-3.5-flash-lite",
            "openai/gpt-5.4-mini",
        ),
        gemini_api_key="gemini-key",
    )


def test_catalog_exposes_only_routes_whose_provider_key_exists() -> None:
    catalog = ModelCatalog.from_settings(_settings())

    assert [route.key for route in catalog.routes] == [
        "gemini/gemini-3.5-flash-lite"
    ]


def test_catalog_resolves_enabled_route_and_builds_agent_settings() -> None:
    catalog = ModelCatalog.from_settings(_settings())

    route = catalog.resolve("gemini", "gemini-3.5-flash-lite")
    routed_settings = route.apply(_settings())

    assert routed_settings.agents_model == (
        "litellm/gemini/gemini-3.5-flash-lite"
    )


def test_catalog_rejects_unlisted_route() -> None:
    with pytest.raises(ValueError, match="not enabled"):
        ModelCatalog.from_settings(_settings()).resolve(
            "openai", "gpt-5.4-mini"
        )
```

- [x] **Step 2: Run the test and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_model_catalog.py -q
```

Expected: collection FAIL because `app.model_catalog` does not exist.

- [x] **Step 3: Implement `ModelRoute` and `ModelCatalog`**

```python
from dataclasses import dataclass

from app.config import LLMProvider, Settings


@dataclass(frozen=True)
class ModelRoute:
    provider: LLMProvider
    model: str

    @property
    def key(self) -> str:
        return f"{self.provider.value}/{self.model}"

    def apply(self, settings: Settings) -> Settings:
        return settings.model_copy(
            update={"llm_provider": self.provider, "llm_model": self.model}
        )


class ModelCatalog:
    def __init__(self, routes: tuple[ModelRoute, ...], default: ModelRoute) -> None:
        self.routes = routes
        self.default = default
        self._by_key = {route.key: route for route in routes}

    @classmethod
    def from_settings(cls, settings: Settings) -> "ModelCatalog":
        routes = []
        for value in settings.llm_allowed_models or (settings.agents_model.removeprefix("litellm/"),):
            provider_text, separator, model = value.partition("/")
            if not separator or not model:
                raise ValueError(f"Invalid allowed model route: {value}.")
            provider = LLMProvider(provider_text)
            key_exists = {
                LLMProvider.OPENAI: settings.openai_api_key,
                LLMProvider.GEMINI: settings.gemini_api_key,
            }[provider]
            if key_exists:
                routes.append(ModelRoute(provider, model))
        default_key = f"{settings.llm_provider.value}/{settings.llm_model}"
        by_key = {route.key: route for route in routes}
        if default_key not in by_key:
            raise ValueError("The default model route is not enabled.")
        return cls(tuple(routes), by_key[default_key])

    def resolve(self, provider: str, model: str) -> ModelRoute:
        key = f"{provider.strip().lower()}/{model.strip()}"
        try:
            return self._by_key[key]
        except KeyError as error:
            raise ValueError("The selected model route is not enabled.") from error
```

- [x] **Step 4: Run catalog tests and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_model_catalog.py -q
```

Expected: all catalog tests PASS.

- [x] **Step 5: Commit**

```bash
git add app/model_catalog.py tests/unit/test_model_catalog.py
git commit -m "feat: add safe model catalog"
```

### Task 3: Route the Agent while sharing conversation memory

**Files:**
- Modify: `app/agent/tool_loop.py`
- Modify: `app/application.py`
- Modify: `app/bootstrap.py`
- Modify: `tests/unit/test_tool_loop.py`
- Modify: `tests/unit/test_tool_loop_application.py`
- Modify: `tests/test_agent.py`

- [x] **Step 1: Write failing routing and shared-session tests**

Add a fake `create_agent` callback to `SentinelToolLoop` and assert that two
routes create two Agents while both runs receive the same session object:

```python
def test_model_switch_uses_route_agent_and_same_conversation_session() -> None:
    created_models: list[str] = []
    seen_sessions: list[object] = []

    def fake_create_agent(settings: Settings):
        created_models.append(settings.agents_model)
        return SimpleNamespace(model=settings.agents_model)

    async def fake_run(agent, prompt, **kwargs):
        seen_sessions.append(kwargs["session"])
        return SimpleNamespace(final_output="Hello.")

    settings = _settings().model_copy(
        update={
            "llm_allowed_models": (
                "openai/gpt-5.4-mini",
                "gemini/gemini-3.5-flash-lite",
            ),
            "gemini_api_key": "gemini-key",
        }
    )
    catalog = ModelCatalog.from_settings(settings)
    loop = SentinelToolLoop(
        settings,
        FakeGateway(),
        catalog=catalog,
        create_agent=fake_create_agent,
        run_agent=fake_run,
    )

    async def run_both() -> None:
        await loop.run("hello", PortfolioPolicy(), "user-1", model_route=catalog.default)
        await loop.run(
            "hello again",
            PortfolioPolicy(),
            "user-1",
            model_route=catalog.resolve("gemini", "gemini-3.5-flash-lite"),
        )

    asyncio.run(run_both())

    assert len({id(session) for session in seen_sessions}) == 1
    assert created_models == [
        "litellm/openai/gpt-5.4-mini",
        "litellm/gemini/gemini-3.5-flash-lite",
    ]
```

Add an application test asserting the route reaches the fake loop. Route fields
are added to the public structured response in Task 4 so this task remains
focused on runtime routing.

- [x] **Step 2: Run focused tests and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_tool_loop.py tests/unit/test_tool_loop_application.py tests/test_agent.py -q
```

Expected: FAIL because the loop/application do not accept `model_route`.

- [x] **Step 3: Implement route-aware Agent caching**

In `SentinelToolLoop.__init__`, accept `catalog` and `create_agent`, retain one
shared `ConversationSessionStore`, and add:

```python
self._catalog = catalog or ModelCatalog.from_settings(settings)
self._create_agent = create_agent or create_tool_loop_agent
self._agents: dict[str, Agent[SentinelRunContext]] = {}

def _agent_for(self, route: ModelRoute | None):
    selected = route or self._catalog.default
    if selected.key not in self._agents:
        self._agents[selected.key] = self._create_agent(selected.apply(self._settings))
    return self._agents[selected.key]
```

Both `run` and `stream` gain `model_route: ModelRoute | None = None` and pass
`self._agent_for(model_route)` to the SDK runner. Do not create a separate
conversation store per route.

Update `SentinelApplication.handle/stream_handle` to accept the optional route,
pass it to the loop, and place the selected route on the final structured DTO.

Update `create_application(settings, gateway, catalog=None)` to create one
catalog and pass it to `SentinelToolLoop`.

- [x] **Step 4: Run focused tests and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_tool_loop.py tests/unit/test_tool_loop_application.py tests/test_agent.py -q
```

Expected: focused tests PASS; existing console behavior still uses the default.

- [x] **Step 5: Commit**

```bash
git add app/agent/tool_loop.py app/application.py app/bootstrap.py tests/unit/test_tool_loop.py tests/unit/test_tool_loop_application.py tests/test_agent.py
git commit -m "feat: route Sentinel across allowed models"
```

### Task 4: Extend the safe API contract

**Files:**
- Modify: `app/models/api.py`
- Modify: `app/api.py`
- Modify: `app/application.py`
- Modify: `tests/unit/test_api_models.py`
- Modify: `tests/unit/test_api.py`
- Modify: `tests/unit/test_tool_loop_application.py`

- [x] **Step 1: Write failing API tests**

Update requests to include `provider` and `model`, then add:

```python
def test_models_endpoint_returns_enabled_routes_without_keys() -> None:
    client = TestClient(create_api(FakeStreamingApplication(), _settings()))

    response = client.get("/api/models")

    assert response.status_code == 200
    assert response.json()["default"] == {
        "provider": "openai",
        "model": "gpt-5.4-mini",
    }
    assert "test-key" not in response.text


def test_chat_rejects_route_outside_allowlist_before_streaming() -> None:
    client = TestClient(create_api(FakeStreamingApplication(), _settings()))

    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": "user-1",
            "message": "Analyze.",
            "provider": "gemini",
            "model": "unknown",
        },
    )

    assert response.status_code == 422
```

- [x] **Step 2: Run API tests and verify RED**

```bash
.venv/bin/python -m pytest tests/unit/test_api.py tests/unit/test_api_models.py -q
```

Expected: FAIL because route fields and `/api/models` do not exist.

- [x] **Step 3: Add typed DTOs and endpoint validation**

Add to `app/models/api.py`:

```python
class ModelOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    provider: str
    model: str


class ModelCatalogResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    default: ModelOption
    models: list[ModelOption]
```

Add bounded `provider` and `model` fields to `ChatStreamRequest`, and add
`provider/model` to `StructuredSentinelResponse`.

Update `SentinelApplication.stream_handle` to populate those fields from the
validated route, and update all structured-response test fixtures with explicit
route values.

In `create_api`, construct or accept one `ModelCatalog`. Add `/api/models`.
Resolve the route before returning `StreamingResponse`; translate `ValueError`
to `HTTPException(status_code=422, detail="Selected model is not enabled.")`.
Pass the resolved route into `application.stream_handle`.

- [x] **Step 4: Run API tests and verify GREEN**

```bash
.venv/bin/python -m pytest tests/unit/test_api.py tests/unit/test_api_models.py -q
```

Expected: all API tests PASS and response bodies contain no configured key.

- [x] **Step 5: Commit**

```bash
git add app/models/api.py app/api.py tests/unit/test_api.py tests/unit/test_api_models.py
git commit -m "feat: expose validated model routes"
```

### Task 5: Replace the page with the chat-first shell

**Files:**
- Modify: `web/index.html`
- Modify: `web/styles.css`
- Modify: `tests/test_ui.js`

- [x] **Step 1: Replace the static UI contract test**

Assert the new semantic structure and removal of dashboard panels:

```javascript
test("page uses the chat-first Agent Pulse shell", () => {
  const html = readFileSync(join(__dirname, "../web/index.html"), "utf8");
  assert.match(html, /id="model-trigger"/);
  assert.match(html, /id="model-menu"/);
  assert.match(html, /id="chat-thread"/);
  assert.match(html, /id="chat-composer"/);
  assert.doesNotMatch(html, /desk-grid|Analysis Request|Tool Evidence/);
});
```

- [x] **Step 2: Run Node tests and verify RED**

```bash
node --test tests/test_ui.js
```

Expected: FAIL because the old ledger/dashboard markup remains.

- [x] **Step 3: Implement the semantic HTML shell**

Replace the page body with:

```html
<main class="chat-shell">
  <header class="chat-header">
    <div class="content-grid">
      <a class="wordmark" href="/">Sentinel</a>
      <button id="model-trigger" class="model-trigger" aria-expanded="false" aria-controls="model-menu">
        <span id="active-model">Loading model…</span><span class="chevron" aria-hidden="true"></span>
      </button>
      <div id="model-menu" class="model-menu" hidden></div>
    </div>
  </header>
  <ol id="chat-thread" class="chat-thread content-grid" aria-label="Conversation"></ol>
  <form id="chat-composer" class="composer-wrap">
    <div class="composer content-grid">
      <textarea id="prompt" rows="1" maxlength="8000" placeholder="Ask Sentinel anything…"></textarea>
      <button id="send-button" type="submit" aria-label="Send message">↑</button>
    </div>
  </form>
</main>
<p id="live-status" class="sr-only" aria-live="polite"></p>
```

Implement the approved graphite/yellow variables, shared 680px content grid,
soft surfaces, responsive speaker column and reduced-motion rule in CSS. CSS
chevrons must use borders/transforms, not Unicode glyphs.

- [x] **Step 4: Run Node tests and verify GREEN**

```bash
node --test tests/test_ui.js
```

Expected: shell contract test PASS.

- [x] **Step 5: Commit**

```bash
git add web/index.html web/styles.css tests/test_ui.js
git commit -m "feat: add chat-first Sentinel shell"
```

### Task 6: Implement model selection and per-turn Agent Pulse

**Files:**
- Modify: `web/app.js`
- Modify: `tests/test_ui.js`

- [ ] **Step 1: Write failing JavaScript behavior tests**

Update request construction and add pure state tests:

```javascript
test("chat request includes the selected validated route", () => {
  assert.deepEqual(
    buildChatRequest("user-1", "Analyze.", {
      provider: "gemini",
      model: "gemini-3.5-flash-lite",
    }),
    {
      session_id: "user-1",
      message: "Analyze.",
      provider: "gemini",
      model: "gemini-3.5-flash-lite",
    },
  );
});

test("activity reducer updates only the current turn", () => {
  const first = reduceActivity([], {
    sequence: 1,
    kind: "PORTFOLIO_READ",
    status: "STARTED",
    message: "Started portfolio retrieval.",
  });
  const second = reduceActivity(first, {
    sequence: 2,
    kind: "PORTFOLIO_READ",
    status: "COMPLETED",
    message: "Completed portfolio retrieval.",
  });

  assert.equal(second.length, 1);
  assert.equal(second[0].status, "COMPLETED");
});
```

- [ ] **Step 2: Run Node tests and verify RED**

```bash
node --test tests/test_ui.js
```

Expected: FAIL because route-aware request/reducer are missing.

- [ ] **Step 3: Implement model popover and isolated turn views**

Implement/export these pure helpers:

```javascript
function buildChatRequest(sessionId, message, route) {
  return {
    session_id: sessionId.trim(),
    message: message.trim(),
    provider: route.provider,
    model: route.model,
  };
}

function reduceActivity(current, event) {
  const next = current.map((item) => ({ ...item }));
  if (event.status === "STARTED") return [...next, event];
  const index = next.findLastIndex((item) => item.kind === event.kind);
  if (index >= 0) next[index] = event;
  else next.push(event);
  return next;
}
```

On startup, fetch `/api/models`, choose its default, render only returned routes,
and never allow free-text model IDs. Clicking an option updates the route for
the next message without changing `session_id`.

For each submit, create a new assistant turn object containing its own response
node, pulse button, pulse detail and `activities` array. Bind that turn object
inside the SSE parser callback. `activity` updates the compact status and its
own list; `text_delta` updates its response; `completed` maps its structured
evidence; `error` marks only that turn failed and exposes Retry.

Use `aria-expanded`/`hidden` for Pulse and model menu. Escape all data by
assigning `textContent`; never build provider/tool content with `innerHTML`.

- [ ] **Step 4: Run Node tests and verify GREEN**

```bash
node --test tests/test_ui.js
```

Expected: all UI unit tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/app.js tests/test_ui.js
git commit -m "feat: stream Agent Pulse chat turns"
```

### Task 7: Documentation, full verification and visual QA

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/agent-guidelines.md`
- Modify: `docs/sentinel-project-guide.html`
- Modify: `tests/test_project_guide.py`

- [ ] **Step 1: Update documentation contracts**

Document:

```text
LLM_ALLOWED_MODELS is a backend allowlist, not a provider fetch.
GET /api/models returns enabled routes without secrets.
POST /api/chat/stream includes provider/model.
Changing model preserves session_id, conversation, policy and profile.
Agent Pulse exposes activity only, never chain-of-thought.
```

Replace screenshots/descriptions of the ledger dashboard with the chat-first
layout and update the file map for `app/model_catalog.py`.

- [ ] **Step 2: Run the complete automated verification**

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: zero failures and no whitespace errors. The existing third-party
Starlette/AnyIO deprecation warning may remain until the dependency resolves it.

- [ ] **Step 3: Run local HTTP smoke checks**

Start:

```bash
.venv/bin/uvicorn app.api:create_app --factory --host 127.0.0.1 --port 8765
```

Verify:

```bash
curl -sS http://127.0.0.1:8765/api/health
curl -sS http://127.0.0.1:8765/api/models
curl -I http://127.0.0.1:8765/
```

Expected: health and model JSON plus HTTP 200 for `/`; no API keys in model JSON.

- [ ] **Step 4: Perform visual and interaction QA**

At desktop and mobile widths verify:

```text
shared header/thread/composer edges
model text and CSS chevron alignment
model popover keyboard behavior
one-line collapsed Agent Pulse
compact expanded process
failed/completed states with text, not color alone
long Vietnamese wrapping
reduced-motion behavior
```

- [ ] **Step 5: Commit documentation and final adjustments**

```bash
git add README.md docs tests/test_project_guide.py web
git commit -m "docs: explain chat-first model routing"
```
