import { useState, useEffect } from 'react'
import { useTelemetryStore } from './store/telemetryStore'
import './App.css'
import AppHeader from './components/layout/AppHeader'
import { Simulation } from './components/charts/Simulation'
import { DailyMetrics } from './components/charts/DailyMetrics'
import { PowerOutputChart } from './components/charts/PowerOutputChart'
import { WaveHeight } from './components/charts/WaveHeight'
import { LogsPanel } from './components/ui/LogsPanel'
import { Voltage } from './components/charts/Voltage'
import { Current } from './components/charts/Current'

function App() {
  const [isLogsPanelOpen, setIsLogsPanelOpen] = useState(false);

  useEffect(() => {
    // Listen to real-time live telemetry data from AWS IoT Core MQTT
    if (import.meta.env.VITE_AWS_IOT_ENDPOINT) {
      import('./services/mqttClient').then(({ connectMqttClient }) => {
        connectMqttClient();
      });

      return () => {
        import('./services/mqttClient').then(({ disconnectMqttClient }) => {
          disconnectMqttClient();
        });
      };
    }
  }, []);

  // Backfill: fetch recent historical data so charts have initial history on load
  useEffect(() => {
    async function backfill() {
      if (!import.meta.env.VITE_HISTORY_API_URL) return;
      const now = new Date();
      const fiveMinAgo = new Date(now.getTime() - 300000);
      const date = now.toISOString().split('T')[0];
      const startTime = fiveMinAgo.toISOString();
      const endTime = now.toISOString();
      try {
        const res = await fetch(
          `${import.meta.env.VITE_HISTORY_API_URL}?date=${date}&startTime=${startTime}&endTime=${endTime}`
        );
        const data = await res.json();
        const records = data.records || [];
        if (records.length > 0) {
          useTelemetryStore.getState().seedHistory(records);
        }
      } catch (err) {
        console.warn("Backfill failed (API may not be deployed yet):", err);
      }
    }
    backfill();
  }, []);

  return (
    <div className="w-screen h-screen bg-sky-50 flex flex-col justify-start items-start">
      <AppHeader 
        onOpenLogs={() => setIsLogsPanelOpen(true)} 
        onTriggerEasterEgg={() => setIsLogsPanelOpen(true)}
      />
      <div className='flex-1 self-stretch p-2 flex flex-col justify-start items-start gap-2'>
        <div className='w-full flex flex-col md:grid md:grid-cols-3 md:grid-rows-2 md:h-full gap-2'>
          <Simulation />
          <DailyMetrics />
          <PowerOutputChart />
          <Voltage/>
          <Current/>
          <WaveHeight />
        </div>
        <LogsPanel
          isOpen={isLogsPanelOpen}
          onClose={()=> setIsLogsPanelOpen(false)}
        />
      </div>
    </div>
  )
}

export default App
