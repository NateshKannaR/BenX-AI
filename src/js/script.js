function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function randomStep(current, step, min, max) {
  const next = current + (Math.random() * step * 2 - step);
  return Math.round(clamp(next, min, max));
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

const state = {
  cpu: 15,
  mem: 35,
  battery: 45,
  disk: 69
};

function updateClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  const stamp = `[${hh}:${mm}:${ss}]`;

  setText("clock", `${hh}:${mm}:${ss}`);
  setText("chatTs", stamp);
}

function renderStats() {
  setText("cpuUsage", `${state.cpu}%`);
  setText("memory", `${state.mem}%`);
  setText("disk", `${state.disk}%`);
  setText("battery", `${state.battery}% (Discharging)`);
}

function tickStats() {
  state.cpu = randomStep(state.cpu, 5, 8, 96);
  state.mem = randomStep(state.mem, 4, 15, 90);
  state.disk = randomStep(state.disk, 2, 40, 92);
  state.battery = randomStep(state.battery, 1, 5, 98);
  renderStats();
}

updateClock();
renderStats();
setInterval(updateClock, 1000);
setInterval(tickStats, 1800);
