// Sarthi - The IoT Wearable "Context" Engine
// V7: Zero-Instruction Sandbox

const WS_URL = "ws://localhost:8000/ws";
let ws;
let isConnected = false;

// --- DOM Elements ---
// Sliders
const sliderHr = document.getElementById('slider-hr');
const sliderHrVal = document.getElementById('slider-hr-val');
const sliderSpeed = document.getElementById('slider-speed');
const sliderSpeedVal = document.getElementById('slider-speed-val');
const sliderSpo2 = document.getElementById('slider-spo2');
const sliderSpo2Val = document.getElementById('slider-spo2-val');
const sliderTemp = document.getElementById('slider-temp');
const sliderTempVal = document.getElementById('slider-temp-val');
const selectApp = document.getElementById('select-app');

// Chat UI
const chatProfiler = document.getElementById('chat-profiler');
const chatAction = document.getElementById('chat-action');
const actionMsgContainer = document.querySelector('.action-msg');
const wsStatusDot = document.querySelector('.dot');
const wsStatusText = document.getElementById('ws-status');
const telemetryTicker = document.querySelector('.telemetry-ticker');

// Watch UI
const watchHr = document.getElementById('watch-hr');
const watchBattery = document.getElementById('watch-battery');
const watchTime = document.getElementById('watch-time');
const watchDate = document.getElementById('watch-date');
const watchApp = document.getElementById('watch-app');
const watchScreen = document.getElementById('watch-screen');
const watchFaceBase = document.getElementById('watch-face-base');

const watchAlertOverlay = document.getElementById('watch-alert-overlay');
const watchAlertIcon = document.getElementById('watch-alert-icon');
const watchAlertTitle = document.getElementById('watch-alert-title');
const watchAlertDesc = document.getElementById('watch-alert-desc');
const sosCountdown = document.getElementById('sos-countdown');

// Init Date
const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
const d = new Date();
if(watchDate) watchDate.innerText = `${days[d.getDay()]} ${d.getDate()}`;

// --- Slider Event Listeners ---
sliderHr.addEventListener('input', (e) => { sliderHrVal.innerText = `${e.target.value} BPM`; triggerTelemetryUpdate(); });
sliderSpeed.addEventListener('input', (e) => { sliderSpeedVal.innerText = `${e.target.value} km/h`; triggerTelemetryUpdate(); });
sliderSpo2.addEventListener('input', (e) => { sliderSpo2Val.innerText = `${e.target.value}%`; triggerTelemetryUpdate(); });
sliderTemp.addEventListener('input', (e) => { sliderTempVal.innerText = `${e.target.value}°C`; triggerTelemetryUpdate(); });
selectApp.addEventListener('change', triggerTelemetryUpdate);

let sosTimerInterval;
let sosSeconds = 10;

// --- Quick Scenarios ---
window.injectScenario = function(scenario) {
    if (scenario === 'prayer') {
        sliderHr.value = 65; sliderSpeed.value = 0; selectApp.value = "Beads Counter";
    } else if (scenario === 'traffic') {
        sliderHr.value = 95; sliderSpeed.value = 15; selectApp.value = "Maps Navigation";
    } else if (scenario === 'panic') {
        sliderHr.value = 155; sliderSpeed.value = 0; selectApp.value = "Clock";
    }
    
    // Update displays
    sliderHrVal.innerText = `${sliderHr.value} BPM`;
    sliderSpeedVal.innerText = `${sliderSpeed.value} km/h`;
    
    triggerTelemetryUpdate();
};

// --- WebSocket Connection ---
function initWebSocket() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        isConnected = true;
        wsStatusDot.classList.add('online');
        wsStatusText.innerHTML = '<div class="dot online"></div> Online';
        triggerTelemetryUpdate();
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "agent_decision") {
            handleAgentDecision(message.data);
        }
    };
    
    ws.onclose = () => {
        isConnected = false;
        wsStatusDot.classList.remove('online');
        wsStatusText.innerHTML = '<div class="dot"></div> Offline';
        setTimeout(initWebSocket, 3000);
    };
}

let updateDebounce;
function triggerTelemetryUpdate() {
    clearTimeout(updateDebounce);
    updateDebounce = setTimeout(sendTelemetry, 500); // Debounce slider movements
}

let lastSentTelemetry = { hr: -1, speed: -1, spo2: -1, temp: -1, app: "" };

