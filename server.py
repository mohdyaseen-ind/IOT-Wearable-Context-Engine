import os
import json
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import groq

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here" else None

# The Temporal Memory Engine (Stores last 5 telemetry states)
memory_window = deque(maxlen=5)

SYSTEM_PROMPT = """You are Sarthi, an autonomous AI Profiler Agent running on a smartwatch.
You are a STATEFUL AI. You do not just look at the current snapshot; you look at the user's Recent Memory Window to detect trends.
Your job is to analyze the user's real-time telemetry and deduce their current state and urgency level dynamically.
DO NOT use hardcoded rules. You must think like a medical professional and context-aware assistant.

Respond ONLY in valid JSON format, matching exactly this schema:
{
    "profiler_thought": "A first-person, friendly explanation of what you observe. YOU MUST MENTION THE MEMORY/HISTORY if it is relevant (e.g. 'I see your HR is 150 and speed is 0, BUT looking at your memory, you were just running 10 seconds ago. You are just cooling down.')",
    "action_thought": "A first-person explanation of the action you are taking (e.g., 'Silencing notifications', 'Initiating SOS', 'Monitoring quietly').",
    "urgency": "Low" | "Medium" | "Critical",
    "action_title": "Short title for watch overlay (e.g., 'Workout Focus', 'SOS INITIATED', 'Absolute Silence', 'Monitoring')",
    "action_desc": "Short description for watch overlay",
    "action_icon": "fa-car" | "fa-om" | "fa-triangle-exclamation" | "fa-shield-halved" | "fa-person-running" | "fa-bed" | "fa-bell-slash",
    "ui_state": "normal" | "state-emergency",
    "is_active": true or false
}

Guidelines for Reasoning (The Cooldown Logic & Advanced Biometrics):
- Analyze the correlation between 'hr_bpm' (Heart Rate), 'gps_speed_kmh', 'spo2_pct' (Blood Oxygen), and 'body_temp_c'.
- THE FALSE POSITIVE TRAP: If HR is very high (>120) and speed is 0 NOW, check the Recent Memory Window! If they were moving fast (>10km/h) recently, this is NOT a medical emergency. It is a Workout Cooldown. Keep urgency Low.
- TRUE MEDICAL EMERGENCY: If HR is very high (>120) and speed is 0 NOW, AND they have been at speed 0 in all recent memory, this is a panic attack or cardiac event. Trigger Critical SOS!
- SLEEP APNEA DETECTION: If the app is "Sleep Tracker" and SpO2 drops below 92%, the user is experiencing Sleep Apnea or respiratory distress. Urgency="Critical", action="Wake up user", ui_state="state-emergency", action_icon="fa-lungs".
- FEVER DETECTION: If Body Temp is > 38.0°C and HR is elevated but speed is 0, the user has a Fever/Infection. Urgency="Medium", suggest rest.
- If HR is elevated (>100) and speed is high (>5km/h), they are likely working out or running (Medium urgency, trigger 'Workout Focus').
- If speed is very high (>20km/h), they are in a vehicle (Medium urgency, trigger 'Driving Focus').
- If app is "Beads Counter" and HR is low/resting, they need absolute silence (Low urgency, trigger 'Absolute Silence').
- For normal daily activities (e.g. HR 60-90, speed 0-4, SpO2 >95, Temp <37.5), is_active should be false (just 'Monitoring quietly').

Always adapt dynamically. Flex your medical and contextual intelligence.
"""

async def process_telemetry_with_llm(telemetry_data: dict, history: list) -> dict:
    # --- IoT EDGE FILTER (WAKE-WORD PATTERN) ---
    # To save battery and API tokens, we bypass the heavy 70B LLM for normal baseline states.
    sensors = telemetry_data.get("sensors", {})
    app_name = telemetry_data.get("active_app", "Clock")
    hr = sensors.get("hr_bpm", 70)
    speed = sensors.get("gps_speed_kmh", 0)
    spo2 = sensors.get("spo2_pct", 98)
    temp = sensors.get("body_temp_c", 36.5)

    if 60 <= hr <= 90 and speed == 0 and app_name == "Clock" and spo2 >= 95 and temp <= 37.5:
        return {
            "profiler_thought": f"[Edge Filter Active] Heart rate: {hr} BPM | SpO2: {spo2}% | Temp: {temp}°C. Baseline normal. I am bypassing the cloud LLM to save battery.",
            "action_thought": "I will remain asleep in the background.",
            "urgency": "Low",
            "action_title": "Monitoring",
            "action_desc": "Normal",
            "action_icon": "fa-shield-halved",
            "ui_state": "normal",
            "is_active": False
        }

    # --- CLOUD LLM (HEAVY INFERENCE) ---
    if not client:
        return fallback_logic(telemetry_data, history)
        
    try:
        user_prompt = f"Recent Memory Window (Past to Present):\n{json.dumps(history, indent=2)}\n\nCURRENT Telemetry:\n{json.dumps(telemetry_data, indent=2)}"
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"LLM Error: {e}")
        return fallback_logic(telemetry_data, history)

