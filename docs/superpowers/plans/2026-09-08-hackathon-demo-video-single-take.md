# Sentinel Hackathon Demo Video Single-Take Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stitched demo export with an uninterrupted 85–90 second recording that visibly follows one real Sentinel session from request through Binance Demo `FILLED` confirmation.

**Architecture:** Capture one MOV source from the display containing a clean Chrome window, with every application interaction occurring while that recording remains active. Produce the final MP4 in one FFmpeg encode from that source; timed caption images may be overlaid, but there are no internal cuts, speed changes, concatenation, cloned frames, or synthetic application states.

**Tech Stack:** FastAPI/Uvicorn, Sentinel web UI, Binance Demo Trading, Binance Skills Hub CLI, macOS Computer Use, `screencapture`, FFmpeg 8, Pillow caption assets.

---

## File Map

- Read: `docs/superpowers/specs/2026-09-08-hackathon-demo-video-single-take-design.md` — approved continuity and acceptance rules.
- Read: `.env` — validate configuration without printing credential values.
- Use locally, ignored: `.superpowers/binance-cli-demo-wrapper` — compatibility wrapper already used by the verified rehearsal.
- Create temporarily: `/private/tmp/sentinel-single-take.XXXXXX/single-take.mov` — the only source take.
- Create temporarily: `/private/tmp/sentinel-single-take.XXXXXX/caption-overlay-*.png` — transparent timed caption images.
- Replace locally, ignored: `artifacts/demo/sentinel-track-a-demo.mp4` — continuous final export.
- Replace locally, ignored: `artifacts/demo/sentinel-track-a-thumbnail.jpg` — approval-card thumbnail.

### Task 1: Preflight the Continuous Recording

- [ ] **Step 1: Confirm the repository and current ignored media remain clean**

Run:

```bash
git status --short
git check-ignore -v artifacts/demo/sentinel-track-a-demo.mp4
git check-ignore -v artifacts/demo/sentinel-track-a-thumbnail.jpg
```

Expected: `git status --short` prints nothing and both media files resolve to
`.gitignore` rules.

- [ ] **Step 2: Check required configuration without printing secrets**

Run:

```bash
.venv/bin/python -c "from dotenv import dotenv_values; c=dotenv_values('.env'); print({'provider':c.get('LLM_PROVIDER'),'model':c.get('LLM_MODEL'),'binance_env':c.get('BINANCE_API_ENV'),'provider_key':bool(c.get('OPENAI_API_KEY') or c.get('GEMINI_API_KEY')),'binance_key':bool(c.get('BINANCE_API_KEY')),'binance_secret':bool(c.get('BINANCE_SECRET_KEY'))})"
```

Expected: `binance_env` is `demo` and all three key booleans are `True`.

- [ ] **Step 3: Create the source-take directory**

Run:

```bash
mktemp -d /private/tmp/sentinel-single-take.XXXXXX
```

Expected: one new private directory. Preserve the returned absolute path for the
entire recording.

- [ ] **Step 4: Start the recording-only backend**

Run in a continuing session:

```bash
env SENTINEL_DEMO_EXECUTION_ENABLED=true BINANCE_CLI_PATH=/Users/pham.minh/Documents/sentinel-agent/.superpowers/binance-cli-demo-wrapper .venv/bin/uvicorn app.api:create_app --factory --host 127.0.0.1 --port 8000
```

Expected: Uvicorn listens on `127.0.0.1:8000`; no configuration file changes.

- [ ] **Step 5: Open a clean Chrome session on the recorded display**

Open `http://127.0.0.1:8000/?single-take=1` in a dedicated Chrome window. Use
Computer Use to confirm the empty chat, hide unrelated windows, and verify no
permission dialog or personal notification is visible.

### Task 2: Record One Uninterrupted Source Take

- [ ] **Step 1: Start the single screen recording**

Run once, targeting the display containing Chrome:

```bash
screencapture -v -V90 -D1 -x /private/tmp/sentinel-single-take.XXXXXX/single-take.mov
```

Replace the directory component with the exact path returned by Task 1. Do not
stop or restart this command during the workflow.

- [ ] **Step 2: Activate Chrome and show the idle Sentinel UI for three seconds**

Bring Chrome to the foreground after recording starts. Keep the cursor away from
the input and verify the recorded display contains Chrome rather than Codex.

- [ ] **Step 3: Enter and submit the complete approved request**

