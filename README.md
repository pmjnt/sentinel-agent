# Sentinel Agent

Sentinel is a Python AI Agent for policy-driven crypto portfolio risk analysis. It is intentionally structured so the boundary between the LLM, deterministic Python rules, and external tools is easy to see.

The deterministic domain core now calculates portfolio allocations, detects policy violations, builds draft rebalance proposals, and evaluates risk without an LLM. A structured-output policy parser and in-memory policy conversation service are also implemented. Binance MCP OAuth and safe tool discovery are implemented; the production data adapter will be written only after its real schema is reviewed. There is no real trading, database, Docker, LangChain, LangGraph, or CrewAI.

## Development documentation

- [Architecture](docs/architecture.md)
- [Development guidelines](docs/development-guidelines.md)
- [Agent guidelines](docs/agent-guidelines.md)
- [Testing guidelines](docs/testing.md)
- [Binance MCP discovery and security](docs/binance-mcp.md)
- [Vietnamese SRD guide](docs/sentinel-srd-guide.html)

The core responsibility rule is:

```text
LLM understands and coordinates.
Python calculates and validates.
RiskEngine enforces safety rules.
Binance MCP supplies live read-only data in the target runtime.
```

## What is an AI Agent?

A normal chatbot receives text and returns text. An AI Agent can also choose and call tools while working toward the user's goal.

In Sentinel, the user asks a risk question. The LLM decides whether it needs portfolio holdings, market data, or both. The OpenAI Agents SDK runs the selected Python tool, sends its structured result back to the LLM, and lets the LLM continue its analysis.

Sentinel uses LiteLLM as a model-routing layer. OpenAI Agents SDK still owns the Agent and tool loop; LiteLLM only routes the model request to OpenAI or Gemini.

```text
Sentinel Agent -> LiteLLM -> OpenAI or Gemini
```

## The LLM and the tools

The **LLM is the AI brain**. It lives behind the `Agent` configured in `app/agent.py`. It understands the user's request, reads Sentinel's instructions, decides which tools are relevant, and explains the risk.

The **tools are ordinary Python capabilities exposed to the LLM**:

- `get_portfolio()` returns the user's mocked holdings and total value.
- `get_market_data(symbol)` returns mocked price, 24-hour change, and volatility.

Each tool starts as a plain Python function, which makes it easy to unit test. `function_tool(...)` creates a separate SDK wrapper that describes the function to the LLM. The Agent receives the wrappers, while tests call the plain functions directly.

```text
Plain Python function --function_tool(...)--> AI-callable tool
```

## Architecture

```text
User
  |
  v
Sentinel Agent / LLM
  |
  | chooses tools
  |
  +----> get_portfolio()
  |
  +----> get_market_data()
  |
  v
LLM analyzes tool results
  |
  v
Final response
```

## Sentinel's agent loop

For this request:

```text
Analyze my BTC exposure and tell me whether it currently looks risky.
```

the loop is expected to work like this:

1. The LLM sees that exposure depends on the user's holdings and calls `get_portfolio()`.
2. The tool returns BTC = $6,000, ETH = $2,500, USDT = $1,500, total = $10,000.
3. The LLM sees that "currently risky" also needs market context and calls `get_market_data("BTCUSDT")`.
4. The tool returns the mocked BTC price, 24-hour change, and volatility.
5. The LLM receives both tool results, separates facts from interpretation, and explains concentration and market risk.

There is no hard-coded Python `if` statement that forces this sequence. The LLM chooses tools from the user's request, the Agent instructions, each tool's description, and its argument schema. `Runner.run(...)` manages the tool-call loop.

## Project structure

```text
sentinel-agent/
├── app/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── policy_parser.py
│   │   ├── prompts.py
│   │   └── sentinel.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── market.py
│   │   ├── policy.py
│   │   ├── portfolio.py
│   │   ├── risk.py
│   │   └── trade.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── policy_service.py
│   │   ├── portfolio_service.py
│   │   ├── rebalance_service.py
│   │   ├── policy_conversation_service.py
│   │   ├── policy_response_service.py
│   │   └── risk_service.py
│   ├── sessions.py
│   └── tools/
│       ├── __init__.py
│       ├── market.py
│       └── portfolio.py
├── tests/
│   ├── unit/
│   ├── test_agent.py
│   ├── test_config.py
│   ├── test_market.py
│   ├── test_portfolio.py
│   └── test_ui.js
├── web/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.12
- An OpenAI or Gemini API key

Confirm your Python version:

```bash
python3.12 --version
```

## Create a virtual environment

From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

## Install dependencies

```bash
python -m pip install -r requirements.txt
```

`litellm==1.83.0` is pinned because it is compatible with the OpenAI Python 3.x dependency used by the installed Agents SDK. Upgrade the Agents SDK and LiteLLM together after checking their dependency ranges.

## Configure the LLM provider and model

Copy the example file:

```bash
cp .env.example .env
```

Then edit `.env`. The default example prioritizes Gemini's free tier:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite

OPENAI_API_KEY=
GEMINI_API_KEY=your_gemini_api_key_here
```

