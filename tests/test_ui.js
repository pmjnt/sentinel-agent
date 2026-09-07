const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const {
  buildChatRequest,
  buildPlanActionRequest,
  buildResearchEvidenceRows,
  createSseParser,
  formatActivityLabel,
  getPlanApprovalPresentation,
  isValidPrompt,
  parseInlineMarkdown,
  parseMarkdownBlocks,
  reduceActivity,
} = require("../web/app.js");

test("builds compact verified research rows without raw candles", () => {
  const rows = buildResearchEvidenceRows({
    plan: {
      candidate_limit: 3,
      timeframes: ["1h"],
      lookback_days: 1,
      priorities: ["MOMENTUM"],
    },
    scan: {
      observed_at: "2026-09-07T00:00:00Z",
      candidates: [
        { symbol: "BTCUSDT", quote_volume: "1000000" },
        { symbol: "ETHUSDT", quote_volume: "900000" },
      ],
    },
    analyzed_candidates: [
      {
        candidate: { symbol: "BTCUSDT" },
        timeframes: [{
          timeframe: "1h",
          return_percent: "5",
          trend: "BULLISH",
          realized_volatility_percent: "1.2",
          max_drawdown_percent: "3",
          volume_change_percent: "8",
        }],
      },
    ],
    failed_symbols: ["SOLUSDT"],
  });

  assert.deepEqual(rows.map((row) => row.label), [
    "Research plan",
    "Market scan",
    "Top volume",
    "BTCUSDT · 1h",
    "Unavailable history",
  ]);
  assert.match(rows[3].value, /return 5% · trend BULLISH/);
  assert.doesNotMatch(JSON.stringify(rows), /open_time|close_time|candles/);
});

test("plan actions use a dedicated endpoint and exact session", () => {
  assert.deepEqual(
    buildPlanActionRequest(" user-1 ", "PLAN-ABC123", "approve"),
    {
      url: "/api/plans/PLAN-ABC123/approve",
      options: {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: "user-1" }),
      },
    },
  );
  assert.throws(
    () => buildPlanActionRequest("user-1", "PLAN-ABC123", "execute"),
    /Unsupported plan action/,
  );
  assert.equal(
    buildPlanActionRequest("user-1", "PLAN-ABC123", "approve-symbol").url,
    "/api/plans/PLAN-ABC123/approve-symbol",
  );
});

test("non-default symbols require token approval before order approval", () => {
  assert.deepEqual(getPlanApprovalPresentation("PENDING_SYMBOL_APPROVAL"), {
    eyebrow: "TOKEN OUTSIDE DEFAULT UNIVERSE",
    button: "Approve token exception",
    action: "approve-symbol",
  });
  assert.deepEqual(getPlanApprovalPresentation("PENDING_APPROVAL"), {
    eyebrow: "BINANCE DEMO · EXPLICIT APPROVAL REQUIRED",
    button: "Approve Demo order",
    action: "approve",
  });
});

test("accepts meaningful prompts and rejects whitespace", () => {
  assert.equal(isValidPrompt("Analyze my BTC exposure."), true);
  assert.equal(isValidPrompt("   \n  "), false);
});

test("chat request includes the selected validated route", () => {
  assert.deepEqual(
    buildChatRequest(" user-1 ", " Analyze. ", {
      provider: "gemini",
      model: "gemini-3.5-flash-lite",
    }),
    {
      session_id: "user-1",
      message: "Analyze.",
      provider: "gemini",
      model: "gemini-3.5-flash-lite",
    },
  );
});

test("activity reducer completes the matching step without adding a row", () => {
  const started = reduceActivity([], {
    sequence: 1,
    kind: "PORTFOLIO_READ",
    status: "STARTED",
    message: "Started portfolio retrieval.",
  });
  const completed = reduceActivity(started, {
    sequence: 2,
    kind: "PORTFOLIO_READ",
    status: "COMPLETED",
    message: "Completed portfolio retrieval.",
  });

  assert.equal(completed.length, 1);
  assert.equal(completed[0].status, "COMPLETED");
  assert.equal(started[0].status, "STARTED");
});

test("parses headings, bullet lists, and paragraphs for safe rendering", () => {
  assert.deepEqual(
    parseMarkdownBlocks("## Đánh giá\nNội dung.\n\n- Một\n- Hai"),
    [
      { type: "heading", level: 2, text: "Đánh giá" },
      { type: "paragraph", text: "Nội dung." },
      { type: "list", items: ["Một", "Hai"] },
    ],
  );
});

test("splits inline numbered choices into an ordered list", () => {
  assert.deepEqual(
    parseMarkdownBlocks(
      "So sánh nhanh: 1. ETH: cân bằng 2. BTC: an toàn 3. SOL: biến động",
    ),
    [
      { type: "paragraph", text: "So sánh nhanh:" },
      {
        type: "ordered-list",
        items: [
          "ETH: cân bằng",
          "BTC: an toàn",
          "SOL: biến động",
        ],
      },
    ],
  );
});

test("keeps decimal values as paragraph text", () => {
  assert.deepEqual(
    parseMarkdownBlocks("Lợi nhuận 1.5% trong 2.5 năm."),
    [{ type: "paragraph", text: "Lợi nhuận 1.5% trong 2.5 năm." }],
  );
});

test("parses inline bold markers without using HTML", () => {
  assert.deepEqual(parseInlineMarkdown("Tổng: **9,999 USDT**."), [
    { type: "text", text: "Tổng: " },
    { type: "strong", text: "9,999 USDT" },
    { type: "text", text: "." },
  ]);
});

test("parses SSE events across network chunks", () => {
  const events = [];
  const parser = createSseParser((event, data) => events.push({ event, data }));

  parser.push('event: activity\ndata: {"status":"STAR');
  parser.push('TED"}\n\nevent: text_delta\ndata: {"text":"Hi"}\n\n');

  assert.deepEqual(events, [
    { event: "activity", data: { status: "STARTED" } },
    { event: "text_delta", data: { text: "Hi" } },
  ]);
});

test("formats backend activity without exposing implementation data", () => {
  assert.equal(
    formatActivityLabel({
      kind: "PORTFOLIO_READ",
      status: "COMPLETED",
      message: "Completed portfolio retrieval.",
    }),
    "Completed portfolio retrieval.",
  );
});

test("page uses the chat-first Agent Pulse shell", () => {
  const html = readFileSync(join(__dirname, "../web/index.html"), "utf8");
  const styles = readFileSync(join(__dirname, "../web/styles.css"), "utf8");

  assert.match(html, /id="model-trigger"/);
  assert.match(html, /id="model-menu"/);
  assert.match(html, /id="chat-thread"/);
  assert.match(html, /id="chat-composer"/);
  assert.doesNotMatch(html, /desk-grid|Analysis Request|Tool Evidence/);
  assert.match(styles, /\.response-body ul,\s*\.response-body ol/);
});

test("user turns do not render a redundant You label", () => {
  const script = readFileSync(join(__dirname, "../web/app.js"), "utf8");
  assert.doesNotMatch(script, /speaker\.textContent = "You"/);
  assert.match(script, /Verified tool facts/);
  assert.match(script, /document\.createElement\("details"\)/);
  assert.match(script, /if \(result\.analysis \|\| result\.market_research\) renderEvidence\(turn, result\)/);
  assert.match(script, /Approve Demo order/);
  assert.match(script, /Reject/);
});
