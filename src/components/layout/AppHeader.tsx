import Logo from "../../assets/Logo.png";
import { LiveBadge } from "../ui/LiveBadge"

interface AppHeaderProps {
    onOpenLogs: () => void;
}

export default function AppHeader({onOpenLogs}: AppHeaderProps) {
    return (
        <div className="self-stretch p-4 bg-white border-b border-sky-500/20 inline-flex justify-between items-center">
            <div className="size- flex justify-start items-center">
                <img className="h-8" src={Logo} onDragStart={(e) => e.preventDefault()} />
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