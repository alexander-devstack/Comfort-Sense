/* ==========================================
   SMART OFFICE IoT DASHBOARD - JavaScript
   Real-time data fetching and UI updates
   ========================================== */

// Configuration
const CONFIG = {
    API_BASE: '', // Changed from '/api' to fix double-prefix 404s and use port 5005 location
    UPDATE_INTERVAL: 1000,  // 1 second (High-frequency update)
    HISTORY_LIMIT: 50,
    THRESHOLDS: {
        TEMP_COMFORT_MIN: 20,
        TEMP_COMFORT_MAX: 27,
        TEMP_WARNING: 30,
        HUM_COMFORT_MIN: 40,
        HUM_COMFORT_MAX: 60,
        HUM_WARNING: 70,
        LIGHT_ARTIFICIAL: 500,
        PEOPLE_LOW: 3,
        PEOPLE_MEDIUM: 6,
        PEOPLE_HIGH: 10
    }
};

// State
let historyChart = null;
let isConnected = false;
let lastDataId = null;
let lastDataTimestamp = null;

// DOM Elements
const elements = {
    // Connection
    connectionStatus: document.getElementById('connectionStatus'),
    lastUpdate: document.getElementById('lastUpdate'),

    // Header
    headerClock: document.getElementById('headerClock'),
    headerDate: document.getElementById('headerDate'),

    // Room Status
    roomStatusBanner: document.getElementById('roomStatusBanner'),
    occupancyStatus: document.getElementById('occupancyStatus'),
    uptimeValue: document.getElementById('uptimeValue'),

    // Alert Banner
    alertBanner: document.getElementById('alertBanner'),

    // Temperature
    tempValue: document.getElementById('tempValue'),
    tempGauge: document.getElementById('tempGauge'),
    tempStatus: document.getElementById('tempStatus'),

    // Humidity
    humValue: document.getElementById('humValue'),
    humGauge: document.getElementById('humGauge'),
    humStatus: document.getElementById('humStatus'),

    // Light
    lightValue: document.getElementById('lightValue'),
    lightGauge: document.getElementById('lightGauge'),
    lightStatus: document.getElementById('lightStatus'),

    // Motion
    motionIndicator: document.getElementById('motionIndicator'),
    motionStatus: document.getElementById('motionStatus'),
    
    // Outdoor & Efficiency
    outdoorTemp: document.getElementById('outdoorTempValue'),
    outdoorHum: document.getElementById('outdoorHumValue'),
    acEfficiencyBadge: document.getElementById('acEfficiencyBadge'),
    thermalDelta: document.getElementById('thermalDeltaValue'),
    recommendationBanner: document.getElementById('recommendationBanner'),
    recommendationText: document.getElementById('recommendationText'),

    // People Count
    peopleCountValue: document.getElementById('peopleCountValue'),
    peopleBar: document.getElementById('peopleBar'),
    peopleDensity: document.getElementById('peopleDensity'),

    // Comfort Score
    comfortScoreValue: document.getElementById('comfortScoreValue'),
    comfortRingFill: document.getElementById('comfortRingFill'),
    comfortTempBar: document.getElementById('comfortTempBar'),
    comfortHumBar: document.getElementById('comfortHumBar'),
    comfortTempScore: document.getElementById('comfortTempScore'),
    comfortHumScore: document.getElementById('comfortHumScore'),
    comfortIndoor: document.getElementById('comfortIndoor'),
    comfortIdeal: document.getElementById('comfortIdeal'),

    // Energy
    ledRuntime: document.getElementById('ledRuntime'),
    energyUsed: document.getElementById('energyUsed'),
    energyCost: document.getElementById('energyCost'),
    energyRate: document.getElementById('energyRate'),
    energyResetBtn: document.getElementById('energyResetBtn'),

    // Stats
    avgTemp: document.getElementById('avgTemp'),
    avgHum: document.getElementById('avgHum'),
    avgLight: document.getElementById('avgLight'),
    totalReadings: document.getElementById('totalReadings'),

    // Hardware Status
    rgbDot: document.getElementById('rgbDot'),
    buzzerIndicator: document.getElementById('buzzerIndicator')
};

// ==========================================
// API Functions
// ==========================================

