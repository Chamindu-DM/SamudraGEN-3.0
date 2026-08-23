import { useTelemetryStore } from "../../store/telemetryStore";
import { toggleCsvPlayback } from "../../services/csvPlayback";

export function LiveBadge() {
    const isConnected = useTelemetryStore(state => state.isConnected);
    const latest = useTelemetryStore(state => state.latest);
    
    // It's live if connected to data stream and has telemetry
    const isActuallyLive = isConnected && latest !== null;

    const handleClick = () => {
        toggleCsvPlayback();
    };

    return(
        <button 
            type="button"
            onClick={handleClick}
            title={isActuallyLive ? "Live data streaming from CSV. Click to pause/disconnect." : "Offline. Click to go Live and stream data from Sheet1-Table 1.csv (from 160s)."}
            className={`px-3 py-1.5 rounded-lg outline outline-1 outline-offset-[-1px] flex justify-center items-center gap-2 transition-all cursor-pointer select-none border-none ${
                isActuallyLive 
                    ? 'bg-green-100 hover:bg-green-200 outline-green-800/20 shadow-xs active:scale-95' 
                    : 'bg-gray-100 hover:bg-gray-200 outline-gray-800/20 active:scale-95'
            }`}
        >
            <div className="relative flex h-2 w-2">
                {isActuallyLive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-2 w-2 transition-colors ${isActuallyLive ? 'bg-green-500' : 'bg-gray-400'}`}></span>
            </div>
            <div className={`text-center justify-start text-xs font-semibold font-['Inter'] uppercase transition-colors ${isActuallyLive ? 'text-green-800' : 'text-gray-500'}`}>
                {isActuallyLive ? 'Live' : 'Offline'}
            </div>
        </button>
    )
}