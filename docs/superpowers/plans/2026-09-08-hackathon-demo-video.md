# Sentinel Hackathon Demo Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and verify an 85–90 second English-captioned MP4 that demonstrates Sentinel's complete Binance Agent OS Track A workflow through Binance Demo execution.

**Architecture:** Run the existing FastAPI application with Demo execution enabled only for the recording process, drive the chat UI in a dedicated browser window, and capture the story as several short truthful screen-recording clips. Captions are temporary DOM overlays visible only during capture; FFmpeg normalizes and concatenates the clips without fabricating application states.

**Tech Stack:** Python 3.12, FastAPI/Uvicorn, Sentinel web UI, Binance Demo Trading, Binance Skills Hub `binance-cli`, macOS `screencapture`, in-app browser automation, FFmpeg 8.

---

## File Map

- Modify: `.gitignore` — keep generated MOV/MP4 media out of Git history.
- Read: `docs/superpowers/specs/2026-09-08-hackathon-demo-video-design.md` — approved storyboard and safety rules.
- Create locally, ignored: `artifacts/demo/sentinel-track-a-demo.mp4` — final deliverable.
- Create locally, ignored: `artifacts/demo/sentinel-track-a-thumbnail.png` — representative frame when time permits.
- Create temporarily: `/private/tmp/sentinel-demo-*/` — raw and normalized clips.
- Create: `docs/hackathon-submission.md` — concise English submission copy and demo checklist after the video is verified.

### Task 1: Protect Generated Media and Verify the Baseline

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add generated media exclusions**

Append these exact entries to `.gitignore`:

```gitignore
# Locally rendered hackathon media
artifacts/demo/*.mov
artifacts/demo/*.mp4
artifacts/demo/*.png
```

- [ ] **Step 2: Verify the ignore rules**

Run:

```bash
mkdir -p artifacts/demo
touch artifacts/demo/sentinel-track-a-demo.mp4
git check-ignore -v artifacts/demo/sentinel-track-a-demo.mp4
```

Expected: output points to the new `.gitignore` rule.

- [ ] **Step 3: Run the existing automated baseline**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
git diff --check
```

Expected: 294 Python tests pass, 14 UI tests pass, compile exits zero, and
`git diff --check` prints nothing.

- [ ] **Step 4: Commit the media-safety rule**

```bash
git add .gitignore
git commit -m "chore: ignore generated demo media"
```

### Task 2: Preflight the Recording Environment

**Files:**
- Read: `.env`
- Read: `.env.example`
- Read: `app/config.py`

- [ ] **Step 1: Check configuration without printing secrets**

Run:

```bash
.venv/bin/python -c "from dotenv import dotenv_values; c=dotenv_values('.env'); print({'provider':c.get('LLM_PROVIDER'),'model':c.get('LLM_MODEL'),'binance_env':c.get('BINANCE_API_ENV'),'openai_key':bool(c.get('OPENAI_API_KEY')),'gemini_key':bool(c.get('GEMINI_API_KEY')),'binance_key':bool(c.get('BINANCE_API_KEY')),'binance_secret':bool(c.get('BINANCE_SECRET_KEY'))})"
```

Expected: `binance_env` is `demo`; the selected provider's key, Binance key, and
Binance secret are `True`. No credential value is printed.

- [ ] **Step 2: Check required binaries**

Run:

```bash
binance-cli --version
ffmpeg -version
screencapture -h
```

Expected: Binance CLI reports the project-supported version, FFmpeg reports 8.x,
and `screencapture` prints its usage including video capture support.

- [ ] **Step 3: Create a private temporary capture directory**

Run:

```bash
mktemp -d /private/tmp/sentinel-demo.XXXXXX
```

Expected: one new path beginning with `/private/tmp/sentinel-demo.`. Preserve
that exact returned path for every raw clip command in this run.

- [ ] **Step 4: Start the recording-only backend**

Run in a continuing terminal session:

```bash
SENTINEL_DEMO_EXECUTION_ENABLED=true .venv/bin/uvicorn app.api:create_app --factory --host 127.0.0.1 --port 8000
```

Expected: Uvicorn listens on `http://127.0.0.1:8000`. The environment override
applies only to this process and does not modify `.env`.

- [ ] **Step 5: Verify the local API**

Run:

```bash
curl -sS --max-time 10 http://127.0.0.1:8000/api/models
```

Expected: HTTP response contains the configured allowed model route and no API
key or Binance credential.

### Task 3: Rehearse the Full Agent Workflow

