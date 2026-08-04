/**
 * SamudraGEN 3.0 — ESP32 OWSC Telemetry Simulator
 * 
 * Publishes realistic ocean energy telemetry to a local MQTT broker,
 * mimicking the exact JSON schema the ESP32 firmware sends.
 * 
 * Usage:
 *   node esp32_simulator.js
 * 
 * Options (env vars):
 *   MQTT_BROKER_URL  — default: mqtt://localhost:1883
 *   PUBLISH_INTERVAL — default: 5000 (ms)
 *   MQTT_TOPIC       — default: ocean/wave/telemetry
 */

import mqtt from "mqtt";

// ── Configuration ─────────────────────────────────────────
const BROKER_URL = process.env.MQTT_BROKER_URL || "mqtt://localhost:1883";
const TOPIC = process.env.MQTT_TOPIC || "ocean/wave/telemetry";
const INTERVAL_MS = parseInt(process.env.PUBLISH_INTERVAL || "5000", 10);

// ── Realistic OWSC Physics Model ──────────────────────────
// These simulate the physical behavior of a bottom-hinged
// oscillating wave surge converter prototype.

class OWSCSimulator {
  constructor() {
    // Ocean state (slowly drifting)
    this.waveHeight = 1.2;    // meters (typical: 0.5 – 3.0m)
    this.waveFreq = 0.15;     // Hz (typical: 0.05 – 0.30 Hz, i.e. 3–20s periods)

    // Mechanical
    this.rpm = 80;            // generator RPM (typical: 40 – 200)

    // Electrical output
    this.voltage = 12.0;      // volts
    this.current = 0.8;       // amps

    // Time-of-day effects (simulate calmer mornings, rougher afternoons)
    this.timeScale = 0;
  }

  /** Clamp a value between min and max */
  clamp(val, min, max) {
    return Math.min(max, Math.max(min, val));
  }

  /** Brownian random walk with mean-reversion */
  drift(current, target, volatility, min, max) {
    const meanReversion = (target - current) * 0.05;
    const noise = (Math.random() - 0.5) * volatility;
    return this.clamp(current + meanReversion + noise, min, max);
  }

  /** Generate one telemetry tick */
  tick() {
    const now = new Date();
    const hour = now.getHours();

    // Sea state varies with time of day (rougher 12:00–18:00)
    const seaEnergy = hour >= 10 && hour <= 18
      ? 1.0 + Math.sin((hour - 10) / 8 * Math.PI) * 0.6
      : 0.6 + Math.random() * 0.2;

    // Wave height: 0.3m – 3.5m, mean-reverts around seaEnergy-scaled target
    this.waveHeight = this.drift(
      this.waveHeight, 0.8 + seaEnergy * 1.5, 0.15, 0.3, 3.5
    );

    // Wave frequency: 0.05 – 0.30 Hz (inversely correlated with height in real seas)
    const freqTarget = 0.25 - (this.waveHeight / 3.5) * 0.15;
    this.waveFreq = this.drift(this.waveFreq, freqTarget, 0.02, 0.05, 0.30);

    // RPM is proportional to wave energy (height² × freq)
    const waveEnergy = this.waveHeight ** 2 * this.waveFreq;
    const rpmTarget = 40 + waveEnergy * 300;
    this.rpm = Math.round(this.drift(this.rpm, rpmTarget, 8, 0, 240));

    // Voltage: roughly proportional to RPM, clamped to generator rating
    const voltTarget = (this.rpm / 240) * 24;
    this.voltage = Math.round(this.drift(this.voltage, voltTarget, 0.3, 0, 28) * 10) / 10;

    // Current: depends on load, correlates with power demand
    const currTarget = (this.rpm / 240) * 2.5;
    this.current = Math.round(this.drift(this.current, currTarget, 0.1, 0, 3.0) * 10) / 10;

    // Power = V × I
    const power = Math.round(this.voltage * this.current * 10) / 10;

    // Timestamp in ISO-8601 format (matching ESP32 firmware)
    const ts = now.toISOString();

    const waveHeightCm = Math.round(this.waveHeight * 100);
    const waveFreqHz = Math.round(this.waveFreq * 100) / 100;
    
    // Simulate distance sensor (assume sensor is 400cm above sea level)
    const distanceCm = 400 - waveHeightCm;

    return {
      deviceId: "SamudraGEN-ESP32S3-SIM",
      ts,
      waveHeightCm,
      waveFreqHz,
      distanceCm,
      rpm: this.rpm,
      power,
      voltage: this.voltage,
      current: this.current,
      relayMode: "AUTO",
      relayState: "GRID",
      wifiRssi: -65 + Math.round((Math.random() - 0.5) * 10),
      sensorStatus: "OK"
    };
  }
}

// ── MQTT Connection ───────────────────────────────────────
const client = mqtt.connect(BROKER_URL, {
  clientId: `SamudraGEN-ESP32-SIM-${Date.now()}`,
  clean: true,
});

const sim = new OWSCSimulator();

client.on("connect", () => {
  console.log(`✅ Connected to MQTT broker: ${BROKER_URL}`);
  console.log(`📡 Publishing to topic: ${TOPIC}`);
  console.log(`⏱️  Interval: ${INTERVAL_MS}ms`);
  console.log(`─────────────────────────────────────────`);

  // Publish immediately, then on interval
  publishTick();
  setInterval(publishTick, INTERVAL_MS);
});

client.on("error", (err) => {
  console.error("❌ MQTT connection error:", err.message);
  console.error("   Is Mosquitto running? Try: brew services start mosquitto");
});

function publishTick() {
  const payload = sim.tick();
  const json = JSON.stringify(payload);

  client.publish(TOPIC, json, { qos: 0 }, (err) => {
    if (err) {
      console.error("Publish error:", err);
    } else {
      console.log(`📤 ${payload.ts} | H:${payload.waveHeightCm / 100}m F:${payload.waveFreqHz}Hz | RPM:${payload.rpm} | ${payload.voltage}V × ${payload.current}A = ${payload.power}W`);
    }
  });
}
