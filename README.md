# Sentinel Agent

Sentinel is a policy-driven AI Agent that analyzes portfolio risk using Binance
Demo Trading data. It is a Track A project for the Binance Agent OS Mini
Hackathon and uses the official Binance Skills Hub `binance-cli` integration.

Sentinel can optionally place a tightly constrained Binance Demo Spot order only
after the user approves an immutable plan in the UI. Demo balances are simulated
and every response must label them as Binance Demo data.

## Responsibility boundaries

```text
The LLM decides which controlled read/policy/evaluation/proposal tool is needed next.
Binance Skills Hub supplies Demo portfolio and market observations.
Python calculates allocations, policy violations, proposals, and risk decisions.
RiskEngine and the execution service enforce deterministic safety rules.
Python renders authoritative facts; the same LLM adds qualitative interpretation.
```

The LLM is not authoritative for arithmetic, thresholds, permissions, approval,
or trade execution.

The Agent can call exactly eight tools: `get_portfolio`, `get_market_data`,
`update_policy`, `view_policy`, `update_investor_profile`,
`view_investor_profile`, `evaluate_portfolio_risk`, and `propose_trade`. The last
tool only creates a pending plan. There is no order-execution, transfer,
withdrawal, or generic CLI tool available to the LLM.

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
  ├── update_investor_profile / view_investor_profile → saved preferences
  └── evaluate_portfolio_risk
        ├── deterministic allocation and violation checks
        ├── deterministic rebalance proposal
        └── RiskEngine → BLOCKED / REQUIRES_APPROVAL / SAFE_TO_PROPOSE
  └── propose_trade → validated immutable plan, never an order
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
remain mandatory for current financial analysis. Conversation, policy, and
investor-profile state are lost when the process stops.

The investor profile stores only preferences explicitly stated in chat:
objective, time horizon, risk tolerance, acceptable loss, liquidity need, and
excluded assets. It is neither portfolio data nor permission to trade.

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
│   ├── api.py             # FastAPI routes, SSE encoding, static UI
│   ├── application.py     # End-to-end conversational orchestration
│   ├── bootstrap.py       # Runtime dependency composition
│   ├── binance/           # Safe CLI runner, response schemas, gateway
│   ├── execution/         # In-memory immutable plan lifecycle
│   ├── models/            # Pydantic domain models
│   ├── model_catalog.py   # Backend allowlist for selectable LLM routes
│   ├── services/          # Deterministic policy/planning/risk logic
│   ├── tools/             # Legacy two-tool educational example
│   ├── config.py
│   ├── gateways.py
│   └── sessions.py
├── tests/                 # Offline tests; no Binance or LLM calls
├── web/                   # Chat-first UI with per-response Agent Pulse
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
LLM_ALLOWED_MODELS=gemini/gemini-3.5-flash-lite,openai/gpt-5.6-luna
LLM_MAX_TOKENS=4096
GEMINI_API_KEY=your_gemini_api_key

BINANCE_API_ENV=demo
BINANCE_CLI_PATH=binance-cli
BINANCE_API_KEY=your_demo_api_key
BINANCE_SECRET_KEY=your_demo_secret_key
SENTINEL_DEMO_EXECUTION_ENABLED=false
```

OpenAI example:

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
LLM_ALLOWED_MODELS=openai/gpt-5.6-luna,gemini/gemini-3.5-flash-lite
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

`LLM_ALLOWED_MODELS` is a backend allowlist, not a live provider-model fetch.
Only routes whose provider key is configured are returned by `GET /api/models`;
the endpoint never returns credentials. The browser includes the chosen
`provider` and `model` in `POST /api/chat/stream`, and the backend rejects any
route outside the allowlist.

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

## Binance command boundary

Sentinel's gateway contains a fixed allowlist:

```text
spot get-account --omit-zero-balances true
spot ticker-price
spot ticker24hr --symbol <validated symbol>
spot depth --symbol <validated symbol> --limit 100
spot exchange-info --symbol <validated symbol> --show-permission-sets false
```

When Demo execution is explicitly enabled, the separate execution service may
also use only:

```text
spot new-order --symbol <Binance-verified Spot USDT symbol> --side <BUY|SELL> --type MARKET ...
spot get-order --symbol <validated symbol> --orig-client-order-id <plan client id>
```

There is no generic `binance-cli request`, cancel, transfer, withdrawal,
derivatives, or production-Binance code path.

## Controlled Demo execution

Execution is disabled by default. To try it, create a Binance Demo API key with
Spot trading permission and set:

```dotenv
SENTINEL_DEMO_EXECUTION_ENABLED=true
```

Hard application limits cannot be loosened in chat:

- Binance Demo only;
- normal approval for `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, `XRPUSDT`,
  `ADAUSDT`, and `DOGEUSDT`;
