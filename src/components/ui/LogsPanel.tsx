import { useEffect, useState, useMemo } from "react";
import Xicon from "../../assets/X.svg?react"
import CaretDownIcon from "../../assets/CaretDown.svg?react"
import { useTelemetryStore } from "../../store/telemetryStore";
import { DatePicker } from "./DatePicker";
import { fetchHistoricalData } from "../../services/dynamoClient";

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
    const store = useTelemetryStore();
    
    // UI state
    const [visible, setVisible] = useState(false);
    const [animating, setAnimating] = useState(false);
    const [selectedDate, setSelectedDate] = useState<string>("");
    
    // Pagination & Sorting State
    const [currentPage, setCurrentPage] = useState(0);
    const [sortColumn, setSortColumn] = useState<any>("");
    const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

    // Animation & Auto-fetch logic
    useEffect(()=>{
        if (isOpen){
            setVisible(true);
            requestAnimationFrame(() => requestAnimationFrame(() => setAnimating(true)));
            
            if (!selectedDate) {
                store.setHistoricalMode(false);
            }
        } else {
            setAnimating(false);
            const timer = setTimeout(() => setVisible(false), 300);
            return () => clearTimeout(timer);
        }
    }, [isOpen, selectedDate, store.historicalMode, store.startTime, store.endTime]);

    // Format date string for the label
    const formattedDateLabel = useMemo(() => {
        if (!selectedDate) return "";
        const dateObj = new Date(selectedDate);
        return new Intl.DateTimeFormat('en-US', {
            month: 'long', day: 'numeric', year: 'numeric'
        }).format(dateObj);
    }, [selectedDate]);

    // Data Fetching logic
    const handleFetchData = async (date: string, token: any = null) => {
        store.setIsFetchingHistory(true);
        try {
            const result = await fetchHistoricalData(date, token);
            store.setHistoricalLogs(result.items);
            setCurrentPage(0);
            store.setHistoricalMode(true);
        } catch (error) {
            console.error("Failed to fetch historical data", error);
            alert("Error fetching DynamoDB data. Did you set IAM permissions correctly?");
        } finally {
            store.setIsFetchingHistory(false);
        }
    };

    const handleDateSelect = (dateStr: string) => {
        setSelectedDate(dateStr);
        handleFetchData(dateStr, null);
    };

    const handleNextPage = () => setCurrentPage(p => p + 1);
    const handlePrevPage = () => setCurrentPage(p => Math.max(0, p - 1));

    const handleTimeChange = (type: 'startHour' | 'startMin' | 'endHour' | 'endMin', value: string) => {
        let [sH, sM] = store.startTime.split(":");
        let [eH, eM] = store.endTime.split(":");

        if (type === 'startHour') sH = value;
        if (type === 'startMin') sM = value;
        if (type === 'endHour') eH = value;
        if (type === 'endMin') eM = value;

        const newStart = `${sH}:${sM}`;
        const newEnd = `${eH}:${eM}`;
        
        store.setTimeRange(newStart, newEnd);
        // We no longer fetch on time change, we just filter the already fetched displayLogs locally!
    };

    // Determine which logs to show
    let displayLogs = (store.historicalMode ? store.historicalLogs : store.history).filter(log => {
        if (!store.historicalMode) return true; // Don't filter live stream
        let logTimeStr = log.ts;
        if (log.ts.includes("T")) {
            logTimeStr = log.ts.split("T")[1].split(".")[0];
        }
        const logTime = logTimeStr.slice(0, 5); // "HH:MM"
        return logTime >= store.startTime && logTime <= store.endTime;
    });

    if (sortColumn) {
        displayLogs = [...displayLogs].sort((a: any, b: any) => {
            const valA = a[sortColumn];
            const valB = b[sortColumn];
            if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }

    const totalPages = Math.ceil(displayLogs.length / 100);
    const paginatedLogs = store.historicalMode ? displayLogs.slice(currentPage * 100, (currentPage + 1) * 100) : displayLogs;

    const formatTimeDisplay = (ts: string) => {
        if (ts.includes("T")) {
            const parts = ts.split("T");
            const dateParts = parts[0].split("-");
            const monthDay = `${dateParts[1]}/${dateParts[2]}`;
            const timePart = parts[1].split(".")[0].split("+")[0];
            return `${monthDay}, ${timePart}`;
        }
        return ts;
    };

    const isLive = !store.historicalMode;

    const SortHeader = ({ label, column, width }: { label: string, column: any, width: string }) => {
        const isActive = sortColumn === column;
        return (
            <div 
                className={`${width} text-xs font-medium uppercase text-black/60 flex items-center gap-1 cursor-pointer hover:text-black/80 select-none`}
                onClick={() => {
                    if (!column) return;
                    if (isActive) {
                        setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
                    } else {
                        setSortColumn(column);
                        setSortDirection('desc');
                    }
                }}
            >
                {label}
                {column && (
                    <div className={`flex justify-center transition-transform duration-200 ${
                        isActive ? "opacity-100" : "opacity-30"
                    } ${
                        isActive && sortDirection === 'asc' ? "rotate-180" : ""
                    }`}>
                        <CaretDownIcon className="w-3 h-3" />
                    </div>
                )}
            </div>
        )
    };

    const TimeSelect = ({ value, onChange, max }: { value: string, onChange: (val: string) => void, max: number }) => (
        <select 
            className="w-full h-full text-center text-black/80 text-xs font-semibold font-['Inter'] appearance-none bg-transparent outline-none cursor-pointer"
            value={value}
            onChange={(e) => onChange(e.target.value)}
        >
            {Array.from({length: max + 1}).map((_, i) => {
                const num = i.toString().padStart(2, '0');
                return <option key={num} value={num}>{num}</option>
            })}
        </select>
    );

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
            <div className={`absolute top-0 right-0 h-full w-full max-w-[920px] min-w-[600px] bg-white outline outline-1 outline-blue-100 flex flex-col transition-transform duration-300 ease-out ${
            animating ? "translate-x-0" : "translate-x-full"}`}>
            
            {/* Header */}
            <div className="px-4 py-4 border-b border-blue-100 flex justify-between items-center">
                <div className="flex items-center gap-4">
                    <h2 className="text-black text-base font-semibold uppercase m-0">Logs</h2>
                    <DatePicker onSelectDate={handleDateSelect} />
                    {store.historicalMode && (
                        <button 
                            onClick={() => {
                                setSelectedDate("");
                                store.setHistoricalMode(false);
                            }}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium px-2 py-1 rounded hover:bg-blue-50 transition-colors"
                        >
                            Return to Live Stream
                        </button>
                    )}
                </div>
                <button
                    onClick={onClose}
                    className="p-2 rounded-lg outline outline-1 outline-offset-[-1px] outline-black/10 hover:bg-gray-50 transition-colors cursor-pointer"
                >
                    <Xicon className="size-4 text-black"/>
                </button>
            </div>

            {/* Time range */}
            {isLive ? (
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
            ) : (
                <div className="px-4 py-2 flex justify-between items-center bg-gray-50/50">
                    <div className="flex items-center gap-3">
                        <div className="text-black/80 text-xs font-semibold font-['Inter']">Time Range</div>
                        
                        {/* Start Time */}
                        <div className="p-1 rounded-lg outline outline-1 outline-offset-[-1px] outline-black/10 flex justify-center items-center gap-1 bg-white">
                            <div className="size-6 rounded-sm outline outline-1 outline-offset-[-1px] outline-black/5 flex justify-center items-center hover:bg-gray-50">
                                <TimeSelect value={store.startTime.split(':')[0]} onChange={(v) => handleTimeChange('startHour', v)} max={23} />
                            </div>
                            <div className="text-black/80 text-xs font-semibold font-['Inter']">:</div>
                            <div className="size-6 rounded-sm outline outline-1 outline-offset-[-1px] outline-black/5 flex justify-center items-center hover:bg-gray-50">
                                <TimeSelect value={store.startTime.split(':')[1]} onChange={(v) => handleTimeChange('startMin', v)} max={59} />
                            </div>
                        </div>

                        {/* End Time */}
                        <div className="p-1 rounded-lg outline outline-1 outline-offset-[-1px] outline-black/10 flex justify-center items-center gap-1 bg-white">
                            <div className="size-6 rounded-sm outline outline-1 outline-offset-[-1px] outline-black/5 flex justify-center items-center hover:bg-gray-50">
                                <TimeSelect value={store.endTime.split(':')[0]} onChange={(v) => handleTimeChange('endHour', v)} max={23} />
                            </div>
                            <div className="text-black/80 text-xs font-semibold font-['Inter']">:</div>
                            <div className="size-6 rounded-sm outline outline-1 outline-offset-[-1px] outline-black/5 flex justify-center items-center hover:bg-gray-50">
                                <TimeSelect value={store.endTime.split(':')[1]} onChange={(v) => handleTimeChange('endMin', v)} max={59} />
                            </div>
                        </div>
                    </div>
                    <div className="text-black/70 text-[10px] font-medium font-['Inter']">
                        Showing logs for {formattedDateLabel} ({store.startTime} – {store.endTime} UTC)
                    </div>
                </div>
            )}

            {/* Table container */}
            <div className="flex-1 flex flex-col border-t border-blue-100 overflow-hidden">
                {/* Table header row */}
                <div className="flex bg-sky-50 px-4 py-2 shrink-0 gap-4">
                    <SortHeader label="Time" column="ts" width="w-30" />
                    <SortHeader label="Status" column="" width="w-24" />
                    <SortHeader label="Gen RPM" column="rpm" width="w-20" />
                    <SortHeader label="Power (W)" column="power" width="w-24" />
                    <SortHeader label="Voltage (V)" column="voltage" width="w-24" />
                    <SortHeader label="Current (A)" column="current" width="w-24" />
                    <SortHeader label="Wave (m)" column="waveHeight" width="w-24" />
                    <SortHeader label="Freq (Hz)" column="waveFreq" width="w-20" />
                </div>

                {/* Table body (scrollable) */}
                <div className="flex-1 overflow-y-auto">
                    {store.isFetchingHistory ? (
                        <div className="p-8 text-center text-sm text-black/50">Fetching from DynamoDB...</div>
                    ) : displayLogs.length === 0 ? (
                        <div className="p-8 text-center text-sm text-gray-500">
                            {isLive ? "Waiting for telemetry data..." : "No data found for this time range."}
                        </div>
                    ) : (
                        paginatedLogs.map((log, index) => {
                            const status = getStatus(log.rpm, log.power);
                            return (
                                <div
                                    key={index}
                                    className={`flex font-['Roboto_Mono'] text-xs text-black/80 px-4 py-2 gap-4 hover:bg-sky-50/50 transition-colors border-b border-gray-50 ${
                                        status === "Critical" ? "bg-red-50/40" : ""
                                    }`}
                                >
                                    {/* 1. Time Column (w-20) */}
                                    <div className="w-30 text-[11px] text-black flex items-center">{formatTimeDisplay(log.ts)}</div>
                                    
                                    {/* 2. Status Column (w-24) */}
                                    <div className="w-24 flex items-center gap-2">
                                        <div className={`w-2 h-2 rounded-full ${statusDotClass(status)}`} />
                                        <span className="text-[11px] font-medium">{status}</span>
                                    </div> 
                                    
                                    {/* 3. Data Columns (all w-24) */}
                                    <div className="w-20 flex items-center whitespace-nowrap">{Number(log.rpm).toFixed(0)}</div>
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

                {/* Pagination (Only in Historical Mode) */}
                {store.historicalMode && (
                    <div className="px-4 py-3 border-t border-blue-100 flex justify-between items-center bg-gray-50">
                        <div className="text-xs text-black/60 font-medium">
                            {displayLogs.length} rows (Page {currentPage + 1} of {Math.max(1, totalPages)})
                        </div>
                        <div className="flex gap-2">
                            <button 
                                onClick={handlePrevPage}
                                disabled={currentPage === 0}
                                className="px-3 py-1.5 text-xs font-semibold rounded outline outline-1 outline-black/10 bg-white hover:bg-gray-100 disabled:opacity-50 flex items-center gap-1.5"
                            >
                                <CaretDownIcon className="w-3 h-3 rotate-90" />
                                Previous
                            </button>
                            <button 
                                onClick={() => setCurrentPage(0)}
                                disabled={currentPage === 0}
                                className="px-3 py-1.5 text-xs font-semibold rounded outline outline-1 outline-black/10 bg-white hover:bg-gray-100 disabled:opacity-50"
                            >
                                First Page
                            </button>
                            <button 
                                onClick={handleNextPage}
                                disabled={currentPage >= totalPages - 1}
                                className="px-3 py-1.5 text-xs font-semibold rounded outline outline-1 outline-black/10 bg-white hover:bg-gray-100 disabled:opacity-50 flex items-center gap-1.5"
                            >
                                Next 100
                                <CaretDownIcon className="w-3 h-3 -rotate-90" />
                            </button>
                        </div>
                    </div>
                )}
            </div>
            
          </div>
        </div>
    );
}