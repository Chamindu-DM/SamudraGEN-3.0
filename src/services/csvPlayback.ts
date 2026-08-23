import { useTelemetryStore, type TelemetryTick } from "../store/telemetryStore";

let parsedTicksCache: TelemetryTick[] | null = null;
let playbackIntervalId: number | null = null;
let currentSecondIndex = 160;

/**
 * Fetches and parses Sheet1-Table 1.csv
 */
export async function loadCsvData(): Promise<TelemetryTick[]> {
  if (parsedTicksCache && parsedTicksCache.length > 0) {
    return parsedTicksCache;
  }

  let text: string;
  try {
    const res = await fetch('/Sheet1-Table 1.csv');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    text = await res.text();
  } catch {
    try {
      const res = await fetch('/data.csv');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      text = await res.text();
    } catch (e) {
      console.error("Failed to fetch CSV data:", e);
      return [];
    }
  }

  const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
  const ticks: TelemetryTick[] = [];

  // Line 0 is unit headers (e.g. ,rpm,cm,V,mA,,,,,,,,,,,,,)
  // Line 1 is column names (time,rpm,waveheight,voltage,current,power,,,,,,,,,,,,)
  // Data starts at line index 2
  for (let i = 2; i < lines.length; i++) {
    const parts = lines[i].split(',');
    if (parts.length < 6) continue;
    const timeStr = parts[0]?.trim();
    if (!timeStr || !timeStr.startsWith('20')) continue;

    const rpm = parseFloat(parts[1]) || 0;
    const waveHeightCm = parseFloat(parts[2]) || 0;
    const voltage = parseFloat(parts[3]) || 0;
    const currentVal = parseFloat(parts[4]) || 0; // in mA
    const power = parseFloat(parts[5]) || 0; // in W

    // Extract HH:MM:SS from ISO timestamp
    let ts = timeStr;
    if (timeStr.includes('T')) {
      ts = timeStr.split('T')[1].split('+')[0];
    }

    ticks.push({
      ts,
      waveHeight: parseFloat((waveHeightCm / 100).toFixed(4)), // in meters
      waveFreq: 0.2,
      rpm,
      voltage: parseFloat(voltage.toFixed(3)),
      current: parseFloat((currentVal / 1000).toFixed(4)), // in Amps
      power: parseFloat(power.toFixed(4)),
      relayMode: 'battery'
    });
  }

  parsedTicksCache = ticks;
  return ticks;
}

/**
 * Initializes dashboard data at the 160th second without starting playback.
 */
export async function initializeCsvDataAtSecond(startSecond: number = 160) {
  const ticks = await loadCsvData();
  if (ticks.length === 0) return;

  currentSecondIndex = Math.min(Math.max(0, startSecond), ticks.length - 1);
  const seedStartIndex = Math.max(0, currentSecondIndex - 60);
  const initialHistory = ticks.slice(seedStartIndex, currentSecondIndex + 1);

  const store = useTelemetryStore.getState();
  store.clearHistory();
  store.seedHistory(initialHistory);
  const currentTick = ticks[currentSecondIndex];
  store.pushTick(currentTick);
}

/**
 * Starts streaming CSV data starting from the specified second (default 160).
 */
export async function startCsvPlayback(startSecond: number = 160) {
  const ticks = await loadCsvData();
  if (ticks.length === 0) {
    console.error("No CSV ticks available to play");
    return;
  }

  stopCsvPlayback();

  // Clamp start index
  currentSecondIndex = Math.min(Math.max(0, startSecond), ticks.length - 1);

  // Pre-seed history with the preceding ~60 ticks up to startSecond
  const seedStartIndex = Math.max(0, currentSecondIndex - 60);
  const initialHistory = ticks.slice(seedStartIndex, currentSecondIndex + 1);

  const store = useTelemetryStore.getState();
  store.clearHistory();
  store.seedHistory(initialHistory);
  store.setConnected(true);

  // Set latest reading to the startSecond
  const currentTick = ticks[currentSecondIndex];
  store.pushTick(currentTick);

  // Stream each next second
  playbackIntervalId = window.setInterval(() => {
    currentSecondIndex++;
    if (currentSecondIndex >= ticks.length) {
      currentSecondIndex = 0; // Loop around
    }
    const nextTick = ticks[currentSecondIndex];
    useTelemetryStore.getState().pushTick(nextTick);
  }, 1000);
}

/**
 * Stops/pauses the playback
 */
export function stopCsvPlayback() {
  if (playbackIntervalId !== null) {
    clearInterval(playbackIntervalId);
    playbackIntervalId = null;
  }
  useTelemetryStore.getState().setConnected(false);
}

/**
 * Toggles playback on and off
 */
export async function toggleCsvPlayback() {
  const isConnected = useTelemetryStore.getState().isConnected;
  if (isConnected) {
    stopCsvPlayback();
  } else {
    await startCsvPlayback(160);
  }
}

/**
 * Check if playback is currently active
 */
export function isCsvPlaybackRunning(): boolean {
  return playbackIntervalId !== null;
}