**Files:**
- Read: `docs/superpowers/specs/2026-09-08-hackathon-demo-video-design.md`

- [ ] **Step 1: Open a dedicated browser window**

Open `http://127.0.0.1:8000`, use a fresh Sentinel session, hide unrelated tabs
and notifications, and size the application to a clean 16:9 composition. Do not
open developer tools, `.env`, terminal logs, or browser storage during capture.

- [ ] **Step 2: Submit the exact approved prompt**

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

- [ ] **Step 3: Verify the observable Agent loop**

Expand Agent Pulse and confirm that the real activity includes portfolio reading,
research planning, top-volume scanning, candidate-history analysis, research
finalization, risk evaluation, and proposal creation. Do not require a fixed
candidate symbol because the scan uses fresh Binance data.

- [ ] **Step 4: Verify evidence and recommendation quality**

Confirm the response shows Binance Demo portfolio facts, scanned candidates,
observation time, deterministic indicators, a comparison, Sentinel's preferred
asset with reasoning, formal Risk Engine status, and a 50 USDT immutable plan.

- [ ] **Step 5: Exercise the correct approval path**

If the chosen symbol is outside the default allowlist, click the separate
plan-scoped symbol approval first. Then click the dedicated Demo order approval.
Do not type approval into chat.

- [ ] **Step 6: Verify execution truthfully**

Confirm the UI reports `EXECUTED`/`FILLED` only after Binance Demo confirmation
and displays post-order portfolio verification. If required data, approval, or
execution fails, diagnose the run and repeat rehearsal in a fresh session; never
edit a failed run to look successful.

### Task 4: Capture the Story as Short Clips

**Files:**
- Create temporarily: `/private/tmp/sentinel-demo-*/01-title.mov`
- Create temporarily: `/private/tmp/sentinel-demo-*/02-request.mov`
- Create temporarily: `/private/tmp/sentinel-demo-*/03-agent-loop.mov`
- Create temporarily: `/private/tmp/sentinel-demo-*/04-evidence.mov`
- Create temporarily: `/private/tmp/sentinel-demo-*/05-approval.mov`
- Create temporarily: `/private/tmp/sentinel-demo-*/06-verification.mov`
- Create temporarily: `/private/tmp/sentinel-demo-*/07-closing.mov`

- [ ] **Step 1: Add a temporary caption overlay to the browser DOM**

For each clip, inject one fixed bottom caption element into the current page. Use
this visual contract: maximum two short lines, centered, 24–30 px sans-serif,
white text, translucent near-black background, 12 px vertical padding, rounded
corners, and no overlap with Agent Pulse, verified facts, plan controls, or order
status. Remove or replace the element between clips. This DOM-only change must
not be committed to the application.

- [ ] **Step 2: Record the five-second identity clip**

Display:

```text
SENTINEL
A policy-driven AI portfolio agent · Built with Binance Agent OS
```

Record the main display for five seconds with macOS `screencapture`, saving the
result as `01-title.mov` in the preserved temporary directory.

- [ ] **Step 3: Record the ten-second request clip**

Use a fresh session, paste the approved prompt, display `One request. The Agent
plans the workflow.`, and record submission as `02-request.mov`.

- [ ] **Step 4: Record up to 25 seconds of live Agent activity**

Immediately expand Agent Pulse. Record real streaming activity as
`03-agent-loop.mov`, using these captions in sequence:

```text
The LLM chooses controlled tools.
Binance Agent OS supplies fresh data.
```

Stop this clip after 25 seconds even if the run continues. Wait off-camera for
the run to finish; this removes dead waiting time without changing event order.

- [ ] **Step 5: Record the evidence clip**

After successful completion, record 20–22 seconds while deliberately scrolling
through verified research, candidate comparisons, Sentinel's preference, Risk
Engine status, and the trade plan. Display:

```text
LLM judges. Python calculates and validates.
```

Save as `04-evidence.mov`.

- [ ] **Step 6: Record the approval clip**

Record 10–12 seconds as `05-approval.mov`. Show any required plan-scoped token
approval, then click the dedicated order approval. Display:

```text
A recommendation is not permission.
Every order requires explicit approval.
```

- [ ] **Step 7: Record execution verification**

After Binance Demo confirms the order and the portfolio refresh completes,
record `EXECUTED`/`FILLED` and post-order verification for 7–9 seconds as
`06-verification.mov`. Do not record a success clip if Binance has not confirmed
the order.

- [ ] **Step 8: Record the closing clip**

Display the following for five seconds and save as `07-closing.mov`:

