import { useEffect, useState } from "react";
import Xicon from "../../assets/X.svg?react"
import { useTelemetryStore } from "../../store/telemetryStore";

function getStatus (rpm: number, power: number): "Normal" | "Critical" | "Warning" {
    if (rpm >= 270 || power >= 25 ) return "Critical";
    if (rpm >= 250 || power >= 22 ) return "Warning";
    return "Normal";
}

function statusDotClass(status: string): string{
    switch (status) {
        case "Normal": return "bg-green-500";
        case "Critical": return "bg-red-600";
        case "Warning": return "bg-amber-500";
        default: return "bg-gray-400";
    }
}

interface LogsPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

export function LogsPanel({ isOpen, onClose }: LogsPanelProps){
    const history = useTelemetryStore((state) => state.history);

    const [visible, setVisible] = useState(false);
    const [animating, setAnimating] = useState(false);

    useEffect(()=>{
        if (isOpen){
            setVisible(true);
            requestAnimationFrame(() => requestAnimationFrame(() => setAnimating(true)));
        } else {
            setAnimating(false);
            const timer = setTimeout(() => setVisible(false), 300);
            return () => clearTimeout(timer);
        }
        }, [isOpen]);

        if (!visible) return null;

        return(
            <div className="fixed top-[65px] bottom-0 left-0 right-0 z-40 overflow-hidden">
                {/* Backdrop */}
                <div className={`absolute inset-0 bg-black transition-opacity duration-300 ${
                    animating ? "opacity-10" : "opacity-0"
                }`}
                onClick={onClose}
                />
                {/* Side Panel */}
                <div className={`absolute top-0 right-0 h-full w-full max-w-[820px] min-w-[600px] bg-white outline outline-1 outline-blue-100 flex flex-col transition-transform duration-300 ease-out ${
                animating ? "translate-x-0" : "translate-x-full"}`}>
                
                {/* Header */}
                <div className="px-4 py-4 border-b border-blue-100 flex justify-between items-center">
                    <h2 className="text-black text-base font-semibold  uppercase m-0">Logs</h2>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg outline outline-1 outline-offset-[-1px] outline-black/10  hover:bg-gray-50 transition-colors cursor-pointer"
                        >
                            <Xicon className="size-4 text-black"/>
                        </button>
                </div>
                {/* Time range */}
                <div className="px-4 py-3 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <span className="text-black/80 text-xs font-semibold font-['Inter']">
                            Time Range
                        </span>
                        <span className="text-xs font-medium text-black/60 bg-gray-100 px-2 py-1 rounded">
                            Live Stream
                        </span>
                    </div>
                    <span className="text-black/70 text-[10px] font-medium font-['Inter']">
                        Showing real-time session logs
                    </span>
                </div>

                {/* Table container */}
                <div className="flex-1 flex flex-col border-t border-blue-100 overflow-hidden">
                    {/* Table header row */}
                    <div className="flex bg-sky-50 px-4 py-2 shrink-0 gap-4">
                        <div className="w-30 text-xs font-medium uppercase text-black/60">Time</div>
                        <div className="w-34 text-xs font-medium uppercase text-black/60">Status</div>
                        <div className="w-24 text-xs font-medium uppercase text-black/60">Gen RPM</div>
                        <div className="w-24 text-xs font-medium uppercase text-black/60">Power (W)</div>
                        <div className="w-24 text-xs font-medium uppercase text-black/60">Voltage (V)</div>
                        <div className="w-24 text-xs font-medium uppercase text-black/60">Current (A)</div>
                        <div className="w-24 text-xs font-medium uppercase text-black/60">Wave (m)</div>
                        <div className="w-20 text-xs font-medium uppercase text-black/60">Freq (Hz)</div>
                    </div>

                    {/* Table body (scrollable) */}
                    <div className="flex-1 overflow-y-auto">
                        {history.length === 0 ? (
                            <div className="p-8 text-center text-sm text-gray-500">
                                Waiting for telemetry data...
                            </div>
                        ) : (
                            [...history].reverse().map((log, index) => {
                                const status = getStatus(log.rpm, log.power);
                                return (
                                    <div
                                        key={index}
                                        className={`flex font-['Roboto_Mono'] text-xs text-black/80 px-4 py-2 gap-4 hover:bg-sky-50/50 transition-colors border-b border-gray-50 ${
                                            status === "Critical" ? "bg-red-50/40" : ""
                                        }`}
                                    >
                                        {/* 1. Time Column (w-20) */}
                                        <div className="w-30 text-[11px] text-black flex items-center">{log.ts}</div>
                                        
                                        {/* 2. Status Column (w-24) */}
                                        <div className="w-34 flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full ${statusDotClass(status)}`} />
                                            <span className="text-[11px] font-medium">{status}</span>
                                        </div> 
                                        
                                        {/* 3. Data Columns (all w-24) */}
                                        <div className="w-24 flex items-center whitespace-nowrap">{Number(log.rpm).toFixed(0)}</div>
                                        <div className="w-24 flex items-center whitespace-nowrap">{Number(log.power).toFixed(0)}</div>
                                        <div className="w-24 flex items-center whitespace-nowrap">{Number(log.voltage).toFixed(2)}</div>
                                        <div className="w-24 flex items-center whitespace-nowrap">{Number(log.current).toFixed(2)}</div>
                                        <div className="w-24 flex items-center whitespace-nowrap">{Number(log.waveHeight).toFixed(2)}</div>
                                        <div className="w-20 flex items-center whitespace-nowrap">{Number(log.waveFreq).toFixed(2)}</div>
                                    </div>
                                );
                            })
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}