Other general-purpose Gemini models currently shown in the UI are:

```text
gemini-3.1-flash-lite
gemini-3.5-flash
gemini-3-flash-preview
```

Google lists these models as free of charge within free-tier quotas. Free tier does not mean unlimited use, availability can vary by region/account, and Google may change its model catalog or quotas. Check the [official Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) before relying on a model.

To use OpenAI instead:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna

OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=
```

`LLM_MODEL` is editable. Enter only the provider's model ID; Sentinel adds the LiteLLM routing prefix itself. For example, enter `gpt-5.6-luna`, not `litellm/openai/gpt-5.6-luna`.

Only the API key for the selected provider is required. The provider validates whether the configured model exists and whether your key can access it when the first request is made.

Never commit `.env`. It is listed in `.gitignore`. OpenAI tracing is disabled in this MVP so a Gemini configuration does not also require an OpenAI key.

## Run Sentinel

```bash
python main.py
```

At the prompt, try:

```text
Sentinel > Analyze my BTC exposure and tell me whether it currently looks risky.
```

Type `exit` to close the application.

## Discover the real Binance MCP schema

Binance requires a public HTTPS OAuth Client ID Metadata Document. Configure its URL
first:

```dotenv
BINANCE_MCP_CLIENT_METADATA_URL=https://your-domain.example/oauth/client-metadata.json
```

The discovery command then opens Binance OAuth and calls only MCP `list_tools()`:

```bash
python -m app.mcp.discover
```

Select read-only Market Data/Account access when available; do not grant Trade or
Transfer permissions. OAuth state is held only in memory. See the
[Binance MCP guide](docs/binance-mcp.md) before running it.

## Preview the vintage web interface

The `web/` directory is a plain HTML/CSS/JavaScript prototype. It shows provider/model selection, the decisions Sentinel would make, tool inputs and outputs, and a report that separates factual tool data from AI interpretation.

Start a local static server from the project root:

```bash
python -m http.server 8000 -d web
```

Then open [http://localhost:8000](http://localhost:8000).

The progress and result shown in this interface are deliberately **simulated with mocked data**. Changing the provider or model demonstrates the future configuration flow; it does not send a request to OpenAI or Gemini from the browser.

### What happens when a model is selected?

In the current static UI, the selection only updates a route preview such as:

```text
litellm/gemini/gemini-3.5-flash-lite
```

The working console app uses the same idea through `.env`:

```text
LLM_PROVIDER + LLM_MODEL
          |
          v
Settings.agents_model
          |
          v
Agent(model="litellm/gemini/gemini-3.5-flash-lite")
          |
          v
LiteLLM reads GEMINI_API_KEY and calls Gemini
```

`Runner.run(...)` then sends the user's prompt to that model. When the model chooses a Sentinel tool, the Agents SDK executes it and returns its structured result to the same model. A later backend will receive the UI selection, validate it against an allow-list, and construct `Settings`; the browser must never receive or store the API key.

When a backend is added later, a FastAPI SSE or WebSocket endpoint can replace the JavaScript timers. The existing event renderer can remain and render real Agent/tool events as they arrive.

## Run tests

```bash
python -m pytest -v
node --test tests/test_ui.js
```

The tests cover the plain mock-data functions, provider configuration, Agent construction, and the static UI's pure domain logic. They do not call OpenAI or Gemini and do not need a real API key.

## What LiteLLM does

Sentinel passes model IDs such as these to OpenAI Agents SDK:

```text
litellm/openai/gpt-5.6-luna
litellm/gemini/gemini-3.5-flash-lite
```

The SDK delegates those model requests to LiteLLM. LiteLLM selects the provider and reads its standard API-key environment variable. It does not decide when to call portfolio or market tools; that remains the responsibility of the Sentinel Agent and its LLM.

This MVP does not use the LiteLLM Proxy Server, automatic fallback, load balancing, cost tracking, or multi-provider retries.

For a basic syntax check:

```bash
python -m compileall app main.py tests
```

## What changes when Binance MCP is added?

Phase 1 currently has this data path:

```text
LLM -> local tool -> hard-coded mock data
```

A later Binance MCP phase will use a path such as:

```text
LLM -> MCP tool -> Binance -> real data
```

The mock implementations in `app/tools/portfolio.py` and `app/tools/market.py` are the main code that will be replaced or adapted. The Pydantic models, Sentinel instructions, console loop, and the overall Agent/tool loop can mostly remain.

Adding Binance MCP or trading is deliberately outside this phase.
