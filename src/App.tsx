import { useState, useEffect } from 'react'
import { initializeCsvDataAtSecond } from './services/csvPlayback'
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
    // Initialize data from CSV at 160th second
    initializeCsvDataAtSecond(160);

    // If AWS endpoint is configured and active, connect to real MQTT
    if (import.meta.env.VITE_AWS_IOT_ENDPOINT && import.meta.env.VITE_USE_AWS === 'true') {
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


  return (
    <div className="w-screen h-screen bg-sky-50 flex flex-col justify-start items-start">
      <AppHeader onOpenLogs={() => setIsLogsPanelOpen(true)} />
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
