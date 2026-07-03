import './App.css'
import AppHeader from './components/layout/AppHeader'
import {Simulation} from './components/charts/Simulation'
import {DailyMetrics} from './components/charts/DailyMetrics'
import {PowerOutputChart} from './components/charts/PowerOutputChart'
import {VoltageCurrent} from './components/charts/VoltageCurrent'
import {WaveFreq} from './components/charts/WaveFreq'
import {WaveHeight} from './components/charts/WaveHeight'

function App() {
  return (
    <div className="w-screen h-screen bg-sky-50 flex flex-col justify-start items-start overflow-hidden">
      <AppHeader />
      <div className='flex-1 self-stretch p-2 flex flex-col justify-start items-start gap-2'>
        <div className='w-full h-full grid grid-cols-3 grid-rows-2 gap-2'>
          <Simulation/>
          <DailyMetrics/>
          <PowerOutputChart/>
          <VoltageCurrent/>
          <WaveFreq/>
          <WaveHeight/>
        </div>
      </div>
    </div>
  )
}

export default App
