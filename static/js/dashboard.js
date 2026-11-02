/**
 * ==============================================================================
 * Smart Classroom Environmental Monitoring System
 * Dashboard Frontend Controller
 * - Real-time polling & Chart.js live rendering
 * - Dynamic temperature & humidity color state managers
 * - Hardware device status tracking & offline detection (15s threshold)
 * ==============================================================================
 */

// Global State
let tempChart = null;
let humChart = null;
let previousReading = null;
let lastKnownReadingTime = null;
let pollTimer = null;
let clockTimer = null;
let secondsCounterTimer = null;

// Configurable Thresholds (Defaults matching backend)
const thresholds = {
  temperature: {
    coolMax: 18.0,
    comfortableMax: 24.0,
    warmMax: 30.0
  },
  humidity: {
    lowMax: 30.0,
    normalMax: 60.0,
    elevatedMax: 70.0
  },
  deviceTimeoutSeconds: 15
};

// Color palettes for chart accents
const CHART_COLORS = {
  temp: {
    cool: { border: '#0284c7', bg: 'rgba(2, 132, 199, 0.12)' },
    comfortable: { border: '#16a34a', bg: 'rgba(22, 163, 74, 0.12)' },
    warm: { border: '#ea580c', bg: 'rgba(234, 88, 12, 0.12)' },
    hot: { border: '#dc2626', bg: 'rgba(220, 38, 38, 0.14)' }
  },
  humidity: {
    low: { border: '#d97706', bg: 'rgba(217, 119, 6, 0.12)' },
    normal: { border: '#059669', bg: 'rgba(5, 150, 105, 0.12)' },
    elevated: { border: '#0284c7', bg: 'rgba(2, 132, 199, 0.12)' },
    high: { border: '#e11d48', bg: 'rgba(225, 29, 72, 0.14)' }
  }
};

// ==============================================================================
// Initialization
// ==============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initCharts();
  fetchThresholds();
  fetchDashboardData();

  // Poll backend every 3.5 seconds
  pollTimer = setInterval(fetchDashboardData, 3500);

  // Update "seconds ago" counter every second
  secondsCounterTimer = setInterval(updateSecondsAgoCounter, 1000);

  // Setup Event Listeners
  setupEventListeners();
});

// ==============================================================================
// Digital Clock & Timestamp Manager
// ==============================================================================
function initClock() {
  const timeElem = document.getElementById('clock-time');
  const dateElem = document.getElementById('clock-date');

  function update() {
    const now = new Date();
    if (timeElem) {
      timeElem.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    }
    if (dateElem) {
      dateElem.textContent = now.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }
  }

  update();
  clockTimer = setInterval(update, 1000);
}

// ==============================================================================
// Timezone-safe UTC Date Parser
// ==============================================================================
function parseTimestamp(ts) {
  if (!ts) return new Date();
  if (typeof ts === 'string') {
    // If the timestamp string lacks timezone indicator, treat it as UTC
    if (!ts.endsWith('Z') && !ts.includes('+') && !ts.match(/-\d{2}:\d{2}$/)) {
      return new Date(ts + 'Z');
    }
  }
  return new Date(ts);
}

// ==============================================================================
// Threshold Evaluation Helpers
// ==============================================================================
function evaluateTemperature(temp) {
  if (temp < thresholds.temperature.coolMax) {
    return {
      code: 'cool',
      label: 'Cool',
      cssClass: 'temp-cool',
      badgeClass: 'badge-cool',
      color: CHART_COLORS.temp.cool
    };
  } else if (temp <= thresholds.temperature.comfortableMax) {
    return {
      code: 'comfortable',
      label: 'Comfortable',
      cssClass: 'temp-comfortable',
      badgeClass: 'badge-comfortable',
      color: CHART_COLORS.temp.comfortable
    };
  } else if (temp <= thresholds.temperature.warmMax) {
    return {
      code: 'warm',
      label: 'Warm',
      cssClass: 'temp-warm',
      badgeClass: 'badge-warm',
      color: CHART_COLORS.temp.warm
    };
  } else {
    return {
      code: 'hot',
      label: 'Hot',
      cssClass: 'temp-hot',
      badgeClass: 'badge-hot',
      color: CHART_COLORS.temp.hot
    };
  }
}

