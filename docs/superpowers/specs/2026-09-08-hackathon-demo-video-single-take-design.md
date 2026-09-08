# Sentinel Hackathon Demo Video — Single-Take Revision

Date: 2026-09-08

## Problem

The first export used separately recorded clips and extended still frames to meet
the target duration. Although its event order was truthful, the edit made the
Agent workflow appear discontinuous and its timing unnatural.

## Approved Direction

Replace the first export with one continuous recording of a fresh Sentinel
browser session. The take must visibly preserve this uninterrupted sequence:

```text
fresh chat
→ complete natural-language request
→ live Agent Pulse activity
→ final response and Verified Tool Facts
→ pending 50 USDT Binance Demo plan
→ explicit approval click
→ confirmed FILLED result
```

There must be no internal video cuts, speed changes, duplicated frames, frozen
frames, or reordered application states. Trimming is allowed only before the
first useful frame and after the final confirmed state.

## Capture Method

- Start the recording-only backend with Demo execution enabled for that process.
- Open a clean Chrome window on the recorded display and start a fresh session.
- Begin one screen recording before entering the request.
- Paste the complete approved request into the input as one value, then submit.
- Expand Agent Pulse while the controlled tool loop is still running.
- After completion, open Verified Tool Facts and deliberately scroll through the
  evidence, response, Risk Engine result, and pending plan.
- Keep the pending plan visible before clicking `Approve Demo order`.
- Remain on the same page until Binance Demo reports `FILLED`.
- End the recording only after the confirmed state has remained readable.

## Timing

The application determines the pace; the edit does not manufacture it. Aim for
an 85–90 second final export by using deliberate real-time pauses while the
request, evidence, approval boundary, and FILLED result are readable. If the
live workflow completes unusually quickly or slowly, truthful continuity takes
priority over hitting an exact duration, while the final must remain at or below
90 seconds.

## Captions and Presentation

English captions may be overlaid after capture, but only as timed graphics over
the continuous take. Captions must not conceal Agent Pulse, Verified Tool Facts,
the approval controls, or the execution result. The video remains silent,
1920×1080, 30 fps, H.264, and yuv420p.

No terminal, `.env`, credentials, personal notifications, unrelated tabs, or
production-account information may appear.

## Acceptance Criteria

- One continuous source take with no internal cuts or synthetic holds.
- The complete request is visible before submission.
- Agent Pulse visibly changes as real tools run.
- Verified Tool Facts and the selected opportunity are readable.
- The 50 USDT Binance Demo plan is visibly pending before approval.
- The approval click is visible.
- `FILLED` appears only after confirmation from Binance Demo.
- Final duration is no more than 90 seconds.
- Output is 1920×1080, 30 fps, H.264, and yuv420p.
- The full video plays without corruption, notifications, secrets, or unrelated
  application content.
