function isValidPrompt(prompt) {
  return typeof prompt === "string" && prompt.trim().length > 0;
}

function buildChatRequest(sessionId, message, route) {
  return {
    session_id: sessionId.trim(),
    message: message.trim(),
    provider: route.provider,
    model: route.model,
  };
}

function reduceActivity(current, event) {
  const next = current.map((item) => ({ ...item }));
  if (event.status === "STARTED") return [...next, { ...event }];

  for (let index = next.length - 1; index >= 0; index -= 1) {
    if (next[index].kind === event.kind && next[index].status === "STARTED") {
      next[index] = { ...event };
      return next;
    }
  }
  return [...next, { ...event }];
}

function parseMarkdownBlocks(markdown) {
  const blocks = [];
  let paragraph = [];
  let listItems = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  };
  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: "list", items: listItems });
      listItems = [];
    }
  };

  String(markdown).replaceAll("\r\n", "\n").split("\n").forEach((line) => {
    const trimmed = line.trim();
    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    const bullet = /^[-*]\s+(.+)$/.exec(trimmed);

    if (!trimmed) {
      flushParagraph();
      flushList();
    } else if (heading) {
      flushParagraph();
      flushList();
      blocks.push({
        type: "heading",
        level: heading[1].length,
        text: heading[2],
      });
    } else if (bullet) {
      flushParagraph();
      listItems.push(bullet[1]);
    } else {
      flushList();
      paragraph.push(trimmed);
    }
  });
  flushParagraph();
  flushList();
  return blocks;
}