- another token requires Binance `exchange-info` validation and a separate,
  plan-scoped token-exception approval;
- MARKET BUY/SELL only;
- 10–100 USDT per order;
- explicit approval for every order;
- plan expires after five minutes.

Policy chat may make these limits stricter using maximum trade value, maximum
estimated slippage, allowed symbols, allocation limits, stablecoin reserve, and
high-volatility blocking. The flow is:

```text
LLM reads fresh data → Python validates → LLM proposes PLAN-ID
→ for a non-default token, user first approves that token exception
→ user separately approves the Demo order → Python reads fresh data and validates again
→ gateway submits one Demo order → gateway queries order
→ only FILLED becomes EXECUTED → portfolio is refreshed
```

The plan ID becomes Binance's client order ID, so retrying an already completed
approval returns the saved result instead of submitting another order. Automated
tests always use fake gateways and never send orders.

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

## Run the web UI

```bash
uvicorn app.api:create_app --factory --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The browser sends chat to
`POST /api/chat/stream`. The compact header picker shows routes returned by
`GET /api/models`; API keys never reach the browser. Changing the model keeps
the same `session_id`, so conversation, policy, and investor profile continue.

The endpoint emits named SSE events:

```text
activity   → safe STARTED/COMPLETED tool progress
text_delta → validated AI interpretation chunks
completed  → typed JSON with policy, profile, analysis, activity, execution state
error      → generic safe failure message
```

Tool arguments, raw results, chain-of-thought, and credentials are not placed in
activity events. Model prose is buffered until safety validation passes, so
activity appears live while answer chunks begin after validation.

Each assistant response owns a small collapsible **Agent Pulse**. It shows only
safe tool/activity status from the backend; it is not model reasoning or hidden
chain-of-thought.

When the Agent creates a valid proposal, the response also includes a compact
Demo order card. **Approve Demo order** and **Reject** call dedicated endpoints;
approval is not inferred from ordinary chat text.

Default tokens use `POST /api/plans/{plan_id}/approve`. A valid token outside
the default set first uses `POST /api/plans/{plan_id}/approve-symbol`; this only
moves that exact, unexpired plan to `PENDING_APPROVAL`. It does not submit an
order. The user must then click **Approve Demo order**, and all market, policy,
balance, and Binance symbol checks run again before submission.

Try profile chat:

```text
My objective is growth, my horizon is 3 years, and I accept a 20% decline.
Show my investor profile.
Analyze my portfolio and suggest a direction consistent with my profile.
```

## Test

```bash
python -m pytest -q
node --test tests/test_ui.js
python -m compileall -q app main.py tests
```

Tests use fake gateways and fake subprocesses. They never call Binance, OpenAI,
Gemini, or a real CLI process.

## What gets replaced later?

`BinanceCliGateway` is behind application-owned read and Demo-execution
protocols. If Binance later supports Sentinel as a direct MCP client, a new MCP
gateway can implement those protocols without changing the Agent, domain models,
or deterministic services.
