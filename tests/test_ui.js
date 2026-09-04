const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildActivitySteps,
  getAgentModelRoute,
  getModelsForProvider,
  isValidPrompt,
} = require("../web/app.js");

test("returns the supported OpenAI models", () => {
  assert.deepEqual(getModelsForProvider("openai"), [
    "gpt-5.6-luna",
    "gpt-5.4-mini",
  ]);
});

test("returns the supported Gemini models", () => {
  assert.deepEqual(getModelsForProvider("gemini"), [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
  ]);
});

test("builds the LiteLLM route passed to the Agents SDK", () => {
  assert.equal(
    getAgentModelRoute("gemini", "gemini-3.5-flash-lite"),
    "litellm/gemini/gemini-3.5-flash-lite",
  );
});

test("accepts meaningful prompts and rejects whitespace", () => {
  assert.equal(isValidPrompt("Analyze my BTC exposure."), true);
  assert.equal(isValidPrompt("   \n  "), false);
});

test("activity calls portfolio before market data and finishes with a report", () => {
  const labels = buildActivitySteps().map((step) => step.label);
  const portfolioIndex = labels.indexOf("Calling get_portfolio()");
  const marketIndex = labels.indexOf('Calling get_market_data("BTCUSDT")');

  assert.ok(portfolioIndex >= 0);
  assert.ok(marketIndex > portfolioIndex);
  assert.equal(labels.at(-1), "Report ready");
});
