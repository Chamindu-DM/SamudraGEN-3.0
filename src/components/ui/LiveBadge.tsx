import { useTelemetryStore } from "../../store/telemetryStore";
import { startCsvPlayback, stopCsvPlayback, isCsvPlaybackRunning } from "../../services/csvPlayback";

interface LiveBadgeProps {
    onTriggerEasterEgg?: () => void;
}

export function LiveBadge({ onTriggerEasterEgg }: LiveBadgeProps) {
    const isConnected = useTelemetryStore(state => state.isConnected);
    const latest = useTelemetryStore(state => state.latest);
    
    // It's live if connected to data stream and has telemetry
    const isActuallyLive = isConnected && latest !== null;
    const isCsvRunning = isCsvPlaybackRunning();

    const handleClick = () => {
        if (!isActuallyLive || !isCsvRunning) {
            // Easter egg: start CSV simulation from 160s and open side panel
            startCsvPlayback(160).then(() => {
                useTelemetryStore.getState().setHistoricalMode(false);
                onTriggerEasterEgg?.();
            });
        } else {
            // If CSV easter egg is currently running, stop it and return to listening for real MQTT telemetry
            stopCsvPlayback();
            useTelemetryStore.getState().setConnected(false);
            if (import.meta.env.VITE_AWS_IOT_ENDPOINT) {
                import("../../services/mqttClient").then(({ connectMqttClient }) => {
                    connectMqttClient();
                });
            }
        }
    };

    return(
        <button 
            type="button"
            onClick={handleClick}
            title={
                isActuallyLive 
                    ? (isCsvRunning 
                        ? "Easter Egg active: Streaming from Sheet1-Table 1.csv. Click to stop and return to live MQTT." 
                        : "Live: Receiving telemetry from AWS IoT Core.")
                    : "Offline. (Easter egg: click to stream CSV telemetry from 160s & view logs)"
            }
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