function sendTelemetry() {
    if (!isConnected) return;
    
    const currentHr = parseInt(sliderHr.value);
    const currentSpeed = parseInt(sliderSpeed.value);
    const currentSpo2 = parseInt(sliderSpo2.value);
    const currentTemp = parseFloat(sliderTemp.value);
    const currentApp = selectApp.value;

    // The IoT "Delta Filter" - Only send data to backend if something significantly changed!
    if (
        Math.abs(currentHr - lastSentTelemetry.hr) < 5 &&
        Math.abs(currentSpeed - lastSentTelemetry.speed) < 2 &&
        Math.abs(currentSpo2 - lastSentTelemetry.spo2) < 2 &&
        Math.abs(currentTemp - lastSentTelemetry.temp) < 0.3 &&
        currentApp === lastSentTelemetry.app
    ) {
        // Optimistic UI update for watch (sensors only)
        updateWatchSensors({ sensors: { hr_bpm: currentHr, gps_speed_kmh: currentSpeed }, active_app: currentApp });
        return; // Do not send WebSocket!
    }

    lastSentTelemetry = { hr: currentHr, speed: currentSpeed, spo2: currentSpo2, temp: currentTemp, app: currentApp };
    
    telemetryTicker.innerHTML = `<i class="fa-solid fa-satellite-dish fa-fade"></i> Sending to Edge Node...`;
    
    let accel = "Still";
    if (currentSpeed > 0) accel = "Moving";
    if (currentSpeed > 10) accel = "Bumpy";

    const telemetry = {
        timestamp: new Date().toISOString(),
        sensors: {
            hr_bpm: currentHr,
            accelerometer: accel,
            gps_speed_kmh: currentSpeed,
            spo2_pct: currentSpo2,
            body_temp_c: currentTemp,
            battery_pct: 85
        },
        active_app: currentApp
    };

    ws.send(JSON.stringify(telemetry));
    
    updateWatchSensors(telemetry);
}

function handleAgentDecision(decision) {
    telemetryTicker.innerHTML = `<i class="fa-solid fa-check" style="color:#34c759"></i> Decision Received.`;
    
    // Update Chat UI (The ChatGPT style reasoning)
    if(chatProfiler) chatProfiler.innerText = decision.profiler_thought;
    if(chatAction) chatAction.innerText = decision.action_thought;
    
    if(decision.urgency === "Critical") {
        actionMsgContainer.classList.add('critical');
    } else {
        actionMsgContainer.classList.remove('critical');
    }

    // Prepare Action for Watch
    let action = {
        isActive: decision.is_active,
        title: decision.action_title,
        desc: decision.action_desc,
        icon: decision.action_icon,
        iconBg: decision.ui_state === 'state-emergency' ? '#fff' : '#5e5ce6',
        uiState: decision.ui_state
    };
    if(decision.action_icon === 'fa-car') action.iconBg = '#34c759';

    updateWatchAction(action);
}

// --- Watch UI Updaters ---
function updateWatchSensors(telemetry) {
    if(!watchHr) return;
    watchHr.innerText = telemetry.sensors.hr_bpm;
    
    let iconClass = "fa-clock";
    if(telemetry.active_app === "Beads Counter") iconClass = "fa-hands-praying";
    if(telemetry.active_app === "Maps Navigation") iconClass = "fa-map-location-dot";
    if(telemetry.active_app === "Sleep Tracker") iconClass = "fa-bed";
    
    watchApp.innerHTML = `<i class="fa-solid ${iconClass}"></i>`;
    
    const now = new Date();
    watchTime.innerText = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
}

function updateWatchAction(action) {
    clearInterval(sosTimerInterval);
    
    if (action.isActive) {
        watchAlertOverlay.classList.add('active');
        watchFaceBase.classList.add('blurred');
        
        watchAlertTitle.innerText = action.title;
        watchAlertDesc.innerText = action.desc;
        watchAlertIcon.innerHTML = `<i class="fa-solid ${action.icon}"></i>`;
        if (action.iconBg) watchAlertIcon.style.background = action.iconBg;

        if (action.uiState === 'state-emergency') {
            watchScreen.classList.add('state-emergency');
            sosCountdown.style.display = 'block';
            sosSeconds = 10;
            document.getElementById('sos-timer').innerText = sosSeconds;
            sosTimerInterval = setInterval(() => {
                sosSeconds--;
                if(sosSeconds >= 0) document.getElementById('sos-timer').innerText = sosSeconds;
            }, 1000);
        } else {
            watchScreen.classList.remove('state-emergency');
            sosCountdown.style.display = 'none';
        }
    } else {
        watchAlertOverlay.classList.remove('active');
        watchFaceBase.classList.remove('blurred');
        watchScreen.classList.remove('state-emergency');
        sosCountdown.style.display = 'none';
    }
}

// Start
initWebSocket();
setInterval(() => {
    const now = new Date();
    if(watchTime) watchTime.innerText = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
}, 10000);
