# SamudraGEN 3.0: Marine Telemetry Digital Twin

## 1. Project Overview & Identity

We are building **SamudraGEN 3.0**, an advanced marine telemetry dashboard and real-time digital twin for an Oscillating Wave Surge Converter (OWSC) prototype. The physical device is a bottom-hinged floating module deployed near a coastal pier to harvest renewable energy from sea waves.

An onboard **ESP32 microcontroller** reads high-frequency physical and electrical sensor data and transmits it over standard Wi-Fi via a local router.

The primary goal of this application is to give engineers a zero-latency, highly visual representation of the device's mechanical movement and electrical efficiency from anywhere in the world.

---

## 2. Core Frontend Tech Stack & Architecture

To avoid Server-Side Rendering (SSR) hydration issues with canvas and WebGL engines, this project is built entirely as a pure, high-performance **Single Page Application (SPA)**.

* **Build Tool & Framework:** Vite + React + TypeScript
* **Styling:** Tailwind CSS (utility-first approach matching a strict, clean modern industrial UI)
* **3D Digital Twin Engine:** Native `three` (Three.js) initialized within a React reference to maintain direct control over the WebGL render loop, ensuring maximum performance without the overhead of wrappers.
* **Data Visualization:** Apache ECharts (`echarts` + `echarts-for-react`) for canvas-level performance with dense time-series data.
* **State Management:** Zustand (for reactive, decoupled state injection to prevent DOM-wide re-renders during high-frequency telemetry ticks)
* **Communication Protocol:** `mqtt` (MQTT over WebSockets for direct browser-to-cloud telemetry ingestion)

---

## 3. Data Flow & Serverless Architecture

The project leverages a decoupled, serverless backend. No traditional backend server logic should be written inside this repository.

1. **Ingestion:** ESP32 -> WiFi Router -> AWS IoT Core (MQTT Topic: `ocean/wave/telemetry`).
2. **Live Stream (Real-Time):** The Vite SPA connects directly to AWS IoT Core via secure WebSockets (authenticated securely via AWS Cognito temporary credentials). Incoming payloads are pushed directly to the global Zustand store.
3. **Historical Logs (24/7 Tracking):** An AWS IoT rule routes incoming payloads into an **Amazon DynamoDB** database. To fetch logs, the frontend queries an external **AWS Lambda** serverless function exposed via **AWS API Gateway**.

### JSON Telemetry Schema Example

```json
{
  "ts": "10:30:12",
  "waveHeight": 1.55,
  "waveFreq": 0.25,
  "rpm": 120,
  "power": 24.0,
  "voltage": 24.1,
  "current": 1.0
}
```

---

## 5. Repository File Structure

The codebase is organized as follows:

```text
src/
├── assets/          # Static assets (SVGs, logos, images)
├── components/
│   ├── 3d/          # OceanSimulation.tsx (Native Three.js integration)
│   ├── charts/      # Apache ECharts components (PowerOutputChart, WaveHeight, DailyMetrics, etc.)
│   ├── layout/      # AppHeader.tsx
│   └── ui/          # Reusable dashboard widgets and common elements (CommonCard, LiveBadge, Reading)
├── services/        # mqttClient.ts (AWS IoT WebSockets or similar ingestion setup)
├── store/           # telemetryStore.ts (Zustand Global State Engine)
├── App.css          # Global Styles
├── App.tsx          # Main Grid Assembler
├── index.css        # Tailwind Injections
└── main.tsx         # React DOM Entry
```
