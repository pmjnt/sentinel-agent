# Sentinel

**A policy-driven AI portfolio agent for safer crypto decision workflows.**

Sentinel lets a user describe portfolio goals and safety rules in natural
language. The Agent reads Binance Demo portfolio and market data, detects policy
violations, researches liquid Spot markets, explains its judgment, and can
prepare a tightly controlled Demo trade plan.

The LLM never receives unrestricted trading or shell access. Financial
calculations, policy checks, approval rules, and execution guards remain in
deterministic Python.

> Built as a Binance Agent OS Mini Hackathon Track A project using the official
> Binance Skills Hub `binance-cli` integration.

## Why this is an AI Agent

A normal chatbot generates a response in one step. Sentinel runs a controlled
loop:

```text
User intent
    ↓
LLM chooses the next allowed tool
    ↓
Python validates the request and runs the tool
    ↓
Verified result returns to the LLM
    ↓
LLM chooses another tool or produces a grounded judgment
```

The LLM provides language understanding, adaptive tool selection, qualitative
comparison, and user-facing judgment. Python remains authoritative for numbers,
business rules, formal risk status, approval, and execution.

## Current capabilities

- Conversational portfolio-risk analysis from Binance Demo holdings.
- Natural-language portfolio policy updates and policy review.
- Process-local investor preferences such as objective, horizon, acceptable
  loss, risk tolerance, liquidity need, and excluded assets.
- Deterministic allocation calculations and policy-violation detection.
- Deterministic rebalance proposals and Risk Engine decisions.
- Adaptive Binance Spot USDT research using quote volume and kline history.
- Deterministic return, trend, realized volatility, maximum drawdown, and volume
  change calculations.
- Evidence-grounded recommendations with a clear Sentinel preference.
- OpenAI and Gemini model routing through LiteLLM with a backend allowlist.
- Console chat and a chat-first web UI.
- Server-Sent Events for live, collapsible Agent activity.
- Structured verified facts separated from LLM interpretation.
- Immutable Binance Demo trade proposals with a dedicated approval action.
- Optional, tightly bounded Binance Demo Spot execution and post-order
  verification.

For the complete current-state reference, read
[Current Capabilities (Vietnamese)](docs/current-capabilities.md).

## Architecture

```text
Browser / Console
       │
       v
Sentinel Agent (LLM + OpenAI Agents SDK)
       │ chooses from 12 controlled tools
       v
Application orchestration
       ├── Policy and investor-profile state
       ├── Portfolio analysis and rebalance services
       ├── Adaptive market-research service
       └── Deterministic Risk Engine
                    │
                    v
          Safe Binance CLI Gateway
                    │
                    v
             Binance Demo Trading
```

The Agent can use only these tool groups:

- Portfolio and market reads.
- Policy and investor-profile updates/views.
- Deterministic portfolio evaluation.
- Demo trade proposal creation.
- Bounded market-research planning, scanning, history analysis, and
  finalization.

There is no generic CLI, arbitrary URL, arbitrary code, transfer, withdrawal,
or direct order-execution tool available to the LLM.

## Safety model

```text
AI understands and recommends.
Python calculates and validates.
Risk Engine blocks unsafe plans.
The user explicitly approves.
The execution service revalidates.
Binance Demo executes and confirms.
```

Important hard limits:

- Binance Demo only; production Binance is rejected.
- Demo execution is disabled by default.
- MARKET BUY/SELL only.
- Every order requires a dedicated explicit approval action, separate from chat.
- Hard order value range: 10–100 USDT.
- Plans expire after five minutes.
- BTC, ETH, BNB, SOL, XRP, ADA, and DOGE USDT pairs use normal approval.
- Another valid Spot USDT token requires a separate plan-scoped token approval
  before order approval.
- Policy rules may make execution stricter, never weaker than hard limits.
- No response claims success until Binance returns and confirms `FILLED`.

A recommendation is not approval, and a trade proposal is not an executed
order.

## Requirements

- Python 3.12
- Official `binance-cli` 2.1.1
- A Binance Demo Trading API key
- An OpenAI API key, a Gemini API key, or both

## Quick start

### 1. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Install the official Binance CLI

Download and inspect the installer before running it:

