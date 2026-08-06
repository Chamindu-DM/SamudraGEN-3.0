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
  relayMode?: string;  // "battery" | "load"
}


export interface TelemetryState {
  // Latest single reading (for gauges, badges, Reading components)
  latest: TelemetryTick | null;

  // Rolling buffer for time-series charts (last N ticks)
  history: TelemetryTick[];
  maxHistory: number;           // e.g., 200 ticks = ~16 min at 5s intervals

  // Connection status
  isConnected: boolean;
  
  // Historical Logs
  historicalMode: boolean;
  historicalLogs: TelemetryTick[];
  isFetchingHistory: boolean;
  startTime: string; // HH:mm
  endTime: string;   // HH:mm

  // Actions
  pushTick: (tick: TelemetryTick) => void;
  setConnected: (status: boolean) => void;
  clearHistory: () => void;
  seedHistory: (ticks: TelemetryTick[]) => void;
  
  // Historical Actions
  setHistoricalMode: (mode: boolean) => void;
  setHistoricalLogs: (logs: TelemetryTick[]) => void;
  setIsFetchingHistory: (isFetching: boolean) => void;
  setTimeRange: (start: string, end: string) => void;
}

export const useTelemetryStore = create<TelemetryState>((set, _get) => ({
  latest: null,
  history: [],
  maxHistory: 200,
  isConnected: false,
  
  historicalMode: false,
  historicalLogs: [],
  isFetchingHistory: false,
  startTime: "00:00",
  endTime: "23:59",
  
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
           
  setHistoricalMode: (mode) => set({ historicalMode: mode }),
  setHistoricalLogs: (logs) => set({ historicalLogs: logs }),
  setIsFetchingHistory: (isFetching) => set({ isFetchingHistory: isFetching }),
  setTimeRange: (start, end) => set({ startTime: start, endTime: end }),
}));