import { useEffect } from 'react'
import { useTelemetryStore } from './store/telemetryStore'
import './App.css'
import AppHeader from './components/layout/AppHeader'
import { Simulation } from './components/charts/Simulation'
import { DailyMetrics } from './components/charts/DailyMetrics'
import { PowerOutputChart } from './components/charts/PowerOutputChart'
import { VoltageCurrent } from './components/charts/VoltageCurrent'
import { WaveFreq } from './components/charts/WaveFreq'
import { WaveHeight } from './components/charts/WaveHeight'
import { LogsPanel } from './components/ui/LogsPanel'
import { useState } from 'react'

function App() {
  const [isLogsPanelOpen, setIsLogsPanelOpen] = useState(false);

  // 🚨 TEMPORARY: Simulate incoming data to test the LogsPanel 🚨
  useEffect(() => {
    const interval = setInterval(() => {
      // Create a fake tick
      const fakeTick = {
        ts: new Date().toLocaleTimeString('en-US', { hour12: false }), // HH:MM:SS
        waveHeight: 1.2 + Math.random() * 0.5,
        waveFreq: 0.15 + Math.random() * 0.05,
        rpm: Math.floor(220 + Math.random() * 70), // Random RPM between 220-290
        power: Math.floor(20 + Math.random() * 10),
        voltage: 12 + Math.random() * 2,
        current: 1.5 + Math.random() * 0.5,
      };
      // Push it to the Zustand store!
      useTelemetryStore.getState().pushTick(fakeTick);
    }, 2000); // Every 2 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-screen h-screen bg-sky-50 flex flex-col justify-start items-start">
      <AppHeader onOpenLogs={() => setIsLogsPanelOpen(true)} />
      <div className='flex-1 self-stretch p-2 flex flex-col justify-start items-start gap-2'>
        <div className='w-full flex flex-col md:grid md:grid-cols-3 md:grid-rows-2 md:h-full gap-2'>
          <Simulation />
          <DailyMetrics />
          <PowerOutputChart />
          <VoltageCurrent />
          <WaveFreq />
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
