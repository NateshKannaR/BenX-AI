const chartConfig = {
  type: 'line',
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { display: false },
      y: { display: false, min: 0, max: 100 }
    },
    elements: {
      line: { tension: 0.4, borderWidth: 2 },
      point: { radius: 0 }
    },
    animation: { duration: 300 }
  }
};

const createChart = (id, color) => {
  const ctx = document.getElementById(id).getContext('2d');
  return new Chart(ctx, {
    ...chartConfig,
    data: {
      labels: Array(20).fill(''),
      datasets: [{
        data: Array(20).fill(0),
        borderColor: color,
        backgroundColor: `${color}20`,
        fill: true
      }]
    }
  });
};

const charts = {
  cpu: createChart('cpuChart', '#00ff88'),
  ram: createChart('ramChart', '#00d4ff'),
  network: createChart('networkChart', '#ff00ff'),
  gpu: createChart('gpuChart', '#ffaa00'),
  temp: createChart('tempChart', '#ff0055')
};

const state = {
  cpu: 15, ram: 35, network: 0, gpu: 20, temp: 45
};

const updateChart = (chart, value) => {
  chart.data.datasets[0].data.shift();
  chart.data.datasets[0].data.push(value);
  chart.update('none');
};

const randomStep = (current, step, min, max) => {
  const next = current + (Math.random() * step * 2 - step);
  return Math.max(min, Math.min(max, next));
};

const updateStats = () => {
  state.cpu = randomStep(state.cpu, 8, 5, 95);
  state.ram = randomStep(state.ram, 6, 10, 90);
  state.network = randomStep(state.network, 50, 0, 1000);
  state.gpu = randomStep(state.gpu, 10, 0, 100);
  state.temp = randomStep(state.temp, 3, 30, 85);

  updateChart(charts.cpu, state.cpu);
  updateChart(charts.ram, state.ram);
  updateChart(charts.network, state.network / 10);
  updateChart(charts.gpu, state.gpu);
  updateChart(charts.temp, state.temp);

  document.getElementById('cpuValue').textContent = `${Math.round(state.cpu)}%`;
  document.getElementById('ramValue').textContent = `${Math.round(state.ram)}%`;
  document.getElementById('networkValue').textContent = `${Math.round(state.network)} KB/s`;
  document.getElementById('gpuValue').textContent = `${Math.round(state.gpu)}%`;
  document.getElementById('tempValue').textContent = `${Math.round(state.temp)}°C`;
};

const updateClock = () => {
  const now = new Date();
  const time = now.toTimeString().split(' ')[0];
  document.getElementById('clock').textContent = time;
  document.getElementById('chatTs').textContent = `[${time}]`;
};

updateClock();
setInterval(updateClock, 1000);
setInterval(updateStats, 1000);