function evaluateHumidity(hum) {
  if (hum < thresholds.humidity.lowMax) {
    return {
      code: 'low',
      label: 'Low Humidity',
      cssClass: 'hum-low',
      badgeClass: 'badge-hum-low',
      color: CHART_COLORS.humidity.low
    };
  } else if (hum <= thresholds.humidity.normalMax) {
    return {
      code: 'normal',
      label: 'Normal Range',
      cssClass: 'hum-normal',
      badgeClass: 'badge-hum-normal',
      color: CHART_COLORS.humidity.normal
    };
  } else if (hum <= thresholds.humidity.elevatedMax) {
    return {
      code: 'elevated',
      label: 'Elevated Humidity',
      cssClass: 'hum-elevated',
      badgeClass: 'badge-hum-elevated',
      color: CHART_COLORS.humidity.elevated
    };
  } else {
    return {
      code: 'high',
      label: 'High Humidity',
      cssClass: 'hum-high',
      badgeClass: 'badge-hum-high',
      color: CHART_COLORS.humidity.high
    };
  }
}

// ==============================================================================
// Chart.js Setup
// ==============================================================================
function initCharts() {
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 500,
      easing: 'easeOutQuart'
    },
    interaction: {
      mode: 'index',
      intersect: false
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#f8fafc',
        bodyColor: '#e2e8f0',
        padding: 10,
        cornerRadius: 8,
        displayColors: false
      }
    },
    scales: {
      x: {
        grid: {
          color: '#f1f5f9',
          drawBorder: false
        },
        ticks: {
          color: '#94a3b8',
          font: { size: 11, family: "'Inter', sans-serif" },
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 7
        }
      },
      y: {
        grid: {
          color: '#f1f5f9',
          drawBorder: false
        },
        ticks: {
          color: '#94a3b8',
          font: { size: 11, family: "'Inter', sans-serif" }
        }
      }
    }
  };

  // Temperature Chart
  const tempCtx = document.getElementById('tempChart').getContext('2d');
  tempChart = new Chart(tempCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Temperature (°C)',
        data: [],
        borderColor: CHART_COLORS.temp.comfortable.border,
        backgroundColor: CHART_COLORS.temp.comfortable.bg,
        borderWidth: 2.5,
        pointBackgroundColor: '#ffffff',
        pointBorderColor: CHART_COLORS.temp.comfortable.border,
        pointBorderWidth: 2,
        pointRadius: 3.5,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.35
      }]
    },
    options: {
      ...chartOptions,
      scales: {
        ...chartOptions.scales,
        y: {
          ...chartOptions.scales.y,
          title: {
            display: true,
            text: 'Temperature (°C)',
            color: '#64748b',
            font: { size: 11, weight: '600' }
          }
        }
      }
    }
  });

  // Humidity Chart
  const humCtx = document.getElementById('humChart').getContext('2d');
  humChart = new Chart(humCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Relative Humidity (%)',
        data: [],
        borderColor: CHART_COLORS.humidity.normal.border,
        backgroundColor: CHART_COLORS.humidity.normal.bg,
        borderWidth: 2.5,
        pointBackgroundColor: '#ffffff',
        pointBorderColor: CHART_COLORS.humidity.normal.border,
        pointBorderWidth: 2,
        pointRadius: 3.5,
        pointHoverRadius: 6,
        fill: true,
        tension: 0.35
      }]
    },
    options: {
      ...chartOptions,
      scales: {
        ...chartOptions.scales,
        y: {
          ...chartOptions.scales.y,
          title: {
            display: true,
            text: 'Humidity (%)',
            color: '#64748b',
            font: { size: 11, weight: '600' }
          },
          min: 0,
          max: 100
        }
      }
    }
  });
}