```text
AI understands. Policy protects. You stay in control.
github.com/pmjnt/sentinel-agent
```

### Task 5: Normalize, Assemble, and Verify the MP4

**Files:**
- Create temporarily: normalized MP4 clips and `clips.ffconcat`
- Create locally, ignored: `artifacts/demo/sentinel-track-a-demo.mp4`
- Create locally, ignored: `artifacts/demo/sentinel-track-a-thumbnail.png`

- [ ] **Step 1: Normalize every clip**

For each numbered MOV, run FFmpeg with this video transform:

```text
scale=1920:1080:force_original_aspect_ratio=decrease,
pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,
fps=30,format=yuv420p
```

Encode with H.264 (`libx264`), `-preset medium`, `-crf 20`, no audio, and save
each normalized result beside its source using the same number and `.mp4`.

- [ ] **Step 2: Create the exact concat manifest**

Create `clips.ffconcat` in the temporary directory with the seven normalized
clip paths in numeric order and this header:

```text
ffconcat version 1.0
```

- [ ] **Step 3: Concatenate the normalized clips**

Run:

```bash
ffmpeg -f concat -safe 0 -i clips.ffconcat -c copy -movflags +faststart artifacts/demo/sentinel-track-a-demo.mp4
```

Run from a working directory where `clips.ffconcat` resolves to the manifest and
the output resolves to the repository's `artifacts/demo` directory.

- [ ] **Step 4: Measure the final media**

Run:

```bash
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt -of json artifacts/demo/sentinel-track-a-demo.mp4
```

Expected: H.264, 1920×1080, 30 fps, `yuv420p`, duration no longer than 90
seconds, and a non-zero file size.

- [ ] **Step 5: Render a thumbnail**

Run:

```bash
ffmpeg -ss 00:00:45 -i artifacts/demo/sentinel-track-a-demo.mp4 -frames:v 1 artifacts/demo/sentinel-track-a-thumbnail.png
```

Expected: a 1920×1080 PNG showing verified evidence or Sentinel's preferred
candidate, with no credential or private notification visible.

- [ ] **Step 6: Perform visual QA**

Watch the final MP4 from start to end. Confirm captions are readable, cuts keep
the true event order, all required sections are visible, the closing URL is
correct, there are no exposed secrets or personal notifications, and success is
shown only after Binance Demo confirmation.

### Task 6: Prepare and Publish the Submission Materials

**Files:**
- Create: `docs/hackathon-submission.md`

- [ ] **Step 1: Write the English submission copy**

Create `docs/hackathon-submission.md` containing:

```markdown
# Binance Agent OS Mini Hackathon — Track A Submission

Meet Sentinel: a policy-driven AI portfolio agent built with Binance Agent OS
and the official Binance Skills Hub CLI.

Sentinel turns a natural-language goal into a controlled workflow: it reads a
Binance Demo portfolio, scans high-volume Spot markets, investigates fresh
market history, explains its own evidence-grounded preference, validates every
proposal with deterministic Python and a Risk Engine, then requires explicit
human approval before Demo execution.

AI understands. Policy protects. You stay in control.

GitHub: https://github.com/pmjnt/sentinel-agent

Demo: attach `artifacts/demo/sentinel-track-a-demo.mp4` to the Track A reply or
quote-repost.
```

- [ ] **Step 2: Verify the repository remains secret-free and clean**

Run:

```bash
git status --short
git check-ignore -v artifacts/demo/sentinel-track-a-demo.mp4
git diff --check
```

Expected: generated media is ignored; only the intended documentation and
`.gitignore` changes appear before commit.

- [ ] **Step 3: Re-run the full automated suite**

Run:

```bash
.venv/bin/python -m pytest -q
node --test tests/test_ui.js
.venv/bin/python -m compileall -q app main.py tests
```

Expected: 294 Python tests and 14 UI tests pass; compile exits zero.

- [ ] **Step 4: Commit the submission document**

```bash
git add docs/hackathon-submission.md
git commit -m "docs: add Track A submission copy"
```

- [ ] **Step 5: Push the documentation commits**

```bash
git push origin main
```

Expected: GitHub `main` contains the approved video design, implementation plan,
media ignore rules, and submission copy. The generated MP4 remains local for
upload to the campaign post rather than bloating Git history.

- [ ] **Step 6: Hand off the verified deliverables**

Report the absolute MP4 and thumbnail paths, duration, codec, dimensions, file
size, final Git commit, and public GitHub URL. Remind the user that only they can
complete the required Binance survey and publish the X reply/quote-repost.