```bash
curl --proto '=https' --tlsv1.2 -L \
  https://github.com/binance/binance-cli/releases/download/v2.1.1/binance-cli-installer.sh \
  -o /tmp/binance-cli-installer.sh
less /tmp/binance-cli-installer.sh
sh /tmp/binance-cli-installer.sh
binance-cli --version
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Gemini example:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
LLM_ALLOWED_MODELS=gemini/gemini-3.5-flash-lite,openai/gpt-5.4-mini
LLM_MAX_TOKENS=4096
GEMINI_API_KEY=your_gemini_api_key_here

BINANCE_API_ENV=demo
BINANCE_CLI_PATH=binance-cli
BINANCE_API_KEY=your_demo_api_key_here
BINANCE_SECRET_KEY=your_demo_secret_key_here
SENTINEL_DEMO_EXECUTION_ENABLED=false
```

For OpenAI, set `LLM_PROVIDER=openai`, choose an allowed OpenAI model, and set
`OPENAI_API_KEY`. LiteLLM builds routes such as:

```text
gemini + gemini-3.5-flash-lite
→ litellm/gemini/gemini-3.5-flash-lite
```

Never commit `.env`. API keys are used only by the backend and are never
returned to the browser.

## Run the console

```bash
python main.py
```

Type `exit` to close the application.

## Run the web UI

```bash
uvicorn app.api:create_app --factory --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The UI provides a compact model selector, streaming Agent activity, structured
verified facts, natural-language responses, and dedicated approval/rejection
buttons for Demo plans.

## Example prompts

```text
Analyze my BTC exposure and tell me whether it currently looks risky.

Keep at least 30% in USDT, no asset above 40%, and block rebalancing during high volatility. Then analyze my portfolio.

My goal is growth for 12 months and I accept a 20% decline. Give me several options.

Scan the strongest Binance markets for one-month growth and compare the best candidates.

Propose a 50 USDT BTC Demo purchase.
```

## API and streaming

Main endpoints:

```text
GET  /api/models
POST /api/chat/stream
POST /api/plans/{plan_id}/approve-symbol
POST /api/plans/{plan_id}/approve
POST /api/plans/{plan_id}/reject
```

The chat endpoint emits safe SSE events:

```text
activity   → STARTED / COMPLETED / FAILED tool progress
text_delta → validated LLM interpretation chunks
completed  → typed policy, profile, analysis, research, activity, and execution data
error      → sanitized failure message
```

Raw prompts, secrets, tool arguments, raw Binance responses, raw candles, and
hidden chain-of-thought are not exposed in the activity timeline.

## Testing

```bash
python -m pytest -q
node --test tests/test_ui.js
python -m compileall -q app main.py tests
git diff --check
```

Tests use fake gateways and fake subprocesses. The automated suite does not call
OpenAI, Gemini, Binance, or a real CLI process, and it never places an order.

## Project structure

```text
sentinel-agent/
├── app/
│   ├── agent/       # Active Agent loop, prompts, tools, context, memory, streaming
│   ├── binance/     # Fixed-command CLI runner, schemas, and Demo gateway
│   ├── execution/   # Immutable plan store and lifecycle
│   ├── models/      # Pydantic domain and API models
│   ├── services/    # Deterministic policy, analysis, research, risk, and execution
│   ├── api.py       # FastAPI, SSE, plan endpoints, static UI hosting
│   ├── application.py
│   ├── bootstrap.py
│   ├── config.py
│   └── sessions.py
├── docs/
├── tests/
├── web/
├── main.py
└── requirements.txt
```

## Documentation

- [Current capabilities — Vietnamese](docs/current-capabilities.md)
- [Agent guidelines](docs/agent-guidelines.md)
- [Development guidelines](docs/development-guidelines.md)
- [Testing guidelines](docs/testing.md)

## Current limitations

- Portfolio, policy, profile, and execution features use Binance Demo only.
- Conversation, policy, investor profile, and pending plans are stored in memory
  and are lost when the process stops.
- Binance MCP is not connected; Sentinel currently uses the official Binance CLI.
- Market research uses Binance market/volume/kline data only; it does not yet use
  news, on-chain data, sentiment feeds, or predictive ML models.
- Execution requires the dedicated approval endpoint/action used by the UI; chat
  text alone never grants approval.
- Sentinel does not support withdrawals, transfers, derivatives, autonomous
  continuous monitoring, or unrestricted autonomous trading.

## Disclaimer

Sentinel is an educational and hackathon project. It uses simulated Binance Demo
Trading data and does not provide guaranteed financial outcomes. Nothing in this
project is an offer, solicitation, or promise of investment performance.