async function fetchLatestData() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/data`);
        const result = await response.json();

        if (result.status === 'success' && result.data) {
            updateConnectionStatus(true);
            
            // Only update everything if it's actually new data
            if (result.data.id !== lastDataId) {
                updateDashboard(result.data);
                lastDataId = result.data.id;
                lastDataTimestamp = result.data.timestamp;
                
                // Trigger chart and stats updates as well for better sync
                fetchHistory();
                fetchStats();
            }
        }
    } catch (error) {
        console.error('Error fetching data:', error);
        updateConnectionStatus(false);
    }
}

async function fetchHistory() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/history?limit=${CONFIG.HISTORY_LIMIT}`);
        const result = await response.json();

        if (result.status === 'success' && result.data) {
            updateChart(result.data);
        }
    } catch (error) {
        console.error('Error fetching history:', error);
    }
}

async function fetchStats() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/stats`);
        const result = await response.json();

        if (result.status === 'success' && result.stats) {
            updateStats(result.stats);
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function resetEnergy() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/energy/reset`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.status === 'success') {
            // Animate button feedback
            const btn = elements.energyResetBtn;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                Reset!
            `;
            btn.style.borderColor = '#22c55e';
            btn.style.color = '#22c55e';

            setTimeout(() => {
                btn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="23 4 23 10 17 10"></polyline>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                    </svg>
                    Reset
                `;
                btn.style.borderColor = '';
                btn.style.color = '';
            }, 2000);

            // Immediately refresh
            fetchLatestData();
        }
    } catch (error) {
        console.error('Error resetting energy:', error);
    }
}

// ==========================================
// UI Update Functions
// ==========================================

