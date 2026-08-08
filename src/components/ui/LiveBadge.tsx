import { useTelemetryStore } from "../../store/telemetryStore";

export function LiveBadge() {
    const isConnected = useTelemetryStore(state => state.isConnected);
    const latest = useTelemetryStore(state => state.latest);
    
    // It's only truly live if we're connected to MQTT AND we've received at least one telemetry packet
    const isActuallyLive = isConnected && latest !== null;

    return(
        <div className={`px-3 py-2 rounded-lg outline outline-1 outline-offset-[-1px] flex justify-center items-center gap-2 transition-colors ${isActuallyLive ? 'bg-green-100 outline-green-800/10' : 'bg-gray-100 outline-gray-800/10'}`}>
            <div className="relative flex h-2 w-2">
                {isActuallyLive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-2 w-2 transition-colors ${isActuallyLive ? 'bg-green-500' : 'bg-gray-400'}`}></span>
            </div>
            <div className={`text-center justify-start text-xs font-semibold font-['Inter'] uppercase transition-colors ${isActuallyLive ? 'text-green-800' : 'text-gray-500'}`}>
                {isActuallyLive ? 'Live' : 'Offline'}
            </div>
        </div>
    )
}