# Sentinel Binance Skills Hub Integration Design

## Goal

Replace mocked production data and the unsupported custom Binance MCP client with
read-only Binance Demo Trading data obtained through the official Binance Skills Hub
`binance-cli`, while preserving Sentinel's LLM-driven application tool loop and
deterministic risk controls.

## Track and scope

Sentinel targets Binance Agent OS Mini Hackathon Track A. It uses Binance Skills
Hub, an Agent OS component, to build a portfolio-policy agent. It does not target
Track B, connect to the Agentic MCP server in its normal runtime, or execute a
trade.

This checkpoint supports:

- Spot Demo account balances through a Binance Demo API key.
- Public Spot Demo prices and 24-hour market data.
- Deterministic USD valuation, allocation, volatility classification, policy
  checks, proposal creation, and risk decisions.
- LLM selection of the stable `get_portfolio()` and
  `get_market_data(symbol)` application tools.

It does not support order placement, transfer, withdrawal, arbitrary CLI
commands, MCP OAuth, FastAPI, or persistent credentials.

## Options considered

1. Binance Agentic MCP: preferred protocol boundary, but Binance rejected the
   custom Sentinel OAuth client as unsupported.
2. Direct HTTP calls: technically simple, but duplicates request signing and
   uses Agent OS less visibly.
3. Binance Skills Hub `binance-cli`: selected because it is official, works for
   Track A, provides the required Spot account and market capabilities, and
   keeps exchange-specific access behind a replaceable gateway. Demo Trading
   removes financial risk while still returning Binance-managed simulated data.

## Architecture

```text
User
  ↓
Sentinel Agent / LLM
  ├── get_portfolio()
  └── get_market_data(symbol)
             ↓
      BinanceCliGateway
             ↓
   allowlisted binance-cli commands
             ↓
          Binance API

Validated domain models
  ↓
deterministic Python services
  ↓
policy violations → proposal → RiskEngine
  ↓
LLM explanation
```

The Agent depends on a `PortfolioMarketGateway` protocol rather than directly
depending on the CLI. Tool factories close over that gateway so the LLM sees no
gateway argument and no command-construction surface.

## Components

### `app/gateways.py`

Defines the application-owned async port:

```python
class PortfolioMarketGateway(Protocol):
    async def get_portfolio(self) -> Portfolio: ...
    async def get_market_data(self, symbol: str) -> MarketDataResult: ...
```

### `app/binance/runner.py`

Runs the configured `binance-cli` executable with an argument list, never a
shell string. It enforces a timeout, captures JSON stdout, returns clear typed
errors, and never includes environment values in exceptions or logs.

Only the gateway owns calls to the runner. There is no generic CLI tool exposed
to the LLM.

### `app/binance/gateway.py`

Uses a fixed allowlist of read commands:

```text
spot get-account --omit-zero-balances true
spot ticker-price
spot ticker24hr --symbol <validated symbol>
spot klines --symbol <validated symbol> --interval 1h --limit 25
spot depth --symbol <validated symbol> --limit 100
```

It validates CLI JSON with small Pydantic transport models and converts it to
Sentinel domain models. Asset quantities are `free + locked`. USDT is valued at
one USD for MVP; other non-zero assets use their `ASSETUSDT` price. If an asset
cannot be valued, portfolio analysis fails visibly instead of dropping it.

Market symbols must match `^[A-Z0-9]{5,20}$`. Twenty-four-hour change comes from
the ticker. Volatility is classified by deterministic Python from the absolute
24-hour move: LOW below 2%, MEDIUM from 2% to below 4%, HIGH at 4% or above. The
depth snapshot estimates slippage for a documented $1,000 reference sale; an
insufficient book produces a data error.

### `app/tools/portfolio.py` and `app/tools/market.py`

Become tool factories bound to `PortfolioMarketGateway`. Their AI-visible names
and descriptions remain stable. No mock fallback remains in the runtime path.

### `app/agent/sentinel.py` and `main.py`

Create one `BinanceCliRunner`, one `BinanceCliGateway`, bind both tools, and pass
them to the Agent. Startup validates LLM configuration, CLI path, and read-only
Binance Demo credentials before portfolio access. `BINANCE_API_ENV` defaults to
`demo`; `prod` remains an explicit later configuration for a read-only key. Public
market calls remain usable without credentials, but the complete Sentinel analysis
requires Demo account data. Tool results and final explanations label the source as
Binance Demo and never describe simulated holdings as the user's real portfolio.

## Security rules

- The user creates a Binance Demo API key. Production credentials are not required
  for this checkpoint. If `prod` is enabled later, its key must have Reading enabled
  and every trading, transfer, and withdrawal permission disabled.
- Secrets stay only in local environment variables and are never deployed,
  committed, logged, placed in exceptions, or sent to the LLM.
- The process runner uses `create_subprocess_exec`/argument arrays and never
  `shell=True`.
- The LLM cannot select CLI subcommands or pass arbitrary URLs.
- The gateway contains no order, transfer, cancel, or generic `request`
  capability.
- Binance failures are fail-closed; mock data is never substituted.
- The unused MCP implementation, dependencies, tests, documentation, and hosted
  metadata file are removed from the production project. The web UI remains.

## Error handling

Configuration errors name only the missing variable or executable. CLI timeout,
non-zero exit, invalid JSON, invalid schema, unsupported symbol, missing price,
and insufficient order-book depth become safe application errors without
including stderr that might contain credentials. The Agent tells the user that
required Binance data could not be verified and produces no recommendation.

## Testing and verification

Unit tests use a fake runner and fixture JSON; no test calls Binance, an LLM, or
a subprocess. Tests cover command allowlisting, symbol validation, account
mapping, total/weight calculation, market mapping, volatility thresholds,
slippage, malformed responses, missing prices, and sanitized failures.

Integration verification is manual and ordered:

1. Install the official CLI and inspect its version/help.
2. Call public Demo `ticker24hr` with no credentials.
3. Let the user configure a local Demo key without sharing it in chat.
4. Call Demo `get-account` and confirm only non-sensitive structured output is mapped.
5. Run Sentinel and observe the LLM autonomously use both application tools.

All existing Python and UI tests, Python compilation, and `git diff --check`
must pass before completion.
