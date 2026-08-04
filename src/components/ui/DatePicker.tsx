import { useState, useEffect, useRef } from "react";
import CaretDown from "../../assets/CaretDown.svg";

interface DatePickerProps {
    onSelectDate?: (date: string) => void;
}

export function DatePicker({ onSelectDate }: DatePickerProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isLive, setIsLive] = useState(true); // Track if actively streaming live
    const [selectedDate, setSelectedDate] = useState<Date | string>(() => new Date());
    const [availableDates, setAvailableDates] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // 1. Live minute timer (only runs when in live mode)
    useEffect(() => {
        if (!isLive) return;

        const msUntilNextMinute = 60000 - (Date.now() % 60000);
        let intervalId: ReturnType<typeof setInterval>;
        
        const timeoutId = setTimeout(() => {
            setSelectedDate(new Date());
            intervalId = setInterval(() => {
                setSelectedDate(new Date());
            }, 60000);
        }, msUntilNextMinute);

        return () => {
            clearTimeout(timeoutId);
            if (intervalId) clearInterval(intervalId);
        };
    }, [isLive]);

    // 2. Fetch available stored dates from DB API
    useEffect(() => {
        async function fetchStoredDates() {
            setLoading(true);
            try {
                // Generate last 7 days locally (since /dates endpoint doesn't exist)
                const dates = [];
                for (let i = 0; i < 7; i++) {
                    const d = new Date();
                    d.setDate(d.getDate() - i);
                    dates.push(d.toISOString().split('T')[0]);
                }
                setAvailableDates(dates);
            } catch (err) {
                console.error("Failed to fetch available dates", err);
            } finally {
                setLoading(false);
            }
        }
        fetchStoredDates();
    }, []);

    // 3. Click outside handler to close dropdown
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleSelect = (dateStr: string) => {
        setSelectedDate(dateStr);
        setIsLive(false); // Stop live auto-clock when historical date is selected
        setIsOpen(false);
        if (onSelectDate) {
            onSelectDate(dateStr);
        }
    };

    // Format current live date or display selected date string
    const formattedDisplay = selectedDate instanceof Date
        ? new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
          }).format(selectedDate)
        : selectedDate;

    return (
        <div className="relative inline-block" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen((prev) => !prev)}
                className="w-48 h-8 px-3 py-2 rounded-lg outline outline-1 outline-offset-[-1px] outline-black/10 flex justify-between items-center cursor-pointer hover:bg-gray-50 transition-colors"
            >
                <span className="text-black/80 text-xs font-semibold font-['Inter'] truncate">
                    {formattedDisplay}
                </span>
                <img className={`size-4 transform transition-transform ${isOpen ? "rotate-180" : ""}`} src={CaretDown} alt="toggle dropdown" />
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="w-48 p-1 left-0 top-[36px] absolute bg-white rounded-lg shadow-[0px_4px_12px_0px_rgba(0,0,0,0.20)] outline outline-1 outline-offset-[-1px] outline-black/10 flex flex-col gap-1 z-50">
                    {loading ? (
                        <div className="p-2 text-center text-xs text-black/50">Loading dates...</div>
                    ) : availableDates.length === 0 ? (
                        <div className="p-2 text-center text-xs text-black/50">No data found</div>
                    ) : (
                        availableDates.map((date) => {
                            const isSelected = String(formattedDisplay).includes(date);
                            return (
                                <button
                                    key={date}
                                    onClick={() => handleSelect(date)}
                                    className={`self-stretch p-2 rounded-sm text-left flex justify-start items-center cursor-pointer transition-colors text-xs font-medium font-['Inter'] ${
                                        isSelected 
                                            ? "bg-sky-50 outline outline-1 outline-offset-[-1px] outline-blue-100 text-sky-900"
                                            : "text-black/80 hover:bg-gray-100"
                                    }`}
                                >
                                    {date}
                                </button>
                            );
                        })
                    )}
                </div>
            )}
        </div>
    );
}
