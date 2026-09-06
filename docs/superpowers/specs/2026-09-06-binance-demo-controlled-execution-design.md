# Binance Demo Controlled Execution Design

## Goal

Allow Sentinel to propose and execute Binance Demo Spot BUY/SELL orders while preserving the rule: AI understands intent, deterministic Python authorizes financial actions, and the user explicitly approves the exact plan.

## Scope

- Binance Demo only.
- Spot MARKET orders for `BTCUSDT` and `ETHUSDT` only.
- Quote value between 10 and 100 USDT per order.
- Every order requires explicit approval, even if a chat policy is more permissive.
- No production Binance, transfer, withdrawal, derivatives, autonomous execution, or raw generic CLI access.

## Architecture

The Agent receives one additional controlled tool, `propose_trade`, which can create a proposal but cannot execute it. Python validates the symbol, side, amount, current policy, current portfolio, and fresh market data, then stores an immutable pending plan.

Execution is outside the LLM tool loop. A dedicated approval API accepts the plan ID, atomically marks it approved, re-reads portfolio and market data, re-runs deterministic checks, submits one Binance Demo order with an idempotent client order ID, queries its status, and refreshes the portfolio. A rejection API closes the plan without contacting Binance.

## Policy and hard limits

Chat policy gains optional execution constraints: maximum trade value, maximum estimated slippage, and allowed trading symbols. These may make a plan stricter. They can never loosen application safety limits: Demo only, BTC/ETH only, 10–100 USDT, MARKET only, and approval always required.

## Plan lifecycle

`PENDING_APPROVAL -> APPROVED -> EXECUTING -> EXECUTED | FAILED`

`PENDING_APPROVAL -> REJECTED`

Plans expire after five minutes. Approval and execution are idempotent: retrying an already executed plan returns its saved result and never creates a second order.

## UI and API

The streamed chat response contains an optional pending plan. The chat renders a compact proposal card with Approve and Reject buttons. Approval calls a dedicated endpoint instead of sending an ambiguous natural-language message back through the LLM.

## Failure behavior

Missing data, changed prices, insufficient balance, expired plans, policy violations, excess slippage, CLI errors, or unconfirmed Binance order status fail closed. Sentinel never reports execution unless Binance Demo confirms the order status.

## Testing

All automated execution tests use fake gateways and runners. Tests cover hard limits, policy limits, immutable plans, exact approval, expiry, rejection, idempotency, safe CLI arguments, result parsing, API behavior, and UI rendering. No test sends an order to Binance or calls an LLM.
