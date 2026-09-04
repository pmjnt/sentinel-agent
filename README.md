# Sentinel Agent

Sentinel is a minimal Python AI Agent that analyzes the risk of a mocked crypto portfolio. It is intentionally small so the boundary between the LLM and its tools is easy to see.

This is Phase 1 only: there is no Binance connection, real trading, FastAPI, frontend, database, Docker, LangChain, LangGraph, or CrewAI.

## What is an AI Agent?

A normal chatbot receives text and returns text. An AI Agent can also choose and call tools while working toward the user's goal.

In Sentinel, the user asks a risk question. The LLM decides whether it needs portfolio holdings, market data, or both. The OpenAI Agents SDK runs the selected Python tool, sends its structured result back to the LLM, and lets the LLM continue its analysis.

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
│   ├── agent.py
│   ├── config.py
│   ├── models.py
│   └── tools/
│       ├── __init__.py
│       ├── market.py
│       └── portfolio.py
├── tests/
│   ├── test_config.py
│   ├── test_market.py
│   └── test_portfolio.py
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.12
- An OpenAI API key

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

## Configure the API key

Copy the example file:

```bash
cp .env.example .env
```

Then edit `.env`:

```dotenv
OPENAI_API_KEY=your_real_api_key_here
```

Never commit `.env`. It is listed in `.gitignore`.

## Run Sentinel

```bash
python main.py
```

At the prompt, try:

```text
Sentinel > Analyze my BTC exposure and tell me whether it currently looks risky.
```

Type `exit` to close the application.

## Run tests

```bash
python -m pytest -v
```

The tests call only the plain mock-data functions and configuration loader. They do not call the OpenAI API and do not need a real API key.

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