// ==============================================================================
// Data Fetching & UI Update
// ==============================================================================
async function fetchThresholds() {
  try {
    const res = await fetch('/api/thresholds');
    if (res.ok) {
      const data = await res.json();
      thresholds.temperature.coolMax = data.temperature.cool_max;
      thresholds.temperature.comfortableMax = data.temperature.comfortable_max;
      thresholds.temperature.warmMax = data.temperature.warm_max;
      thresholds.humidity.lowMax = data.humidity.low_max;
      thresholds.humidity.normalMax = data.humidity.normal_max;
      thresholds.humidity.elevatedMax = data.humidity.elevated_max;
      thresholds.deviceTimeoutSeconds = data.device_timeout_seconds;
    }
  } catch (err) {
    console.warn('Could not fetch thresholds, using defaults.', err);
  }
}

async function fetchDashboardData() {
  try {
    // 1. Fetch recent readings
    const readingsRes = await fetch('/api/readings?limit=25');

    if (!readingsRes.ok) {
      showErrorBanner('Unable to communicate with the monitoring server. Retrying...');
      return;
    }

    const data = await readingsRes.json();
    hideErrorBanner();

    // 2. Fetch device status
    const statusRes = await fetch('/api/device/status');
    let devStatus = null;
    if (statusRes.ok) {
      devStatus = await statusRes.json();
    }

    renderDashboard(data, devStatus);

  } catch (err) {
    console.error('Network error fetching dashboard data:', err);
    showErrorBanner('Server is currently unreachable. Please verify FastAPI backend is active.');
    markDeviceOffline('Backend Unreachable');
  }
}

function renderDashboard(data, devStatus) {
  const readings = data.readings || [];
  const total = data.total || 0;

  // Update total readings card
  const totalCountElem = document.getElementById('total-readings-count');
  if (totalCountElem) {
    totalCountElem.textContent = total.toLocaleString();
  }

  // Handle Empty State
  if (readings.length === 0) {
    showEmptyState();
    return;
  }

  hideEmptyState();

  // Latest reading is the first item (sorted desc)
  const latest = readings[0];
  lastKnownReadingTime = parseTimestamp(latest.timestamp);

  // Evaluate dynamic colors
  const tempEval = evaluateTemperature(latest.temperature);
  const humEval = evaluateHumidity(latest.humidity);

  // 1. Update Temperature Card
  updateTemperatureCard(latest, tempEval);

  // 2. Update Humidity Card
  updateHumidityCard(latest, humEval);

  // 3. Update Device Status Card & Header Badge
  updateDeviceStatusUI(devStatus, latest);

  // 4. Update Live Charts
  updateCharts(readings, tempEval, humEval);

  // 5. Update Recent Readings Table
  updateTable(readings);

  // Store for trend calculations
  previousReading = latest;
}

// ==============================================================================
// Temperature Card Update
// ==============================================================================
function updateTemperatureCard(reading, tempEval) {
  const card = document.getElementById('temp-card');
  const valueElem = document.getElementById('temp-value');
  const badgeElem = document.getElementById('temp-status-badge');
  const trendElem = document.getElementById('temp-trend');

  if (valueElem) {
    valueElem.textContent = reading.temperature.toFixed(1);
  }

  // Reset classes and add new dynamic class
  if (card) {
    card.classList.remove('temp-cool', 'temp-comfortable', 'temp-warm', 'temp-hot');
    card.classList.add(tempEval.cssClass);
  }

  if (badgeElem) {
    badgeElem.textContent = tempEval.label;
    badgeElem.className = `badge ${tempEval.badgeClass}`;
  }

  // Calculate Trend
  if (trendElem) {
    if (previousReading && previousReading.id !== reading.id) {
      const diff = reading.temperature - previousReading.temperature;
      if (Math.abs(diff) < 0.05) {
        trendElem.innerHTML = '<span class="trend-stable">→ Stable</span>';
      } else if (diff > 0) {
        trendElem.innerHTML = `<span class="trend-up">▲ +${diff.toFixed(1)}°C vs last</span>`;
      } else {
        trendElem.innerHTML = `<span class="trend-down">▼ ${diff.toFixed(1)}°C vs last</span>`;
      }
    } else {
      trendElem.innerHTML = '<span class="trend-stable">DHT22 Digital</span>';
    }
  }
}