function parseInlineMarkdown(text) {
  const tokens = [];
  const pattern = /\*\*([^*]+)\*\*/g;
  let cursor = 0;
  let match = pattern.exec(text);
  while (match) {
    if (match.index > cursor) {
      tokens.push({ type: "text", text: text.slice(cursor, match.index) });
    }
    tokens.push({ type: "strong", text: match[1] });
    cursor = match.index + match[0].length;
    match = pattern.exec(text);
  }
  if (cursor < text.length) {
    tokens.push({ type: "text", text: text.slice(cursor) });
  }
  return tokens.length ? tokens : [{ type: "text", text }];
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

function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function initializeApp() {
  const modelTrigger = document.querySelector("#model-trigger");
  const activeModel = document.querySelector("#active-model");
  const modelMenu = document.querySelector("#model-menu");
  const chatThread = document.querySelector("#chat-thread");
  const form = document.querySelector("#chat-composer");
  const promptInput = document.querySelector("#prompt");
  const promptError = document.querySelector("#prompt-error");
  const sendButton = document.querySelector("#send-button");
  const liveStatus = document.querySelector("#live-status");
  const sessionId = getSessionId();
  let selectedRoute = null;
  let isRunning = false;

  function getSessionId() {
    const stored = window.sessionStorage.getItem("sentinel-session-id");
    if (stored) return stored;
    const created = window.crypto.randomUUID();
    window.sessionStorage.setItem("sentinel-session-id", created);
    return created;
  }

  function setModelMenu(open) {
    modelTrigger.setAttribute("aria-expanded", String(open));
    modelMenu.hidden = !open;
  }

  function routeKey(route) {
    return `${route.provider}/${route.model}`;
  }

  function chooseRoute(route) {
    selectedRoute = { provider: route.provider, model: route.model };
    activeModel.textContent = route.label || route.model;
    modelMenu.querySelectorAll(".model-option").forEach((option) => {
      const selected = option.dataset.route === routeKey(route);
      option.classList.toggle("selected", selected);
      option.setAttribute("aria-checked", String(selected));
    });
    setModelMenu(false);
  }

  function renderModelCatalog(catalog) {
    modelMenu.replaceChildren();
    catalog.models.forEach((route) => {
      const option = document.createElement("button");
      option.type = "button";
      option.className = "model-option";
      option.dataset.route = routeKey(route);
      option.setAttribute("role", "menuitemradio");
      option.setAttribute("aria-checked", "false");

      const label = document.createElement("span");
      label.textContent = route.label;
      const provider = document.createElement("span");
      provider.className = "model-option-provider";
      provider.textContent = route.provider;
      option.append(label, provider);
      option.addEventListener("click", () => chooseRoute(route));
      modelMenu.append(option);
    });
    chooseRoute(catalog.default);
    modelTrigger.disabled = false;
  }

  async function loadModelCatalog() {
    const response = await window.fetch("/api/models");
    if (!response.ok) throw new Error("Model list is unavailable.");
    renderModelCatalog(await response.json());
  }

  function addUserTurn(message) {
    const item = document.createElement("li");
    item.className = "turn user-turn";
    const content = document.createElement("div");
    content.className = "turn-content";
    const text = document.createElement("p");
    text.textContent = message;
    content.append(text);
    item.append(content);
    chatThread.append(item);
  }

  function createAssistantTurn(message, route) {
    const item = document.createElement("li");
    item.className = "turn assistant-turn";
    const speaker = document.createElement("div");
    speaker.className = "speaker";
    speaker.textContent = "Sentinel";
    const content = document.createElement("div");
    content.className = "turn-content";
    const response = document.createElement("div");
    response.className = "response-body";

    const pulse = document.createElement("div");
    pulse.className = "agent-pulse";
    const pulseButton = document.createElement("button");
    pulseButton.type = "button";
    pulseButton.className = "pulse-trigger";
    pulseButton.setAttribute("aria-expanded", "false");
    const dot = document.createElement("span");
    dot.className = "pulse-dot active";
    const pulseLabel = document.createElement("span");
    pulseLabel.className = "pulse-label";
    pulseLabel.textContent = "Preparing request…";
    const pulseCount = document.createElement("span");
    pulseCount.className = "pulse-count";
    const chevron = document.createElement("span");
    chevron.className = "pulse-chevron";
    chevron.setAttribute("aria-hidden", "true");
    pulseButton.append(dot, pulseLabel, pulseCount, chevron);

    const detail = document.createElement("div");
    detail.className = "pulse-detail";
    detail.hidden = true;
    const activityList = document.createElement("ol");
    activityList.className = "pulse-list";
    detail.append(activityList);
    pulse.append(pulseButton, detail);
    content.append(response, pulse);
    item.append(speaker, content);
    chatThread.append(item);

    pulseButton.addEventListener("click", () => {
      const open = pulseButton.getAttribute("aria-expanded") === "true";
      pulseButton.setAttribute("aria-expanded", String(!open));
      detail.hidden = open;
    });

    return {
      item,
      content,
      response,
      pulse,
      pulseLabel,
      pulseCount,
      pulseDot: dot,
      activityList,
      activities: [],
      completed: false,
      message,
      route: { ...route },
    };
  }

  function renderActivity(turn, activity) {
    turn.activities = reduceActivity(turn.activities, activity);
    turn.activityList.replaceChildren();
    turn.activities.forEach((step) => {
      const item = document.createElement("li");
      item.className = `pulse-item ${step.status.toLowerCase()}`;
      item.textContent = formatActivityLabel(step);
      turn.activityList.append(item);
    });
    turn.pulseLabel.textContent = activity.message;
    turn.pulseCount.textContent = `${turn.activities.length}`;
    turn.pulseDot.classList.toggle(
      "active",
      turn.activities.some((step) => step.status === "STARTED"),
    );
    liveStatus.textContent = activity.message;
  }

  function appendEvidence(list, label, value) {
    const item = document.createElement("li");
    const strong = document.createElement("strong");
    strong.textContent = `${label}: `;
    item.append(strong, document.createTextNode(value));
    list.append(item);
  }

  function renderMarkdown(container, markdown) {
    container.replaceChildren();
    const appendInline = (element, text) => {
      parseInlineMarkdown(text).forEach((token) => {
        if (token.type === "strong") {
          const strong = document.createElement("strong");
          strong.textContent = token.text;
          element.append(strong);
        } else {
          element.append(document.createTextNode(token.text));
        }
      });
    };
    parseMarkdownBlocks(markdown).forEach((block) => {
      if (block.type === "heading") {
        const heading = document.createElement(block.level <= 2 ? "h2" : "h3");
        appendInline(heading, block.text);
        container.append(heading);
      } else if (block.type === "list") {
        const list = document.createElement("ul");
        block.items.forEach((text) => {
          const item = document.createElement("li");
          appendInline(item, text);
          list.append(item);
        });
        container.append(list);
      } else {
        const paragraph = document.createElement("p");
        appendInline(paragraph, block.text);
        container.append(paragraph);
      }
    });
  }

  function renderEvidence(turn, result) {
    const analysis = result.analysis;
    const card = document.createElement("details");
    card.className = "evidence-card";
    const summary = document.createElement("summary");
    const title = document.createElement("span");
    title.className = "evidence-title";
    title.textContent = "Verified tool facts";
    const summaryHint = document.createElement("span");
    summaryHint.className = "evidence-hint";
    summaryHint.textContent = "Show";
    summary.append(title, summaryHint);
    const body = document.createElement("div");
    body.className = "evidence-body";
    const source = document.createElement("p");
    source.className = "evidence-source";
    source.textContent = "Binance Demo data checked by deterministic Python rules.";
    const list = document.createElement("ul");
    list.className = "evidence-list";

    appendEvidence(list, "Model", `${result.provider}/${result.model}`);
    if (analysis) {
      appendEvidence(list, "Portfolio", formatMoney(analysis.portfolio.total_usd_value));
      const allocations = analysis.portfolio.assets
        .map((asset) => `${asset.symbol} ${formatPercent(asset.weight)}`)
        .join(" · ");
      appendEvidence(list, "Allocation", allocations);
      appendEvidence(list, "Violations", String(analysis.violations.length));
      if (analysis.market_data.length) {
        const markets = analysis.market_data
          .map((market) => `${market.symbol} ${market.volatility}`)
          .join(" · ");
        appendEvidence(list, "Market", markets);
      }
      appendEvidence(list, "Risk Engine", analysis.risk_decision.status);
    }
    appendEvidence(list, "Execution", result.execution_status);
    body.append(source, list);
    card.append(summary, body);
    card.addEventListener("toggle", () => {
      summaryHint.textContent = card.open ? "Hide" : "Show";
    });
    turn.content.append(card);
  }

  function renderCompleted(turn, result) {
    turn.completed = true;
    renderMarkdown(turn.response, result.ai_interpretation || result.message);
    turn.pulseLabel.textContent = turn.activities.length
      ? "Agent activity complete"
      : "Response complete";
    turn.pulseCount.textContent = turn.activities.length
      ? `${turn.activities.length}`
      : "";
    turn.pulseDot.classList.remove("active");
    turn.pulseDot.style.background = "var(--green)";
    renderEvidence(turn, result);
  }

  function renderFailure(turn, message) {
    turn.response.textContent = message || "Sentinel could not complete the request.";
    turn.response.classList.add("turn-error");
    turn.pulseLabel.textContent = "Request failed";
    turn.pulseDot.classList.remove("active");
    turn.pulseDot.style.background = "var(--red)";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "retry-button";
    retry.textContent = "Retry";
    retry.addEventListener("click", () => {
      retry.remove();
      submitMessage(turn.message, turn.route);
    });
    turn.content.append(retry);
  }

  async function streamChat(turn) {
    const response = await window.fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildChatRequest(sessionId, turn.message, turn.route)),
    });
    if (!response.ok || !response.body) {
      let detail = "Unable to start the Sentinel stream.";
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (_) {
        // The safe generic message is enough when the server has no JSON body.
      }
      throw new Error(detail);
    }

    const parser = createSseParser((event, data) => {
      if (event === "activity") renderActivity(turn, data);
      if (event === "text_delta") turn.response.textContent += data.text;
      if (event === "completed") renderCompleted(turn, data);
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
    if (!turn.completed) throw new Error("Sentinel stream ended before completion.");
  }

  function scrollToTurn(turn) {
    turn.item.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function submitMessage(message, requestedRoute = selectedRoute) {
    if (isRunning || !requestedRoute) return;
    isRunning = true;
    sendButton.disabled = true;
    promptError.hidden = true;
    addUserTurn(message);
    const turn = createAssistantTurn(message, requestedRoute);
    scrollToTurn(turn);
    try {
      await streamChat(turn);
      liveStatus.textContent = "Sentinel response complete.";
    } catch (error) {
      renderFailure(turn, error.message);
      liveStatus.textContent = turn.response.textContent;
    } finally {
      isRunning = false;
      sendButton.disabled = false;
      promptInput.focus();
    }
  }

  function resizePrompt() {
    promptInput.style.height = "auto";
    promptInput.style.height = `${Math.min(promptInput.scrollHeight, 170)}px`;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!isValidPrompt(promptInput.value)) {
      promptError.hidden = false;
      promptInput.focus();
      return;
    }
    const message = promptInput.value.trim();
    promptInput.value = "";
    resizePrompt();
    submitMessage(message);
  });

  promptInput.addEventListener("input", () => {
    if (isValidPrompt(promptInput.value)) promptError.hidden = true;
    resizePrompt();
  });

  promptInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  modelTrigger.addEventListener("click", () => {
    setModelMenu(modelTrigger.getAttribute("aria-expanded") !== "true");
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".model-picker")) setModelMenu(false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setModelMenu(false);
  });

  loadModelCatalog().catch((error) => {
    activeModel.textContent = "Models unavailable";
    sendButton.disabled = true;
    liveStatus.textContent = error.message;
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
    parseInlineMarkdown,
    parseMarkdownBlocks,
    reduceActivity,
  };
}