Set the chat input to this complete value in one operation, so embedded newlines
do not trigger an early submission:

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

Pause while the complete request is readable, then click `Send` exactly once.

- [ ] **Step 4: Show the live Agent Pulse**

While the request is running, expand the current Agent Pulse control. Keep it
visible as activity advances through portfolio retrieval, research planning,
market scan, history analysis, research finalization, deterministic risk, and
Demo trade proposal. Do not navigate away or collapse it.

- [ ] **Step 5: Show response and verified evidence**

After the same turn completes, pause on the Agent-selected opportunity and its
rationale. Expand `VERIFIED TOOL FACTS`, then scroll deliberately through the
portfolio allocation, scan timestamp, top-volume candidates, market indicators,
Risk Engine result, and `Execution: NOT_EXECUTED`.

- [ ] **Step 6: Show the pending plan before approval**

Scroll to the same turn's 50 USDT Binance Demo plan. Keep its PLAN-ID, asset,
amount, `No order has been sent`, and enabled `Approve Demo order` control visible
for at least four seconds.

- [ ] **Step 7: Approve once and wait for confirmation**

Click `Approve Demo order` once. Remain on the same plan card until the backend
returns `Demo order verified: FILLED`. Keep the confirmed state visible for at
least six seconds. If the request does not produce a pending plan or Binance
Demo does not confirm `FILLED`, discard the take and diagnose before retrying;
no fabricated state is allowed.

- [ ] **Step 8: Let the source recording end naturally**

Do not stop the recording early. Keep the confirmed application state visible
until the 90-second capture exits successfully.

### Task 3: Export Without Internal Editing

- [ ] **Step 1: Inspect the source take**

Run:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -show_entries format=duration -of default=noprint_wrappers=1 /private/tmp/sentinel-single-take.XXXXXX/single-take.mov
```

Expected: one video stream and approximately 90 seconds of continuous footage.

- [ ] **Step 2: Create transparent caption images**

Use Pillow with Arial Bold to create transparent 1920×1080 PNGs for these exact
captions:

```text
SENTINEL · A policy-driven AI portfolio agent · Built with Binance Agent OS
One request. The Agent plans the workflow.
The LLM chooses controlled tools. Binance Agent OS supplies fresh data.
LLM judges. Python calculates and validates.
A recommendation is not permission. Every order requires explicit approval.
Execution is verified after approval. Binance Demo · FILLED
AI understands. Policy protects. You stay in control. · github.com/pmjnt/sentinel-agent
```

Place each caption near the lower edge in a high-contrast rounded box without
covering the current application controls.

- [ ] **Step 3: Encode once from the continuous MOV**

Use one FFmpeg invocation with the MOV as input zero and the caption PNGs as
looped inputs. Scale and pad the base video, then chain `overlay` filters with
`enable='between(t,start,end)'` expressions derived from the observed source
timeline. Encode directly to:

```text
artifacts/demo/sentinel-track-a-demo.mp4
```

Required output settings:

```text
1920×1080 · 30 fps · H.264 · CRF 20 · yuv420p · no audio
```

The filter graph must not contain `concat`, `setpts`, `trim`, `tpad`, or a speed
change. The final duration must be at most the continuous source duration and no
more than 90 seconds.

- [ ] **Step 4: Generate the thumbnail**

Extract one frame from the pending-plan interval into:

```text
artifacts/demo/sentinel-track-a-thumbnail.jpg
```

### Task 4: Verify the Replacement

- [ ] **Step 1: Verify technical properties**

Run:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate -show_entries format=duration,size -of default=noprint_wrappers=1 artifacts/demo/sentinel-track-a-demo.mp4
```

Expected: H.264, 1920×1080, yuv420p, 30 fps, and duration no longer than 90
seconds.

- [ ] **Step 2: Verify continuity visually**

Inspect frames every ten seconds and watch the final MP4 from beginning to end.
Confirm the cursor, scroll position, Agent Pulse, response, evidence, approval,
and FILLED state progress continuously without a cut, jump, repeated frame, or
reordered event.

- [ ] **Step 3: Verify safety and repository state**

Confirm there is no terminal, credential, notification, unrelated app, or
production-account data in any inspected frame. Run:

```bash
git status --short
git check-ignore -v artifacts/demo/sentinel-track-a-demo.mp4 artifacts/demo/sentinel-track-a-thumbnail.jpg
git diff --check
```

Expected: working tree clean, generated media ignored, and diff check empty.
