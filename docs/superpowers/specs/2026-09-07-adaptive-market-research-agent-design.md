# Adaptive Binance Market Research Agent

## Goal

Make Sentinel an evidence-driven assistant that forms its own market-research
plan, investigates Binance Spot data, and gives a clear personal judgment instead
of replaying one fixed analysis workflow.

This phase uses Binance data only. It does not add news, unrestricted code
execution, production trading, transfer, or withdrawal.

## Sentinel personality

Sentinel is calm, direct, evidence-driven, and willing to disagree with the user.
It states which option it prefers and gives concise, verifiable reasons. Its
aggressiveness adapts to the validated investor profile, while its core safety
standards do not change. It clearly states material uncertainty and never claims
confidence unsupported by current observations.

This is an observable communication and decision style. Sentinel does not expose
hidden chain-of-thought. It provides a decision summary: evidence considered,
trade-offs, conclusion, and conditions that could invalidate the conclusion.

## Adaptive Agent loop

```text
User request + validated policy + validated investor profile
                         ↓
                 LLM chooses a research plan
                         ↓
              Python validates bounded parameters
                         ↓
                 scan_top_markets()
                         ↓
          LLM selects candidates worth deeper study
                         ↓
             analyze_market_history() per candidate
                         ↓
       Python calculates deterministic market indicators
                         ↓
         LLM compares evidence and may request more data
                         ↓
          LLM gives its judgment and alternatives
                         ↓
      Optional TradePlan → RiskEngine → explicit approval
```

The LLM chooses the analysis recipe, not executable Python code. It may select
timeframes, lookback, candidate count, and which verified candidates deserve
deeper analysis. It can iterate when the first observations are insufficient.

## Controlled research tools

### `scan_top_markets(limit)`

Reads Binance 24-hour ticker data and returns the most liquid eligible Spot USDT
markets ranked by quote volume. Deterministic Python:

- requires symbol status `TRADING`, Spot permission, and USDT quote asset;
- excludes stablecoins and leveraged-token suffixes;
- ranks by Binance `quoteVolume`, not a value invented by the LLM;
- accepts a validated limit from 3 to 10.

The result includes symbol, last price, 24-hour change, quote volume, and a data
timestamp. High volume is treated as liquidity evidence, not proof that an asset
is a good investment.

### `analyze_market_history(symbol)`

Reads Binance klines according to the active research plan. Python calculates
deterministic summaries rather than sending hundreds of raw candles to the LLM:

- return over the selected lookback;
- short-versus-long moving-average trend;
- realized volatility;
- maximum drawdown;
- recent volume change;
- current liquidity and estimated slippage where required.

The tool only accepts candidates returned by the current market scan. This stops
the LLM from injecting arbitrary symbols or command arguments.

### `set_market_research_plan(...)`

The LLM calls this first with a bounded, inspectable recipe:

```text
candidate_limit: 3..10
timeframes: subset of 15m, 1h, 4h, 1d
lookback_days: 1..90
priorities: ordered subset of
  LIQUIDITY, MOMENTUM, DOWNSIDE_CONTROL, VOLATILITY_OPPORTUNITY
```

Pydantic validates the request. Python stores the accepted plan only in the
current Agent run context. Market scan and history tools refuse to run without a
valid plan.

## Division of responsibility

The LLM:

- chooses a research plan appropriate to the request and investor profile;
- chooses which scanned candidates need deeper investigation;
- compares verified indicator summaries;
- makes a qualitative judgment, rejects weak candidates, and recommends its
  preferred option with alternatives;
- may request another permitted timeframe or candidate analysis when evidence is
  insufficient.

Python:

- validates plan bounds and symbol provenance;
- retrieves and schema-validates Binance data;
- calculates indicators and maintains timestamps;
- enforces call, candidate, timeframe, and lookback limits;
- keeps RiskEngine, trade planning, approval, and execution authoritative.

The LLM never receives a generic CLI tool and cannot generate or execute Python.

## Natural evidence-driven response

The response format is chosen by the LLM according to the conversation. Fixed
Assessment, Rationale, Recommendation, and Limitations headings are not required.
A useful response must still make these ideas understandable:

- which option Sentinel prefers;
- the verified observations supporting that preference;
- meaningful trade-offs and alternative choices;
- missing evidence or conditions that could reverse the judgment.

Numbered options are rendered as a proper ordered list by the chat UI. Verified
tool facts and formal execution state remain separate from model prose.

## Safety and failure handling

- Research is read-only and uses Binance Demo/public market data.
- A recommendation never counts as trade approval.
- A trade still requires the existing immutable plan, deterministic checks, and
  explicit UI approval flow.
- Unsupported symbols, invalid plans, stale/malformed Binance responses, and
  insufficient klines fail closed without fabricated values.
- One run analyzes at most 10 candidates and 90 days of history.
- Partial candidate failure is disclosed. Sentinel needs at least two verified
  candidates before making a comparative market recommendation.

## Activity timeline

Expose safe high-level events without chain-of-thought:

```text
Research plan validated
Top Binance markets scanned
BTCUSDT history analyzed
ETHUSDT history analyzed
Candidate comparison completed
```

Raw prompts, tool arguments, credentials, and hidden reasoning are not shown.

## Testing

Offline tests use fake Binance payloads and must cover:

- plan bounds and allowed timeframes;
- quote-volume ranking and excluded asset types;
- deterministic indicator calculations;
- refusal to analyze a symbol absent from the current scan;
- partial and total data failures;
- Agent tool allowlist and adaptive prompt contract;
- natural ordered-list rendering and decimal-number regression;
- no test calling Binance or an LLM;
- the existing trade approval and RiskEngine suites remaining green.
