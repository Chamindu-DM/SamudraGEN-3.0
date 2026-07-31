// Global state management
// Zustand store: grabs MQTT data and feeds it to UI/3D
import { create } from 'zustand';

export interface TelemetryTick {
  ts: string;          // "HH:MM:SS"
  waveHeight: number;  // meters
  waveFreq: number;    // Hz
  rpm: number;         // generator RPM
  power: number;       // watts (V × I)
  voltage: number;     // volts
  current: number;     // amps
}

export interface TelemetryState {
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
  seedHistory: (ticks: TelemetryTick[]) => void;
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  latest: null,
  history: [],
  maxHistory: 200,
  isConnected: false,
  pushTick: (tick) => set((state) => {
    const newHistory = [...state.history, tick].slice(-state.maxHistory);
    return {
      latest: tick,
      history: newHistory,
    };
  }),
  setConnected: (status) => set({ isConnected: status }),
  clearHistory: () => set({ history: [], latest: null }),
  seedHistory: (ticks) => set((state) => {
             if (state.history.length > 0) return state;
             return { history: ticks, latest: ticks[ticks.length - 1] || null };
           }),
}));