function updateConnectionStatus(connected) {
    isConnected = connected;
    const statusEl = elements.connectionStatus;
    const statusText = statusEl.querySelector('.status-text');

    statusEl.classList.remove('connected', 'disconnected');

    if (connected) {
        statusEl.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        statusEl.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

function updateDashboard(data) {
    // data is the inner data object sent from fetchLatestData (result.data)
    const liveData = data || {};
    
    // Update timestamp
    const now = new Date();
    elements.lastUpdate.textContent = `Last update: ${now.toLocaleTimeString()}`;

    // Update Room Status
    const isOccupied = liveData.occupancy === 'occupied';
    elements.roomStatusBanner.classList.toggle('vacant', !isOccupied);
    elements.occupancyStatus.textContent = liveData.occupancy || 'Unknown';

    // Update Uptime
    if (liveData.uptime_seconds !== undefined) {
        elements.uptimeValue.textContent = formatDuration(liveData.uptime_seconds);
    }

    // Update Temperature
    updateTemperature(liveData.temperature);

    // Update Humidity
    updateHumidity(liveData.humidity);

    // Update Light
    updateLight(liveData.light);

    // Update Motion
    updateMotion(liveData.motion);

    // Update People Count
    updatePeopleCount(liveData.people_count);

    // Update Comfort Score
    updateComfortScore(liveData.comfort_score, liveData.comfort_breakdown);

    // Update Suspicious Activity Alert
    updateSuspiciousAlert(liveData.suspicious_activity);

    // Update Outdoor & Efficiency
    updateOutdoorAndEfficiency(liveData);

    // Update Energy
    updateEnergy(liveData.energy);

    // Update Hardware Status (RGB + Buzzer)
    updateHardwareStatus(liveData.rgb_status, liveData.buzzer_active);
}


function updateTemperature(temp) {
    if (temp === null || temp === undefined) {
        elements.tempValue.textContent = '--';
        return;
    }

    animateValue(elements.tempValue, temp, 1);

    // Update gauge (0-50°C range)
    const percentage = Math.min(Math.max((temp / 50) * 100, 0), 100);
    elements.tempGauge.style.width = `${percentage}%`;

    // Update status
    const statusEl = elements.tempStatus;
    const indicator = statusEl.querySelector('.status-indicator');
    const text = statusEl.querySelector('span:last-child');

    if (temp >= CONFIG.THRESHOLDS.TEMP_WARNING) {
        indicator.className = 'status-indicator bad';
        text.textContent = 'Too Hot!';
    } else if (temp >= CONFIG.THRESHOLDS.TEMP_COMFORT_MAX) {
        indicator.className = 'status-indicator moderate';
        text.textContent = 'Warm';
    } else if (temp >= CONFIG.THRESHOLDS.TEMP_COMFORT_MIN) {
        indicator.className = 'status-indicator good';
        text.textContent = 'Comfortable';
    } else {
        indicator.className = 'status-indicator moderate';
        text.textContent = 'Cool';
    }
}

function updateHumidity(hum) {
    if (hum === null || hum === undefined) {
        elements.humValue.textContent = '--';
        return;
    }

    animateValue(elements.humValue, hum, 1);

    // Update gauge (0-100% range)
    const percentage = Math.min(Math.max(hum, 0), 100);
    elements.humGauge.style.width = `${percentage}%`;

    // Update status
    const statusEl = elements.humStatus;
    const indicator = statusEl.querySelector('.status-indicator');
    const text = statusEl.querySelector('span:last-child');

    if (hum >= CONFIG.THRESHOLDS.HUM_WARNING) {
        indicator.className = 'status-indicator bad';
        text.textContent = 'Too Humid!';
    } else if (hum > CONFIG.THRESHOLDS.HUM_COMFORT_MAX) {
        indicator.className = 'status-indicator moderate';
        text.textContent = 'High';
    } else if (hum >= CONFIG.THRESHOLDS.HUM_COMFORT_MIN) {
        indicator.className = 'status-indicator good';
        text.textContent = 'Optimal';
    } else {
        indicator.className = 'status-indicator moderate';
        text.textContent = 'Dry';
    }
}

function updateLight(light) {
    if (light === null || light === undefined) {
        elements.lightValue.textContent = '--';
        return;
    }

    animateValue(elements.lightValue, Math.round(light), 0);

    // Update gauge (0-1024 range)
    const percentage = Math.min(Math.max((light / 1024) * 100, 0), 100);
    elements.lightGauge.style.width = `${percentage}%`;

    // Update status
    const statusEl = elements.lightStatus;
    const indicator = statusEl.querySelector('.status-indicator');
    const text = statusEl.querySelector('span:last-child');

    if (light < CONFIG.THRESHOLDS.LIGHT_ARTIFICIAL) {
        indicator.className = 'status-indicator moderate';
        text.textContent = 'Low Light';
    } else {
        indicator.className = 'status-indicator good';
        text.textContent = 'Adequate Light';
    }
}

function updateMotion(motion) {
    const isActive = motion === 1 || motion === true;

    elements.motionIndicator.classList.toggle('active', isActive);

    const statusText = elements.motionStatus.querySelector('.status-text');
    if (isActive) {
        statusText.textContent = 'Motion Detected';
        elements.motionStatus.classList.add('active');
    } else {
        statusText.textContent = 'No Motion';
        elements.motionStatus.classList.remove('active');
    }
}

// ==========================================
// New Feature: People Count
// ==========================================

function updatePeopleCount(count) {
    if (count === null || count === undefined) count = 0;

    // Update number
    elements.peopleCountValue.textContent = count;

    // Update segmented bar
    const segments = elements.peopleBar.querySelectorAll('.people-bar-segment');
    segments.forEach((seg, index) => {
        const segIndex = index + 1;
        seg.classList.remove('active', 'level-low', 'level-medium', 'level-high');

        if (segIndex <= count) {
            seg.classList.add('active');

            if (segIndex <= CONFIG.THRESHOLDS.PEOPLE_LOW) {
                seg.classList.add('level-low');
            } else if (segIndex <= CONFIG.THRESHOLDS.PEOPLE_MEDIUM) {
                seg.classList.add('level-medium');
            } else {
                seg.classList.add('level-high');
            }
        }
    });

    // Update density text
    const densityEl = elements.peopleDensity;
    const indicator = densityEl.querySelector('.density-indicator');
    const text = densityEl.querySelector('span:last-child');

    if (count === 0) {
        indicator.className = 'density-indicator good';
        text.textContent = 'Empty Room';
    } else if (count <= CONFIG.THRESHOLDS.PEOPLE_LOW) {
        indicator.className = 'density-indicator good';
        text.textContent = 'Low Density';
    } else if (count <= CONFIG.THRESHOLDS.PEOPLE_MEDIUM) {
        indicator.className = 'density-indicator moderate';
        text.textContent = 'Moderate Density';
    } else {
        indicator.className = 'density-indicator bad';
        text.textContent = 'High Density';
    }
}

// ==========================================
// New Feature: Comfort Score
// ==========================================

function updateComfortScore(score, breakdown) {
    if (score === null || score === undefined) return;

    // Update ring value
    elements.comfortScoreValue.textContent = Math.round(score);

    // Update ring fill (circumference = 2 * π * 52 ≈ 326.73)
    const circumference = 326.73;
    const offset = circumference - (score / 100) * circumference;
    elements.comfortRingFill.style.strokeDashoffset = offset;

    // Set ring color based on score
    const ringColor = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444';
    elements.comfortRingFill.style.stroke = ringColor;

    // Update breakdown bars and scores
    if (breakdown) {
        elements.comfortTempBar.style.width = `${breakdown.temp_score}%`;
        elements.comfortHumBar.style.width = `${breakdown.hum_score}%`;
        elements.comfortTempScore.textContent = `${Math.round(breakdown.temp_score)}%`;
        elements.comfortHumScore.textContent = `${Math.round(breakdown.hum_score)}%`;

        // Update comparison
        elements.comfortIndoor.textContent =
            `${breakdown.indoor_temp}°C / ${breakdown.indoor_hum}%`;
        elements.comfortIdeal.textContent =
            `${breakdown.ref_temp}°C / ${breakdown.ref_hum}%`;
    }
}

// ==========================================
// New Feature: Suspicious Activity Alert
// ==========================================

function updateSuspiciousAlert(isSuspicious) {
    if (isSuspicious) {
        elements.alertBanner.style.display = 'flex';
    } else {
        elements.alertBanner.style.display = 'none';
    }
}

// ==========================================
// New Feature: Outdoor & AC Efficiency
// ==========================================

function updateOutdoorAndEfficiency(data) {
    if (data.outdoor_temp === undefined || data.outdoor_hum === undefined) return;

    // Update values with animation
    animateValue(elements.outdoorTemp, data.outdoor_temp, 1);
    animateValue(elements.outdoorHum, data.outdoor_hum, 1);

    // Calculate delta and animate
    const delta = data.outdoor_temp - data.temperature;
    animateValue(elements.thermalDelta, delta, 1);
    elements.thermalDelta.textContent += '°C';

    // Determine efficiency level (mirroring Arduino/Backend logic)
    let efficiency = 'POOR';
    let badgeClass = 'efficiency-badge bad';

    if (delta > 8) {
        efficiency = 'EXCELLENT';
        badgeClass = 'efficiency-badge excellent';
    } else if (delta > 5) {
        efficiency = 'GOOD';
        badgeClass = 'efficiency-badge good';
    } else if (delta > 3) {
        efficiency = 'FAIR';
        badgeClass = 'efficiency-badge moderate';
    }

    elements.acEfficiencyBadge.textContent = efficiency;
    elements.acEfficiencyBadge.className = badgeClass;

    // Smart Recommendations
    updateRecommendation(data.temperature, data.outdoor_temp, data.occupancy);
}

function updateRecommendation(indoorTemp, outdoorTemp, occupancy) {
    const isOccupied = occupancy === 'occupied';
    let recommendation = '';

    // If indoor is warmer than outdoor AND outdoor is cool, recommend ventilation
    if (indoorTemp > outdoorTemp && outdoorTemp < 25 && isOccupied) {
        recommendation = "Outdoor is cooler — consider natural ventilation!";
    } 
    // If it's very hot outside and cooling is minimal
    else if (outdoorTemp > 30 && (outdoorTemp - indoorTemp) < 3 && isOccupied) {
        recommendation = "AC may be underperforming - check maintenance.";
    }

    if (recommendation) {
        elements.recommendationBanner.style.display = 'flex';
        elements.recommendationText.textContent = recommendation;
    } else {
        elements.recommendationBanner.style.display = 'none';
    }
}

// ==========================================
// New Feature: Energy Cost Monitor
// ==========================================

function updateEnergy(energy) {
    if (!energy) return;

    // LED Runtime
    elements.ledRuntime.textContent = formatDuration(energy.led_on_seconds);

    // Energy Used
    elements.energyUsed.textContent = `${energy.energy_kwh.toFixed(6)} kWh`;

    // Cost
    elements.energyCost.textContent = `₹${energy.cost_inr.toFixed(4)}`;

    // Rate
    elements.energyRate.textContent = `₹${energy.rate_per_kwh}/kWh · ${energy.wattage}W`;
}


// ==========================================
// New Feature: Hardware Status
// ==========================================

function updateHardwareStatus(rgbStatus, buzzerActive) {
    // RGB LED Status
    if (rgbStatus) {
        elements.rgbDot.setAttribute('data-status', rgbStatus);
        elements.rgbDot.title = `LED Status: ${rgbStatus.toUpperCase()}`;
    }

    // Buzzer Status
    if (buzzerActive) {
        elements.buzzerIndicator.classList.add('active');
        elements.buzzerIndicator.title = "Buzzer Active! High Humidity Alert";
    } else {
        elements.buzzerIndicator.classList.remove('active');
        elements.buzzerIndicator.title = "Buzzer Inactive";
    }
}

function formatDuration(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds}s`;
    } else {
        return `${seconds}s`;
    }
}

function updateClock() {
    const now = new Date();
    elements.headerClock.textContent = now.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    elements.headerDate.textContent = now.toLocaleDateString([], {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function updateStats(stats) {
    elements.avgTemp.textContent = `${stats.temperature.avg}°C`;
    elements.avgHum.textContent = `${stats.humidity.avg}%`;
    elements.avgLight.textContent = Math.round(stats.light.avg);
    elements.totalReadings.textContent = stats.total_readings.toLocaleString();
}

function animateValue(element, newValue, decimals) {
    const current = parseFloat(element.textContent) || 0;
    const target = parseFloat(newValue) || 0;

    element.textContent = target.toFixed(decimals);
}

// ==========================================
// Chart Functions
// ==========================================

function initChart() {
    const ctx = document.getElementById('historyChart').getContext('2d');

    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Temperature',
                    data: [],
                    borderColor: '#f97316',
                    backgroundColor: 'rgba(249, 115, 22, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                },
                {
                    label: 'Humidity',
                    data: [],
                    borderColor: '#4f7cff',
                    backgroundColor: 'rgba(79, 124, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                },
                {
                    label: 'Outdoor Temp',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.05)',
                    borderWidth: 2,
                    fill: false,
                    borderDash: [5, 5],
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 26, 0.9)',
                    titleColor: '#fff',
                    bodyColor: 'rgba(255, 255, 255, 0.8)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.4)',
                        maxTicksLimit: 8,
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    display: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.4)',
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    });
}

function updateChart(data) {
    if (!historyChart || !data.length) return;

    const labels = data.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    });

    const tempData = data.map(d => d.temperature);
    const humData = data.map(d => d.humidity);
    const outdoorData = data.map(d => d.outdoor_temp);

    historyChart.data.labels = labels;
    historyChart.data.datasets[0].data = tempData;
    historyChart.data.datasets[1].data = humData;
    historyChart.data.datasets[2].data = outdoorData;
    historyChart.update('none');
}

// ==========================================
// Export Functions
// ==========================================

function exportCsv() {
    // Trigger CSV download from the API
    const link = document.createElement('a');
    link.href = `${CONFIG.API_BASE}/api/export`;
    link.download = 'sensor_data.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Show feedback
    const btn = document.getElementById('exportCsvBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        Downloaded!
    `;
    btn.style.borderColor = '#22c55e';
    btn.style.color = '#22c55e';

    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.borderColor = '';
        btn.style.color = '';
    }, 2000);
}

// ==========================================
// Initialization
// ==========================================

function init() {
    console.log('🏢 Comfortsense Dashboard Initialized');

    // Initialize chart
    initChart();

    // Bind export button
    const exportBtn = document.getElementById('exportCsvBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportCsv);
    }

    // Bind energy reset button
    if (elements.energyResetBtn) {
        elements.energyResetBtn.addEventListener('click', resetEnergy);
    }

    // Start clock
    updateClock();
    setInterval(updateClock, 1000);

    // Initial fetch
    fetchLatestData();
    fetchHistory();
    fetchStats();

    // Set up polling
    setInterval(() => {
        fetchLatestData();
    }, CONFIG.UPDATE_INTERVAL);

    // Fetch history and stats less frequently
    setInterval(() => {
        fetchHistory();
        fetchStats();
    }, CONFIG.UPDATE_INTERVAL * 5);
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
