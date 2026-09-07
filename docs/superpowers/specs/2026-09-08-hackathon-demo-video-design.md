# Sentinel Hackathon Demo Video Design

Date: 2026-09-08

## Objective

Create an 85–90 second, English-captioned screen recording for the Binance Agent
OS Mini Hackathon Track A. The video must show that Sentinel is a real agentic
workflow rather than a chatbot or a static UI.

The central story is:

```text
One natural-language request
→ autonomous controlled tool use
→ fresh Binance Agent OS observations
→ evidence-grounded LLM judgment
→ deterministic policy and risk validation
→ explicit human approval
→ Binance Demo execution and verification
```

## Audience and Format

- Audience: international Binance hackathon reviewers.
- Language: English.
- Narration: none.
- Communication: concise on-screen captions plus visible application output.
- Resolution: 1920×1080.
- Target duration: 85–90 seconds.
- Audio: none, avoiding narration quality and music-licensing risks.

## Demo Request

The user submits one request:

```text
My goal is growth over 12 months and I can accept a 20% drawdown.
Keep at least 30% in stablecoins, limit each trade to 50 USDT,
and reject slippage above 0.1%.

Review my Binance Demo portfolio. Scan the highest-volume Binance
Spot USDT markets, select the most relevant candidates, analyze
their recent market history, compare the evidence, and choose your
preferred opportunity.

If the Risk Engine allows it, propose a 50 USDT Demo market buy.
Do not execute without my explicit approval.
```

This deliberately avoids hard-coding BTC, ETH, or SOL. The Agent must create a
bounded research plan, scan current high-volume markets, choose which candidates
deserve deeper analysis, compare verified evidence, and state its own preferred
opportunity.

## Storyboard

### 0–5 seconds — Identity

Show the Sentinel chat interface and overlay:

```text
SENTINEL
A policy-driven AI portfolio agent
Built with Binance Agent OS
```

### 5–15 seconds — One natural-language request

Paste and submit the approved demo request. Overlay:

```text
One request. The Agent plans the workflow.
```

### 15–40 seconds — Observable agent loop

Expand Agent Pulse. Preserve the real ordered activity events, expected to
include the relevant subset of:

```text
Updating investor profile
Updating portfolio policy
Reading portfolio
Creating market research plan
Scanning top-volume markets
Analyzing candidate histories
Finalizing market research
Evaluating risk
Creating trade proposal
```

Overlay two short captions during this sequence:

```text
The LLM chooses controlled tools.
Binance Agent OS supplies fresh data.
```

Long network or model waits may be removed or accelerated, but the edit must not
reorder events or fabricate an activity state.

### 40–62 seconds — Evidence and judgment

Show the collapsible verified-facts/research view and the assistant response.
Keep visible:

- portfolio facts from Binance Demo;
- top-volume candidates and observation time;
- deterministic market indicators;
- the candidate comparison;
- Sentinel's preferred opportunity and rationale;
- the formal Risk Engine result;
- the immutable 50 USDT Demo plan.

Overlay:

```text
LLM judges. Python calculates and validates.
```

### 62–76 seconds — Explicit permission boundary

Show the plan card. If the selected token is outside the default allowlist, use
the separate plan-scoped token approval first. Then click the dedicated Demo
order approval action.

Overlay:

```text
A recommendation is not permission.
Every order requires explicit approval.
```

### 76–85 seconds — Execution verification

Show the Binance Demo result only after the application reports a confirmed
filled order and refreshes the portfolio. Keep `EXECUTED`/`FILLED` and the
post-order verification visible.

### 85–90 seconds — Closing frame

```text
AI understands.
Policy protects.
You stay in control.

github.com/pmjnt/sentinel-agent
```

## Visual and Editing Rules

- Record only the Sentinel browser window.
- Never show `.env`, credentials, debug logs, browser storage, or raw tool data.
- Keep the cursor movement deliberate and avoid unrelated tabs or notifications.
- Use a clean 16:9 crop with the application aligned consistently.
- Use small, high-contrast English captions near the lower edge without covering
  Agent Pulse, verified facts, plan controls, or execution status.
- Use subtle zooms only for the volume scan, Sentinel preference, Risk Engine,
  approval action, and final filled status.
- Do not display hidden chain-of-thought or describe Agent Pulse as reasoning.
- Do not claim production trading; label portfolio and execution as Binance Demo.
- Do not fabricate or pre-render financial results. The selected asset may change
  because the workflow uses fresh market data.

## Recording Preconditions

- The web UI starts successfully and can reach its configured LLM provider.
- Binance Demo credentials are configured only in the backend environment.
- `SENTINEL_DEMO_EXECUTION_ENABLED=true` is set for the recording session.
- The Demo account has enough USDT for a 50 USDT order.
- The configured model is allowed and supports the controlled tool loop.
- Screen-recording permission is available to the recording process.
- Notifications and unrelated applications are hidden.

## Failure Handling

- Run one private rehearsal before recording.
- If required market data fails, do not edit around the failure as though the run
  succeeded; diagnose it, start a fresh session, and record again.
- If the Risk Engine blocks the selected trade, retain that run only as optional
  safety footage. For the primary full-loop video, start a fresh run after
  confirming the approved policy and current market conditions support a safe
  proposal.
- If a non-default token is selected, show both approval stages rather than
  bypassing the plan-scoped token approval.
- If Binance does not confirm `FILLED`, do not show or caption the order as
  executed.
- Never reuse a completed or expired plan for a second order attempt.

## Verification Checklist

Before export, verify:

- duration is no longer than 90 seconds;
- resolution is 1920×1080;
- captions are English and readable at normal playback speed;
- the Agent Pulse shows real tool activity but no hidden reasoning;
- the Agent performs a top-volume scan and candidate analysis;
- verified facts are visually separate from LLM interpretation;
- a Risk Engine result is visible;
- explicit approval is visible;
- `FILLED` is visible only after Binance Demo confirmation;
- no secret, personal notification, or production-account information appears;
- the closing frame contains the correct public GitHub URL;
- the final MP4 plays from beginning to end without missing frames or corruption.

## Deliverables

- One final MP4 suitable for attaching to the Track A submission.
- One thumbnail or representative frame if time permits.
- A short English submission caption prepared separately after the video is
  verified.

