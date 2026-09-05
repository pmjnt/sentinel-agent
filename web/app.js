function isValidPrompt(prompt) {
  return typeof prompt === "string" && prompt.trim().length > 0;
}

function buildChatRequest(sessionId, message) {
  return { session_id: sessionId.trim(), message: message.trim() };
}

function createSseParser(onEvent) {
  let buffer = "";
  return {
    push(chunk) {
      buffer += chunk.replaceAll("\r\n", "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const lines = block.split("\n");
        const eventLine = lines.find((line) => line.startsWith("event:"));
        const dataLines = lines.filter((line) => line.startsWith("data:"));
        if (eventLine && dataLines.length) {
          const event = eventLine.slice(6).trim();
          const rawData = dataLines.map((line) => line.slice(5).trim()).join("\n");
          onEvent(event, JSON.parse(rawData));
        }
        boundary = buffer.indexOf("\n\n");
      }
    },
  };
}

function formatActivityLabel(activity) {
  return activity.message;
}

function formatMoney(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function initializeApp() {
  const form = document.querySelector("#analysis-form");
  const providerSelect = document.querySelector("#provider");
  const modelSelect = document.querySelector("#model");
  const promptInput = document.querySelector("#prompt");
  const promptError = document.querySelector("#prompt-error");
  const runButton = document.querySelector("#run-button");
  const runButtonLabel = document.querySelector("#run-button-label");
  const runId = document.querySelector("#run-id");
  const runRoute = document.querySelector("#run-route");
  const chatLog = document.querySelector("#chat-log");
  const activityLog = document.querySelector("#activity-log");
  const emptyActivity = document.querySelector("#empty-activity");
  const evidenceSection = document.querySelector("#evidence-section");
  const portfolioEvidence = document.querySelector("#portfolio-evidence");
  const marketEvidence = document.querySelector("#market-evidence");
  const profileEvidence = document.querySelector("#profile-evidence");
  const policyEvidence = document.querySelector("#policy-evidence");
  const portfolioData = document.querySelector("#portfolio-data");
  const marketData = document.querySelector("#market-data");
  const profileData = document.querySelector("#profile-data");
  const policyData = document.querySelector("#policy-data");
  const reportSection = document.querySelector("#report-section");
  const factList = document.querySelector("#fact-list");
  const interpretationText = document.querySelector("#interpretation-text");
  const liveStatus = document.querySelector("#live-status");
  const sessionId = getSessionId();

  function getSessionId() {
    const stored = window.sessionStorage.getItem("sentinel-session-id");
    if (stored) return stored;
    const created = window.crypto.randomUUID();
    window.sessionStorage.setItem("sentinel-session-id", created);
    return created;
  }

  function addChatMessage(role, text) {
    const item = document.createElement("li");
    item.className = `chat-message ${role}`;
    const label = document.createElement("strong");
    label.textContent = role === "user" ? "You" : "Sentinel";
    const content = document.createElement("p");
    content.textContent = text;
    item.append(label, content);
    chatLog.append(item);
    chatLog.scrollTop = chatLog.scrollHeight;
    return content;
  }

  function resetRun() {
    activityLog.replaceChildren();
    emptyActivity.hidden = true;
    evidenceSection.hidden = true;
    portfolioEvidence.hidden = true;
    marketEvidence.hidden = true;
    profileEvidence.hidden = true;
    policyEvidence.hidden = true;
    reportSection.hidden = true;
    portfolioData.replaceChildren();
    marketData.replaceChildren();
    profileData.replaceChildren();
    policyData.replaceChildren();
    factList.replaceChildren();
    interpretationText.textContent = "";
  }

  function renderActivity(activity) {
    const item = document.createElement("li");
    item.className = `activity-item ${activity.status.toLowerCase()}`;
    const label = document.createElement("span");
    label.textContent = formatActivityLabel(activity);
    const state = document.createElement("span");
    state.className = "activity-state";
    state.textContent = activity.status;
    item.append(label, state);
    activityLog.append(item);
    liveStatus.textContent = activity.message;
  }

  function appendDataRow(container, label, value, className = "") {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    if (className) detail.className = className;
    row.append(term, detail);
    container.append(row);
  }

  function renderCompleted(result, assistantContent) {
    const analysis = result.analysis;
    assistantContent.textContent = result.ai_interpretation || result.message;

    const hasSavedProfile = Object.entries(result.profile).some(([field, value]) => {
      if (field === "excluded_assets") return Array.isArray(value) && value.length > 0;
      return value != null;
    });
    const profileWasRequested = result.activity.some((activity) =>
      activity.kind === "PROFILE_UPDATE" || activity.kind === "PROFILE_VIEW"
    );
    profileEvidence.hidden = !(hasSavedProfile || profileWasRequested);
    const profileRows = [
      ["Objective", result.profile.objective],
      ["Time horizon", result.profile.time_horizon_months == null ? null : `${result.profile.time_horizon_months} months`],
      ["Risk tolerance", result.profile.risk_tolerance],
      ["Acceptable loss", result.profile.acceptable_loss_percent == null ? null : `${result.profile.acceptable_loss_percent}%`],
      ["Liquidity need", result.profile.liquidity_need],
      ["Excluded assets", result.profile.excluded_assets?.join(", ") || null],
    ];
    profileRows.forEach(([label, value]) => {
      appendDataRow(profileData, label, value ?? "Not specified");
    });

    const policyWasRequested = result.activity.some((activity) =>
      activity.kind === "POLICY_UPDATE" || activity.kind === "POLICY_VIEW"
    );
    const hasPolicy = result.policy.min_stablecoin_weight != null
      || result.policy.max_asset_weight != null
      || result.policy.block_high_volatility
      || result.policy.max_trade_usd_without_approval != null;
    policyEvidence.hidden = !(analysis || hasPolicy || policyWasRequested);
    const percentage = (value) => value == null
      ? "Not configured"
      : `${(Number(value) * 100).toFixed(2)}%`;
    appendDataRow(policyData, "Minimum stablecoin", percentage(result.policy.min_stablecoin_weight));
    appendDataRow(policyData, "Maximum per asset", percentage(result.policy.max_asset_weight));
    appendDataRow(policyData, "High volatility", result.policy.block_high_volatility ? "BLOCK" : "Allowed");
    appendDataRow(
      policyData,
      "Approval threshold",
      result.policy.max_trade_usd_without_approval == null
        ? "Not configured"
        : formatMoney(result.policy.max_trade_usd_without_approval),
    );

    if (!analysis) {
      evidenceSection.hidden = profileEvidence.hidden && policyEvidence.hidden;
      return;
    }

    evidenceSection.hidden = false;
    portfolioEvidence.hidden = false;
    analysis.portfolio.assets.forEach((asset) => {
      appendDataRow(
        portfolioData,
        asset.symbol,
        `${formatMoney(asset.usd_value)} · ${(Number(asset.weight) * 100).toFixed(2)}%`,
      );
    });
    appendDataRow(
      portfolioData,
      "Total portfolio",
      formatMoney(analysis.portfolio.total_usd_value),
    );

    if (analysis.market_data.length) {
      marketEvidence.hidden = false;
      analysis.market_data.forEach((market) => {
        appendDataRow(
          marketData,
          market.symbol,
          `${formatMoney(market.price)} · ${market.change_24h_percent}% · ${market.volatility}`,
          market.volatility === "HIGH" ? "risk-high" : "",
        );
      });
    }

    const facts = [
      `Portfolio total: ${formatMoney(analysis.portfolio.total_usd_value)}.`,
      `Policy violations: ${analysis.violations.length}.`,
      `Risk decision: ${analysis.risk_decision.status}.`,
      `Execution: ${result.execution_status}.`,
    ];
    facts.forEach((fact) => {
      const item = document.createElement("li");
      item.textContent = fact;
      factList.append(item);
    });
    interpretationText.textContent = result.ai_interpretation || "No interpretation returned.";
    reportSection.hidden = false;
  }

  async function loadConfiguration() {
    const response = await window.fetch("/api/config");
    if (!response.ok) throw new Error("Configuration unavailable.");
    const config = await response.json();
    providerSelect.replaceChildren(new Option(config.provider, config.provider));
    modelSelect.replaceChildren(new Option(config.model, config.model));
    providerSelect.disabled = true;
    modelSelect.disabled = true;
    runRoute.textContent = `${config.provider} / ${config.model}`;
  }

  async function streamChat(message, assistantContent) {
    const response = await window.fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildChatRequest(sessionId, message)),
    });
    if (!response.ok || !response.body) throw new Error("Stream unavailable.");

    const parser = createSseParser((event, data) => {
      if (event === "activity") renderActivity(data);
      if (event === "text_delta") assistantContent.textContent += data.text;
      if (event === "completed") renderCompleted(data, assistantContent);
      if (event === "error") throw new Error(data.message);
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      parser.push(decoder.decode(value, { stream: true }));
    }
    parser.push(decoder.decode());
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!isValidPrompt(promptInput.value)) {
      promptError.hidden = false;
      promptInput.focus();
      return;
    }
    const message = promptInput.value.trim();
    promptError.hidden = true;
    resetRun();
    addChatMessage("user", message);
    const assistantContent = addChatMessage("assistant", "");
    promptInput.value = "";
    runButton.disabled = true;
    runButtonLabel.textContent = "Sentinel is working";
    runId.textContent = `SNT-${String(Date.now()).slice(-6)}`;
    try {
      await streamChat(message, assistantContent);
      liveStatus.textContent = "Sentinel response complete.";
    } catch (error) {
      assistantContent.textContent = error.message || "Sentinel could not complete the request.";
      liveStatus.textContent = assistantContent.textContent;
    } finally {
      runButton.disabled = false;
      runButtonLabel.textContent = "Send to Sentinel";
    }
  });

  promptInput.addEventListener("input", () => {
    if (isValidPrompt(promptInput.value)) promptError.hidden = true;
  });
  loadConfiguration().catch(() => {
    runRoute.textContent = "Configuration unavailable";
  });
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initializeApp);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    buildChatRequest,
    createSseParser,
    formatActivityLabel,
    isValidPrompt,
  };
}
