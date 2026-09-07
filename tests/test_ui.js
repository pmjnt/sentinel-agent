const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const {
  buildChatRequest,
  buildPlanActionRequest,
  createSseParser,
  formatActivityLabel,
  isValidPrompt,
  parseInlineMarkdown,
  parseMarkdownBlocks,
  reduceActivity,
} = require("../web/app.js");

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

  assert.match(html, /id="model-trigger"/);
  assert.match(html, /id="model-menu"/);
  assert.match(html, /id="chat-thread"/);
  assert.match(html, /id="chat-composer"/);
  assert.doesNotMatch(html, /desk-grid|Analysis Request|Tool Evidence/);
});

test("user turns do not render a redundant You label", () => {
  const script = readFileSync(join(__dirname, "../web/app.js"), "utf8");
  assert.doesNotMatch(script, /speaker\.textContent = "You"/);
  assert.match(script, /Verified tool facts/);
  assert.match(script, /document\.createElement\("details"\)/);
  assert.match(script, /if \(result\.analysis\) renderEvidence\(turn, result\)/);
  assert.match(script, /Approve Demo order/);
  assert.match(script, /Reject/);
});