def fallback_logic(telemetry: dict, history: list) -> dict:
    """Mock fallback logic in case Groq is unavailable."""
    sensors = telemetry.get("sensors", {})
    app_name = telemetry.get("active_app", "")
    hr = sensors.get("hr_bpm", 70)
    speed = sensors.get("gps_speed_kmh", 0)
    
    # Check history for "Cooldown" logic
    was_running_recently = any(h.get("sensors", {}).get("gps_speed_kmh", 0) > 8 for h in history)

    if hr > 130 and speed == 0:
        if was_running_recently:
            return {
                "profiler_thought": f"Your heart rate is high ({hr} BPM) while standing still, but looking at your memory, you were just running. You are in a cooldown phase.",
                "action_thought": "I will not trigger an SOS. I will let you rest and continue monitoring quietly.",
                "urgency": "Low",
                "action_title": "Cooldown",
                "action_desc": "Recovering from workout.",
                "action_icon": "fa-person-running",
                "ui_state": "normal",
                "is_active": True
            }
        else:
            return {
                "profiler_thought": f"I notice your heart rate has spiked to {hr} BPM, but you are completely still and haven't moved recently. This is highly abnormal.",
                "action_thought": "I'm concerned this might be a panic attack or cardiac event. I am bypassing your silent mode and initiating the SOS protocol.",
                "urgency": "Critical",
                "action_title": "SOS INITIATED",
                "action_desc": "Calling emergency contacts.",
                "action_icon": "fa-triangle-exclamation",
                "ui_state": "state-emergency",
                "is_active": True
            }
    elif app_name == "Beads Counter" and speed == 0:
        return {
            "profiler_thought": "You've opened the Beads Counter and are sitting quietly. It looks like you're starting your prayer or meditation.",
            "action_thought": "To protect your focus, I am silencing all non-emergency notifications and enabling auto-replies.",
            "urgency": "Low",
            "action_title": "Absolute Silence",
            "action_desc": "Notifications & calls muted.",
            "action_icon": "fa-om",
            "ui_state": "normal",
            "is_active": True
        }
    elif app_name == "Maps Navigation" and hr > 85:
        return {
            "profiler_thought": f"You are driving at {speed} km/h and your heart rate is elevated at {hr} BPM. You seem stressed by the traffic.",
            "action_thought": "I am putting your phone on 'Driving Focus' to block WhatsApp spam so you don't get distracted.",
            "urgency": "Medium",
            "action_title": "Driving Focus",
            "action_desc": "Notifications silenced.",
            "action_icon": "fa-car",
            "ui_state": "normal",
            "is_active": True
        }
        
    return {
        "profiler_thought": f"Heart rate is {hr} BPM, speed is {speed}. Everything looks completely normal.",
        "action_thought": "I will remain quietly in the background monitoring your health.",
        "urgency": "Low",
        "action_title": "Monitoring",
        "action_desc": "Normal",
        "action_icon": "fa-shield-halved",
        "ui_state": "normal",
        "is_active": False
    }

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            telemetry_data = json.loads(data_text)
            
            # Extract history as a list
            history_list = list(memory_window)
            
            # Process via Agent with History
            agent_decision = await process_telemetry_with_llm(telemetry_data, history_list)
            
            # Add current to memory window AFTER processing, so it becomes history for the next tick
            memory_window.append(telemetry_data)
            
            await websocket.send_text(json.dumps({
                "type": "agent_decision",
                "data": agent_decision
            }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