// ==============================================================================
// Humidity Card Update
// ==============================================================================
function updateHumidityCard(reading, humEval) {
  const card = document.getElementById('hum-card');
  const valueElem = document.getElementById('hum-value');
  const badgeElem = document.getElementById('hum-status-badge');
  const comfortElem = document.getElementById('hum-comfort-status');

  if (valueElem) {
    valueElem.textContent = reading.humidity.toFixed(1);
  }

  if (card) {
    card.classList.remove('hum-low', 'hum-normal', 'hum-elevated', 'hum-high');
    card.classList.add(humEval.cssClass);
  }

  if (badgeElem) {
    badgeElem.textContent = humEval.label;
    badgeElem.className = `badge ${humEval.badgeClass}`;
  }

  if (comfortElem) {
    if (reading.humidity >= 30 && reading.humidity <= 60) {
      comfortElem.textContent = 'Comfortable RH Range';
    } else if (reading.humidity < 30) {
      comfortElem.textContent = 'Dry Air (Low RH)';
    } else {
      comfortElem.textContent = 'Elevated Humidity';
    }
  }
}

// ==============================================================================
// Device Status UI Update
// ==============================================================================
function updateDeviceStatusUI(devStatus, latest) {
  const headerBadge = document.getElementById('header-status-badge');
  const headerBadgeText = document.getElementById('header-status-text');
  const deviceStatusCard = document.getElementById('device-status-text');
  const deviceLastSeen = document.getElementById('device-last-seen');
  const offlineAlert = document.getElementById('alert-offline');

  const isOnline = devStatus ? devStatus.online : false;
  const lastDate = parseTimestamp(latest.timestamp);
  const timeFormatted = lastDate.toLocaleTimeString('en-US', { hour12: false });

  if (isOnline) {
    // Online State
    if (headerBadge) {
      headerBadge.className = 'connectivity-badge online';
      headerBadgeText.textContent = 'ESP32 Online';
    }
    if (deviceStatusCard) {
      deviceStatusCard.textContent = 'Online';
      deviceStatusCard.style.color = '#16a34a';
    }
    if (offlineAlert) {
      offlineAlert.classList.remove('show');
    }
  } else {
    // Offline State (>15 seconds without readings)
    if (headerBadge) {
      headerBadge.className = 'connectivity-badge offline';
      headerBadgeText.textContent = 'ESP32 Offline';
    }
    if (deviceStatusCard) {
      deviceStatusCard.textContent = 'Offline';
      deviceStatusCard.style.color = '#dc2626';
    }
    if (offlineAlert) {
      offlineAlert.classList.add('show');
    }
  }

  if (deviceLastSeen) {
    deviceLastSeen.textContent = `Last reading: ${timeFormatted}`;
  }

  updateSecondsAgoCounter();
}

function markDeviceOffline(reason) {
  const headerBadge = document.getElementById('header-status-badge');
  const headerBadgeText = document.getElementById('header-status-text');
  const deviceStatusCard = document.getElementById('device-status-text');
  const offlineAlert = document.getElementById('alert-offline');

  if (headerBadge) {
    headerBadge.className = 'connectivity-badge offline';
    headerBadgeText.textContent = 'ESP32 Offline';
  }
  if (deviceStatusCard) {
    deviceStatusCard.textContent = 'Offline';
    deviceStatusCard.style.color = '#dc2626';
  }
  if (offlineAlert) {
    offlineAlert.classList.add('show');
  }
}

