const ui = {
  clock: document.getElementById("clock"),
  dateLabel: document.getElementById("dateLabel"),
  assistantMode: document.getElementById("assistantMode"),
  chatTs: document.getElementById("chatTs"),
  heroTimestamp: document.getElementById("heroTimestamp"),
  activityList: document.getElementById("activityList"),
  chatWindow: document.getElementById("chatWindow"),
  chatInput: document.getElementById("chatInput"),
  sendBtn: document.getElementById("sendBtn"),
  voiceBtn: document.getElementById("voiceBtn"),
  clearBtn: document.getElementById("clearBtn"),
  taskList: document.getElementById("taskList"),
  queuedCount: document.getElementById("queuedCount"),
  commandButtons: document.querySelectorAll("[data-command]")
};

const metrics = {
  cpu: { value: 15, min: 6, max: 95, step: 7, suffix: "%", valueEl: "cpuValue", meterEl: "cpuMeter" },
  ram: { value: 35, min: 14, max: 92, step: 5, suffix: "%", valueEl: "ramValue", meterEl: "ramMeter" },
  network: { value: 320, min: 20, max: 980, step: 90, suffix: " KB/s", valueEl: "networkValue", meterEl: "networkMeter", scaleMax: 1000 },
  gpu: { value: 24, min: 0, max: 100, step: 8, suffix: "%", valueEl: "gpuValue", meterEl: "gpuMeter" },
  temp: { value: 46, min: 32, max: 86, step: 3, suffix: "°C", valueEl: "tempValue", meterEl: "tempMeter", scaleMax: 100 },
  battery: { value: 82, min: 25, max: 100, step: 2, suffix: "%", valueEl: "batteryValue", meterEl: "batteryMeter" }
};

const routineSets = [
  [
    "Analyze current project structure",
    "Monitor clipboard and voice triggers",
    "Prepare shell automation preview"
  ],
  [
    "Inspect dependency health and startup paths",
    "Watch recent command queue",
    "Stage screen analysis pipeline"
  ],
  [
    "Sync plugin manager status",
    "Assess UI responsiveness profile",
    "Queue developer-assistant context"
  ]
];

const activityFeed = [
  "Indexed command surfaces and runtime capabilities.",
  "System telemetry streams stabilized.",
  "Voice shortcut standing by for input capture.",
  "Project analysis pipeline cached for fast follow-up.",
  "Automation planner generated a dry-run sequence.",
  "UI layer refreshed with updated visual hierarchy."
];

const cannedReplies = [
  {
    test: /project|code|analy/i,
    reply: "I can inspect the repository, flag structure issues, and suggest targeted code changes. Point me at the part you want improved first."
  },
  {
    test: /battery|cpu|ram|resource|system/i,
    reply: "Current telemetry is nominal. CPU and memory are fluctuating within expected ranges, and I can surface a deeper process-level breakdown next."
  },
  {
    test: /automate|workflow|routine/i,
    reply: "Describe the workflow in plain language and I’ll convert it into a concrete automation plan with commands and guardrails."
  },
  {
    test: /screen|ocr|vision/i,
    reply: "Screen analysis is available. I can extract visible text, describe UI state, and help automate actions from what is on-screen."
  }
];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function randomStep(current, step, min, max) {
  const next = current + (Math.random() * step * 2 - step);
  return clamp(next, min, max);
}

function nowParts() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");

  return {
    stamp: `[${hh}:${mm}:${ss}]`,
    time: `${hh}:${mm}:${ss}`,
    date: now.toLocaleDateString(undefined, {
      month: "short",
      day: "2-digit",
      year: "numeric"
    })
  };
}

function updateClock() {
  const { stamp, time, date } = nowParts();
  ui.clock.textContent = time;
  ui.dateLabel.textContent = date;
  ui.chatTs.textContent = stamp;
  ui.heroTimestamp.textContent = stamp;
}

function renderMetrics() {
  Object.values(metrics).forEach((metric) => {
    const displayValue = Math.round(metric.value);
    const scaleMax = metric.scaleMax || 100;
    const width = clamp((displayValue / scaleMax) * 100, 0, 100);
    document.getElementById(metric.valueEl).textContent = `${displayValue}${metric.suffix}`;
    document.getElementById(metric.meterEl).style.width = `${width}%`;
  });
}

function tickMetrics() {
  Object.values(metrics).forEach((metric) => {
    metric.value = randomStep(metric.value, metric.step, metric.min, metric.max);
  });

  ui.assistantMode.textContent = metrics.cpu.value > 85 ? "High Load" : "Operational";
  renderMetrics();
}

function addActivity(message) {
  const { stamp } = nowParts();
  const item = document.createElement("article");
  item.className = "activity-item";
  item.innerHTML = `
    <span class="activity-time">${stamp}</span>
    <div>
      <strong>BenX</strong>
      <p>${message}</p>
    </div>
  `;

  ui.activityList.prepend(item);

  while (ui.activityList.children.length > 4) {
    ui.activityList.removeChild(ui.activityList.lastElementChild);
  }
}

function addChatMessage(role, text) {
  const { stamp } = nowParts();
  const item = document.createElement("article");
  item.className = `chat-message ${role}`;
  item.innerHTML = `
    <div class="message-meta">
      <strong>${role === "assistant" ? "BenX" : "You"}</strong>
      <span class="timestamp">${stamp}</span>
    </div>
    <p>${text}</p>
  `;

  ui.chatWindow.appendChild(item);
  ui.chatWindow.scrollTop = ui.chatWindow.scrollHeight;
}

function updateRoutineList() {
  const set = routineSets[Math.floor(Math.random() * routineSets.length)];
  ui.taskList.innerHTML = "";
  set.forEach((task) => {
    const item = document.createElement("li");
    item.textContent = task;
    ui.taskList.appendChild(item);
  });
  ui.queuedCount.textContent = `0${set.length}`.slice(-2);
}

function replyFor(message) {
  const match = cannedReplies.find((entry) => entry.test.test(message));
  return match
    ? match.reply
    : "Command acknowledged. I can expand that into a concrete action plan, inspect the codebase, or execute the next UI/system step you need.";
}

function submitMessage(message) {
  const trimmed = message.trim();
  if (!trimmed) return;

  addChatMessage("user", trimmed);
  addActivity(`Queued request: ${trimmed}`);
  ui.chatInput.value = "";

  window.setTimeout(() => {
    addChatMessage("assistant", replyFor(trimmed));
  }, 420);
}

ui.sendBtn.addEventListener("click", () => submitMessage(ui.chatInput.value));

ui.chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitMessage(ui.chatInput.value);
  }
});

ui.clearBtn.addEventListener("click", () => {
  ui.chatWindow.innerHTML = "";
  addChatMessage("assistant", "Conversation buffer cleared. Ready for the next task.");
  addActivity("Conversation history reset.");
});

ui.voiceBtn.addEventListener("click", () => {
  ui.chatInput.value = "Listening for voice input...";
  ui.chatInput.focus();
  addActivity("Voice capture primed.");
});

ui.commandButtons.forEach((button) => {
  button.addEventListener("click", () => {
    ui.chatInput.value = button.dataset.command;
    ui.chatInput.focus();
  });
});

updateClock();
renderMetrics();
updateRoutineList();
addActivity("Dashboard synchronized with local assistant state.");

window.setInterval(updateClock, 1000);
window.setInterval(tickMetrics, 1800);
window.setInterval(() => addActivity(activityFeed[Math.floor(Math.random() * activityFeed.length)]), 6000);
window.setInterval(updateRoutineList, 12000);
