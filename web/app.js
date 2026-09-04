const MODEL_OPTIONS = Object.freeze({
  openai: Object.freeze(["gpt-5.6-luna", "gpt-5.4-mini"]),
  gemini: Object.freeze([
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
  ]),
});

function getModelsForProvider(provider) {
  return [...(MODEL_OPTIONS[provider] || [])];
}

function isValidPrompt(prompt) {
  return typeof prompt === "string" && prompt.trim().length > 0;
}

function getAgentModelRoute(provider, model) {
  return `litellm/${provider}/${model}`;
}

function getTierLabel(provider) {
  return provider === "gemini" ? "Free tier" : "";
}

function buildActivitySteps() {
  return [
    { id: "request", label: "Request received" },
    { id: "portfolio-required", label: "Portfolio data required" },
    { id: "portfolio-call", label: "Calling get_portfolio()" },
    { id: "portfolio-returned", label: "Portfolio tool returned data" },
    { id: "market-required", label: "BTC market context required" },
    { id: "market-call", label: 'Calling get_market_data("BTCUSDT")' },
    { id: "market-returned", label: "Market tool returned data" },
    { id: "interpretation", label: "Analyzing concentration risk" },
    { id: "report-ready", label: "Report ready" },
  ];
}

function initializeApp() {
  const form = document.querySelector("#analysis-form");
  const providerSelect = document.querySelector("#provider");
  const modelSelect = document.querySelector("#model");
  const tierMark = document.querySelector(".tier-mark");
  const promptInput = document.querySelector("#prompt");
  const promptError = document.querySelector("#prompt-error");
  const runButton = document.querySelector("#run-button");
  const runButtonLabel = document.querySelector("#run-button-label");
  const runId = document.querySelector("#run-id");
  const runRoute = document.querySelector("#run-route");
  const activityLog = document.querySelector("#activity-log");
  const emptyActivity = document.querySelector("#empty-activity");
  const evidenceSection = document.querySelector("#evidence-section");
  const portfolioEvidence = document.querySelector("#portfolio-evidence");
  const marketEvidence = document.querySelector("#market-evidence");
  const reportSection = document.querySelector("#report-section");
  const liveStatus = document.querySelector("#live-status");
  let timers = [];
  let runToken = 0;

  function renderModels() {
    modelSelect.replaceChildren();
    getModelsForProvider(providerSelect.value).forEach((model) => {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      modelSelect.append(option);
    });
    tierMark.textContent = getTierLabel(providerSelect.value);
    tierMark.hidden = tierMark.textContent === "";
    updateRoute();
  }

  function updateRoute() {
    const providerName = providerSelect.options[providerSelect.selectedIndex].text;
    runRoute.textContent = `${providerName} / ${modelSelect.value}`;
  }

  function clearSimulation() {
    timers.forEach(window.clearTimeout);
    timers = [];
    activityLog.replaceChildren();
    evidenceSection.hidden = true;
    portfolioEvidence.hidden = true;
    marketEvidence.hidden = true;
    reportSection.hidden = true;
  }

  function renderActivity(steps) {
    steps.forEach((step) => {
      const item = document.createElement("li");
      item.className = "activity-item";
      item.dataset.stepId = step.id;
      item.innerHTML = `<span>${step.label}</span><span class="activity-state">Pending</span>`;
      activityLog.append(item);
    });
  }

  function setStepState(index, state) {
    const item = activityLog.children[index];
    if (!item) return;
    item.classList.remove("active", "complete");
    item.classList.add(state);
    item.querySelector(".activity-state").textContent = state === "active" ? "Working" : "Done";
  }

  function revealForStep(stepId) {
    if (stepId === "portfolio-returned") {
      evidenceSection.hidden = false;
      portfolioEvidence.hidden = false;
    }
    if (stepId === "market-returned") {
      evidenceSection.hidden = false;
      marketEvidence.hidden = false;
    }
    if (stepId === "report-ready") {
      reportSection.hidden = false;
      reportSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function finishRun(token) {
    if (token !== runToken) return;
    runButton.disabled = false;
    runButtonLabel.textContent = "Run Again";
    liveStatus.textContent = "Analysis complete. Sentinel report is ready.";
  }

  function runSimulation() {
    runToken += 1;
    const token = runToken;
    const steps = buildActivitySteps();
    clearSimulation();
    emptyActivity.hidden = true;
    renderActivity(steps);
    runButton.disabled = true;
    runButtonLabel.textContent = "Analysis in Progress";
    runId.textContent = `SNT-${String(Date.now()).slice(-6)}`;
    updateRoute();
    liveStatus.textContent = "Analysis started.";

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const interval = reducedMotion ? 90 : 430;

    steps.forEach((step, index) => {
      timers.push(window.setTimeout(() => {
        if (token !== runToken) return;
        if (index > 0) setStepState(index - 1, "complete");
        setStepState(index, "active");
        revealForStep(step.id);
        liveStatus.textContent = step.label;

        if (index === steps.length - 1) {
          timers.push(window.setTimeout(() => {
            setStepState(index, "complete");
            finishRun(token);
          }, interval));
        }
      }, index * interval));
    });
  }

  providerSelect.addEventListener("change", renderModels);
  modelSelect.addEventListener("change", updateRoute);
  promptInput.addEventListener("input", () => {
    if (isValidPrompt(promptInput.value)) promptError.hidden = true;
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!isValidPrompt(promptInput.value)) {
      promptError.hidden = false;
      promptInput.focus();
      liveStatus.textContent = "Please enter an analysis request.";
      return;
    }
    promptError.hidden = true;
    runSimulation();
  });

  renderModels();
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initializeApp);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    buildActivitySteps,
    getAgentModelRoute,
    getModelsForProvider,
    getTierLabel,
    isValidPrompt,
  };
}
