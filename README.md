# Sarthi: The Zero-Instruction Wearable Context Engine

> *ChatGPT revolutionized AI because it hid a massive neural network behind a simple, blank text box. It required **zero instructions** to use.*
>
> *We believe wearable AI should be exactly the same. The user should just wear the watch, and it should autonomously protect them. No buttons, no complex menus. Just context.*

**Sarthi** is an edge-simulated, multi-agent AI system that acts as the "brain" for a wearable device. It ingests a continuous stream of biological telemetry (Heart Rate, SpO2, Body Temp, GPS Speed) and uses a **Split-Compute Architecture** to autonomously trigger context-aware actions.

## 🚀 The Architecture (Why it wins)

Streaming sensor data to an LLM every second would drain a smartwatch battery in 5 minutes and cause massive API rate limits. We solved this by building a true **IoT Edge-Triggered Architecture (The Wake-Word Pattern)**.

1. **The Delta Filter (Frontend):** The watch UI only transmits data when it detects a significant delta (e.g., Heart rate jumps by 5 BPM).
2. **The First-Pass Edge Filter (Backend):** Before hitting the cloud LLM, a lightning-fast Python script checks for baseline normalcy. If you are sitting still with a 70 BPM heart rate, the system immediately returns a "Monitoring" state. The heavy cloud LLM remains asleep.
3. **The 70B Multi-Agent LLM (Cloud):** The moment an anomaly is detected (e.g., SpO2 drops to 85%), the system wakes up the massive `llama-3.3-70b-versatile` model via Groq to dynamically diagnose the issue (e.g., Sleep Apnea) and trigger an SOS.
4. **Temporal Memory:** Sarthi doesn't just look at a single snapshot. It maintains a rolling memory window. If your heart rate is 160 BPM but you were sprinting 10 seconds ago, it knows you are just cooling down and avoids a false-positive SOS.

## 🛠 How to Run the Simulation Sandbox

To prove Sarthi requires zero instructions, we built an interactive Simulation Sandbox. 

### 1. Install Dependencies
Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```

### 2. Add your Groq API Key
Sarthi uses the blazing-fast Groq API to run the 70B parameter Llama 3 model in real-time.
1. Go to [console.groq.com](https://console.groq.com) and create a free account.
2. Generate an API Key.
3. Create a `.env` file in this directory and add your key:
```env
GROQ_API_KEY=your_key_here
```
*(Note: If you don't add an API key or if you hit a rate limit, Sarthi will gracefully degrade to a local heuristic fallback script so your demo never crashes!)*

### 3. Start the Edge Node
Start the FastAPI backend:
```bash
python server.py
```

### 4. Open the Sandbox
Open `index.html` in your browser. 
- Use the **User Context Sandbox** on the left to simulate a medical event (e.g., Drag SpO2 down to 85% while the Sleep Tracker app is open).
- Watch the **Sarthi Agent** in the middle panel dynamically reason through the data.
- Watch the **Watch UI** on the right autonomously react without a single button press.