function updateSecondsAgoCounter() {
  const secondsElem = document.getElementById('device-seconds-ago');
  if (!secondsElem || !lastKnownReadingTime) return;

  const now = new Date();
  const diffSec = Math.floor((now - lastKnownReadingTime) / 1000);

  if (diffSec < 0) {
    secondsElem.textContent = 'Just now';
  } else if (diffSec < 60) {
    secondsElem.textContent = `${diffSec}s ago`;
  } else {
    const mins = Math.floor(diffSec / 60);
    secondsElem.textContent = `${mins}m ${diffSec % 60}s ago`;
  }

  // If time exceeds 15 seconds, reflect immediately in UI
  if (diffSec > thresholds.deviceTimeoutSeconds) {
    markDeviceOffline('Timeout');
  }
}

// ==============================================================================
// Live Chart Updates
// ==============================================================================
function updateCharts(readings, tempEval, humEval) {
  if (!tempChart || !humChart) return;

  // Clone and reverse so oldest is on the left, newest on the right
  const chronological = [...readings].reverse();

  const labels = chronological.map(r => {
    const d = parseTimestamp(r.timestamp);
    return d.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  });

  const tempData = chronological.map(r => r.temperature);
  const humData = chronological.map(r => r.humidity);

  // Update Temperature Chart with dynamic colors
  tempChart.data.labels = labels;
  tempChart.data.datasets[0].data = tempData;
  tempChart.data.datasets[0].borderColor = tempEval.color.border;
  tempChart.data.datasets[0].pointBorderColor = tempEval.color.border;
  tempChart.data.datasets[0].backgroundColor = tempEval.color.bg;
  tempChart.update('none'); // Update without full redraw animation

  // Update Humidity Chart with dynamic colors
  humChart.data.labels = labels;
  humChart.data.datasets[0].data = humData;
  humChart.data.datasets[0].borderColor = humEval.color.border;
  humChart.data.datasets[0].pointBorderColor = humEval.color.border;
  humChart.data.datasets[0].backgroundColor = humEval.color.bg;
  humChart.update('none');
}

