# Sentinel Agent

Sentinel is a policy-driven AI Agent that analyzes portfolio risk using Binance
Demo Trading data. It is a Track A project for the Binance Agent OS Mini
Hackathon and uses the official Binance Skills Hub `binance-cli` integration.

Sentinel never places an order. Demo balances are simulated and every response
must label them as Binance Demo data.

## Responsibility boundaries

```text
The LLM decides which controlled read/policy/evaluation tool is needed next.
Binance Skills Hub supplies Demo portfolio and market observations.
Python calculates allocations, policy violations, proposals, and risk decisions.
RiskEngine enforces deterministic safety rules.
Python renders authoritative facts; the same LLM adds qualitative interpretation.
```

The LLM is not authoritative for arithmetic, thresholds, permissions, or trade
execution.

The Agent can call exactly five tools: `get_portfolio`, `get_market_data`,
`update_policy`, `view_policy`, and `evaluate_portfolio_risk`. There are no
order, trade, transfer, withdrawal, or generic CLI tools.

## Policy-driven agent loop

For:

```text
Analyze my BTC exposure and tell me whether it currently looks risky.
```

Sentinel executes this sequence:

```text
User
  ↓
Sentinel Agent / LLM
  ├── get_portfolio → trusted Binance Demo holdings
  ├── get_market_data → trusted Binance Demo market observations
  ├── update_policy / view_policy → validated working policy
  └── evaluate_portfolio_risk
        ├── deterministic allocation and violation checks
        ├── deterministic rebalance proposal
        └── RiskEngine → BLOCKED / REQUIRES_APPROVAL / SAFE_TO_PROPOSE
  ↓
Python renders facts/status → LLM interpretation is appended with a label
```

The SDK returns every tool result to the LLM, so it can inspect the observation
and choose the next safe tool. The LLM may judge whether concentration or market
conditions deserve attention, but only Python can produce formal calculations,
plans, and risk status. The LLM cannot select CLI subcommands or URLs.

Policy updates are staged inside one Agent run and committed to the in-memory
session only after the run succeeds. The earlier `request_interpreter.py`,
`analysis_reporter.py`, `policy_conversation_service.py`, `sentinel.py`, and
`app/tools/` paths remain as tested legacy/educational code; `tool_loop.py` and
`controlled_tools.py` are the active console runtime.

Recent conversation is also kept in a process-local Agents SDK session so
follow-ups such as `More growth` can refer to the preceding exchange. Before a
new run, Sentinel keeps at most 16 user/assistant messages and removes old
tool calls and tool results. A fresh `SentinelRunContext` and fresh Binance reads
remain mandatory for current financial analysis. Conversation and policy state
are both lost when the process stops.

After a successful analysis, the LLM presents Assessment, Rationale,
Recommendation, and Limitations in the user's language. Concrete asset or
percentage allocations require the user's objective, time horizon, and risk
tolerance; otherwise Sentinel asks a focused clarification question.

To keep sequential tool use bounded, one request may inspect at most 20 market
symbols. Larger scopes fail closed and should be split into smaller requests.

## Project structure

```text
sentinel-agent/
├── app/
│   ├── agent/             # Active tool loop, controlled tools, prompts/context
│   ├── application.py     # End-to-end conversational orchestration
│   ├── binance/           # Safe CLI runner, response schemas, gateway
│   ├── models/            # Pydantic domain models
│   ├── services/          # Deterministic policy/planning/risk logic
│   ├── tools/             # Legacy two-tool educational example
│   ├── config.py
│   ├── gateways.py
│   └── sessions.py
├── tests/                 # Offline tests; no Binance or LLM calls
├── web/                   # Static vintage UI prototype
├── docs/
├── main.py
└── requirements.txt
```

More detail:

- [Sổ tay kiến trúc và mã nguồn hiện tại](docs/sentinel-project-guide.html)
- [Architecture](docs/architecture.md)
- [Development guidelines](docs/development-guidelines.md)
- [Agent guidelines](docs/agent-guidelines.md)
- [Testing guidelines](docs/testing.md)
- [Binance Skills Hub setup](docs/binance-skills-hub.md)
- [Vietnamese SRD guide — historical MCP design](docs/sentinel-srd-guide.html)

