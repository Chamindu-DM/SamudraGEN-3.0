// Global state management
// Zustand store: grabs MQTT data and feeds it to UI/3D
interface TelemetryTick {
  ts: string;          // "HH:MM:SS"
  waveHeight: number;  // meters
  waveFreq: number;    // Hz
  rpm: number;         // generator RPM
  power: number;       // watts (V × I)
  voltage: number;     // volts
  current: number;     // amps
}

interface TelemetryState {
  // Latest single reading (for gauges, badges, Reading components)
  latest: TelemetryTick | null;

  // Rolling buffer for time-series charts (last N ticks)
  history: TelemetryTick[];
  maxHistory: number;           // e.g., 200 ticks = ~16 min at 5s intervals

  // Connection status
  isConnected: boolean;

  // Actions
  pushTick: (tick: TelemetryTick) => void;
  setConnected: (status: boolean) => void;
  clearHistory: () => void;
}