// ==============================================================================
// Recent Readings Table Update
// ==============================================================================
function updateTable(readings) {
  const tbody = document.getElementById('readings-table-body');
  if (!tbody) return;

  // Display top 15 readings
  const displayList = readings.slice(0, 15);

  let html = '';
  displayList.forEach(item => {
    const d = parseTimestamp(item.timestamp);
    const timeStr = d.toLocaleTimeString('en-US', { hour12: false });
    const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    const tEval = evaluateTemperature(item.temperature);
    const hEval = evaluateHumidity(item.humidity);

    html += `
      <tr>
        <td>
          <span class="table-cell-highlight">${timeStr}</span>
          <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 0.25rem;">${dateStr}</span>
        </td>
        <td>
          <span class="table-cell-highlight" style="color: ${tEval.color.border};">${item.temperature.toFixed(1)} °C</span>
        </td>
        <td>
          <span class="badge ${tEval.badgeClass}">${tEval.label}</span>
        </td>
        <td>
          <span class="table-cell-highlight" style="color: ${hEval.color.border};">${item.humidity.toFixed(1)} %</span>
        </td>
        <td>
          <span class="badge ${hEval.badgeClass}">${hEval.label}</span>
        </td>
        <td style="color: var(--text-muted); font-family: monospace; font-size: 0.75rem;">
          ${item.device_id || 'esp32-classroom-01'}
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

// ==============================================================================
// UI State & Error Handlers
// ==============================================================================
function showEmptyState() {
  const emptyRow = document.getElementById('empty-state-row');
  if (emptyRow) emptyRow.style.display = 'table-row';

  const tempVal = document.getElementById('temp-value');
  const humVal = document.getElementById('hum-value');
  if (tempVal) tempVal.textContent = '--';
  if (humVal) humVal.textContent = '--';

  const emptyAlert = document.getElementById('alert-empty');
  if (emptyAlert) emptyAlert.classList.add('show');
}

function hideEmptyState() {
  const emptyRow = document.getElementById('empty-state-row');
  if (emptyRow) emptyRow.style.display = 'none';

  const emptyAlert = document.getElementById('alert-empty');
  if (emptyAlert) emptyAlert.classList.remove('show');
}

function showErrorBanner(msg) {
  const banner = document.getElementById('alert-server-error');
  const textElem = document.getElementById('alert-server-error-text');
  if (banner && textElem) {
    textElem.textContent = msg;
    banner.classList.add('show');
  }
}

function hideErrorBanner() {
  const banner = document.getElementById('alert-server-error');
  if (banner) banner.classList.remove('show');
}

// ==============================================================================
// Simulation & Demonstration Helpers
// ==============================================================================
async function sendSampleReading(temperature, humidity) {
  try {
    const res = await fetch('/api/readings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        temperature: parseFloat(temperature),
        humidity: parseFloat(humidity),
        device_id: 'esp32-classroom-01'
      })
    });

    if (res.ok) {
      await fetchDashboardData();
      closeModal('sim-modal');
    } else {
      alert('Error sending sample reading: ' + res.statusText);
    }
  } catch (err) {
    alert('Failed to send reading: ' + err.message);
  }
}

function exportReadingsCSV() {
  fetch('/api/readings?limit=100')
    .then(res => res.json())
    .then(data => {
      const readings = data.readings || [];
      if (readings.length === 0) {
        alert('No readings available to export.');
        return;
      }

      let csv = 'ID,Timestamp,Temperature_C,Temperature_Status,Humidity_Percent,Humidity_Status,Device_ID\n';
      readings.forEach(r => {
        csv += `${r.id},"${r.timestamp}",${r.temperature},"${r.temp_status}",${r.humidity},"${r.humidity_status}","${r.device_id}"\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `classroom_readings_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
}

// ==============================================================================
// Modal Controllers
// ==============================================================================
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('open');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('open');
}

function setupEventListeners() {
  // Manual Refresh Button
  const refreshBtn = document.getElementById('btn-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      fetchDashboardData();
    });
  }

  // Open Sim Modal
  const simBtn = document.getElementById('btn-open-sim');
  if (simBtn) {
    simBtn.addEventListener('click', () => openModal('sim-modal'));
  }

  // Open Settings Modal
  const settingsBtn = document.getElementById('btn-open-settings');
  if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
      // Populate inputs with current threshold values
      document.getElementById('set-cool-max').value = thresholds.temperature.coolMax;
      document.getElementById('set-comf-max').value = thresholds.temperature.comfortableMax;
      document.getElementById('set-warm-max').value = thresholds.temperature.warmMax;
      document.getElementById('set-hum-low').value = thresholds.humidity.lowMax;
      document.getElementById('set-hum-norm').value = thresholds.humidity.normalMax;
      document.getElementById('set-hum-elev').value = thresholds.humidity.elevatedMax;
      openModal('settings-modal');
    });
  }

  // Settings Form Submit
  const settingsForm = document.getElementById('settings-form');
  if (settingsForm) {
    settingsForm.addEventListener('submit', (e) => {
      e.preventDefault();
      thresholds.temperature.coolMax = parseFloat(document.getElementById('set-cool-max').value);
      thresholds.temperature.comfortableMax = parseFloat(document.getElementById('set-comf-max').value);
      thresholds.temperature.warmMax = parseFloat(document.getElementById('set-warm-max').value);
      thresholds.humidity.lowMax = parseFloat(document.getElementById('set-hum-low').value);
      thresholds.humidity.normalMax = parseFloat(document.getElementById('set-hum-norm').value);
      thresholds.humidity.elevatedMax = parseFloat(document.getElementById('set-hum-elev').value);
      closeModal('settings-modal');
      fetchDashboardData();
    });
  }

  // Custom Sim Form Submit
  const simForm = document.getElementById('custom-sim-form');
  if (simForm) {
    simForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const temp = document.getElementById('sim-temp-input').value;
      const hum = document.getElementById('sim-hum-input').value;
      sendSampleReading(temp, hum);
    });
  }

  // Export CSV Button
  const exportBtn = document.getElementById('btn-export-csv');
  if (exportBtn) {
    exportBtn.addEventListener('click', exportReadingsCSV);
  }
}
