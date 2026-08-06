import { useTelemetryStore } from "../../store/telemetryStore";
import { publishControlCommand } from "../../services/mqttClient";
import Logo from "../../assets/Logo.png";
import { LiveBadge } from "../ui/LiveBadge";

export default function AppHeader({onOpenLogs}: {onOpenLogs: () => void}) {

    const latest = useTelemetryStore(state => state.latest);
    const isLoadMode = latest?.relayMode === 'load';

    const handleToggle = () => {
        const newMode = isLoadMode ? 'battery' : 'load';
        publishControlCommand(newMode);
    };

    return (
        <div className="w-full p-4 bg-white border-b border-sky-500/20 inline-flex justify-between items-center">
            <div className="size- flex justify-start items-center">
                <img className="h-8" src={Logo} onDragStart={(e) => e.preventDefault()} />
            </div>
            <div 
                className="w-40 h-8 p-0.5 bg-sky-50 rounded-lg outline outline-1 outline-offset-[-1px] outline-blue-100 inline-flex justify-center items-center gap-0.5 cursor-pointer"
                onClick={handleToggle}
            >
                <div className={`flex-1 self-stretch rounded-md flex justify-center items-center gap-1.5 transition-all duration-200 ${!isLoadMode ? "bg-white shadow-[0px_0px_8px_0px_rgba(0,0,0,0.10)]" : ""}`}>
                    {!isLoadMode && <div className="w-1 h-1 relative bg-sky-500 rounded-full" />}
                    <div className={`justify-start text-xs font-semibold font-['Inter'] ${!isLoadMode ? "text-black" : "text-black/60"}`}>Battery</div>
                </div>
                <div className={`flex-1 self-stretch rounded-md flex justify-center items-center gap-1.5 transition-all duration-200 ${isLoadMode ? "bg-white shadow-[0px_0px_8px_0px_rgba(0,0,0,0.10)]" : ""}`}>
                    {isLoadMode && <div className="w-1 h-1 relative bg-orange-500 rounded-full" />}
                    <div className={`justify-start text-xs font-semibold font-['Inter'] ${isLoadMode ? "text-black" : "text-black/60"}`}>Load</div>
                </div>
            </div>
            <div className="size- flex justify-center items-center gap-2">
                <LiveBadge />
                <button
                    onClick={onOpenLogs}
                    className="h-8 px-3 py-2 rounded-lg outline outline-1 outline-offset-[-1px] outline-black/10 flex justify-center items-center gap-1.5 cursor-pointer hover:bg-gray-50 transition-colors bg-transparent border-none"
                >
                    <span className="text-black/80 text-xs font-semibold font-['Inter']">Open Logs</span>
                </button>
            </div>
        </div>
    );
}