## Requirements

- Python 3.12
- Official `binance-cli` 2.1.1 (the version validated by this project)
- A Binance Demo Trading API key for portfolio reads
- An OpenAI or Gemini API key for the LLM

## Python setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Install the official Binance CLI

For security, download and inspect the official installer instead of piping
network output directly into a shell:

```bash
curl --proto '=https' --tlsv1.2 -L \
  https://github.com/binance/binance-cli/releases/download/v2.1.1/binance-cli-installer.sh \
  -o /tmp/binance-cli-installer.sh
less /tmp/binance-cli-installer.sh
sh /tmp/binance-cli-installer.sh
binance-cli --version
```

The source and releases belong to the official
[binance/binance-cli](https://github.com/binance/binance-cli) repository.

## Configure `.env`

```bash
cp .env.example .env
```

Gemini example:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
LLM_MAX_TOKENS=4096
GEMINI_API_KEY=your_gemini_api_key

BINANCE_API_ENV=demo
BINANCE_CLI_PATH=binance-cli
BINANCE_API_KEY=your_demo_api_key
BINANCE_SECRET_KEY=your_demo_secret_key
```

OpenAI example:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
LLM_MAX_TOKENS=4096
OPENAI_API_KEY=your_openai_api_key
```

`LLM_MODEL` contains the provider model ID. Sentinel constructs the LiteLLM
route, for example:

```text
gemini + gemini-3.5-flash-lite
→ litellm/gemini/gemini-3.5-flash-lite
```

`LLM_MAX_TOKENS` is the maximum model output budget used by every Agent.
Sentinel omits provider-specific reasoning options. For GPT-5.4 Mini, `none` is
already the OpenAI default; omitting the redundant parameter also keeps
LiteLLM on its stable tool-calling path.

For short-lived local troubleshooting only, enable verbose LiteLLM logs:

```dotenv
LITELLM_DEBUG=true
```

Restart `python main.py` after changing the flag. Debug output can include the
prompt, current policy, portfolio context, and request body. Do not commit the
flag as enabled and do not share debug logs publicly. Set it back to `false`
after diagnosing the provider error.

Never commit `.env`. Never paste Binance credentials into chat or frontend
code. Use keys created in Binance Demo Trading, not production credentials.

## Read-only Binance commands

Sentinel's gateway contains a fixed allowlist:

```text
spot get-account --omit-zero-balances true
spot ticker-price
spot ticker24hr --symbol <validated symbol>
spot depth --symbol <validated symbol> --limit 100
```

There is no generic `binance-cli request`, order, cancel, trade, transfer, or
withdrawal code path.

## Run

```bash
python main.py
```

Try analysis:

```text
Sentinel > Analyze my BTC exposure and tell me whether it currently looks risky.
```

Try policy chat:

```text
Sentinel > Giữ ít nhất 30% USDT, không asset nào trên 40%, chặn rebalance khi volatility HIGH, rồi phân tích portfolio.
Sentinel > Xem policy hiện tại.
```

Try general chat:

```text
Sentinel > Xin chào.
```

Policy and short conversation history are kept per console session in memory
and are lost when the process stops.

Type `exit` to close the console.

## Test

```bash
python -m pytest -q
node --test tests/test_ui.js
python -m compileall -q app main.py tests
```

Tests use fake gateways and fake subprocesses. They never call Binance, OpenAI,
Gemini, or a real CLI process.

## Static UI preview

```bash
python -m http.server 8000 -d web
```

Open [http://localhost:8000](http://localhost:8000). The current frontend is a
static visual prototype: its progress animation and result cards are simulated.
It never receives LLM or Binance API keys.

## What gets replaced later?

`BinanceCliGateway` is behind the application-owned
`PortfolioMarketGateway` protocol. If Binance later supports Sentinel as a
direct MCP client, a new MCP gateway can implement the same two methods without
changing the application workflow, domain models, or deterministic services.
