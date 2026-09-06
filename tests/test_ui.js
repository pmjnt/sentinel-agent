const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const {
  buildChatRequest,
  createSseParser,
  formatActivityLabel,
  isValidPrompt,
} = require("../web/app.js");

test("accepts meaningful prompts and rejects whitespace", () => {
  assert.equal(isValidPrompt("Analyze my BTC exposure."), true);
  assert.equal(isValidPrompt("   \n  "), false);
});

test("builds a normalized chat request", () => {
  assert.deepEqual(buildChatRequest(" user-1 ", " Analyze. "), {
    session_id: "user-1",
    message: "Analyze.",
  });
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
