# Sentinel Agent

Sentinel is a policy-driven AI Agent that analyzes portfolio risk using Binance
Demo Trading data. It is a Track A project for the Binance Agent OS Mini
Hackathon and uses the official Binance Skills Hub `binance-cli` integration.

Sentinel never places an order. Demo balances are simulated and every response
must label them as Binance Demo data.

## Responsibility boundaries

```text
LLM understands the request, chooses application tools, and explains results.
Binance Skills Hub supplies Demo portfolio and market observations.
Python calculates allocations, policy violations, proposals, and risk decisions.
RiskEngine enforces deterministic safety rules.
```

The LLM is not authoritative for arithmetic, thresholds, permissions, or trade
execution.

## Agent loop

For:

```text
Analyze my BTC exposure and tell me whether it currently looks risky.
```

the OpenAI Agents SDK lets the LLM choose this sequence:

```text
User
  ↓
Sentinel Agent / LLM
  ├── get_portfolio()
  │         ↓
  │   BinanceCliGateway
  │         ↓
  │   binance-cli spot get-account
  │
  └── get_market_data("BTCUSDT")
            ↓
      BinanceCliGateway
            ↓
      ticker24hr + depth
  ↓
LLM explains facts and interpretation separately
```

Only the two application tools are visible to the LLM. It cannot select CLI
subcommands, URLs, order commands, transfers, or withdrawals.

## Project structure

```text
sentinel-agent/
├── app/
│   ├── agent/             # LLM instructions and Agent construction
│   ├── binance/           # Safe CLI runner, response schemas, gateway
│   ├── models/            # Pydantic domain models
│   ├── services/          # Deterministic policy/planning/risk logic
│   ├── tools/             # Two AI-callable application tools
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
OPENAI_API_KEY=your_openai_api_key
```

`LLM_MODEL` contains the provider model ID. Sentinel constructs the LiteLLM
route, for example:

```text
gemini + gemini-3.5-flash-lite
→ litellm/gemini/gemini-3.5-flash-lite
```

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

Try:

```text
Sentinel > Analyze my BTC exposure and tell me whether it currently looks risky.
```

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
changing the domain models, deterministic services, or AI-visible tool names.
