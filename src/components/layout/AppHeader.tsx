import Logo from "../../assets/Logo.png";
import CaretDown from '../../assets/CaretDown.svg'
import {LiveBadge} from "../ui/LiveBadge"

export default function AppHeader() {
    return (
    <div className="self-stretch p-4 bg-white border-b border-sky-500/20 inline-flex justify-between items-center">
        <div className="size- flex justify-start items-center">
            <img className="h-8" src={Logo} onDragStart={(e)=>e.preventDefault()} />
        </div>
        <div className="size- flex justify-center items-center gap-4">
            <div className="size- px-3 py-2 rounded-lg outline outline-1 outline-offset-[-1px] outline-black/10 flex justify-center items-center gap-2">
                <div className="text-center justify-start text-black/80 text-xs font-semibold font-['Inter']">Jul 3, 2026, 10:30 AM</div>
                <img className="size-4" src={CaretDown}/>
            </div>
            <LiveBadge/>
        </div>
    </div>
    )
}