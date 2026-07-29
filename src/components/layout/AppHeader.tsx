import Logo from "../../assets/Logo.png";
import {LiveBadge} from "../ui/LiveBadge"
import { DatePicker } from "../ui/DatePicker";

export default function AppHeader() {
    const handleDateSelect = (selectedDate: string) => {
        console.log("Fetching historical DB data for:", selectedDate);
    };

    return (
    <div className="self-stretch p-4 bg-white border-b border-sky-500/20 inline-flex justify-between items-center">
        <div className="size- flex justify-start items-center">
            <img className="h-8" src={Logo} onDragStart={(e)=>e.preventDefault()} />
        </div>
        <div className="size- flex justify-center items-center gap-2">
            <LiveBadge/>
            <DatePicker onSelectDate={handleDateSelect} />
        </div>
    </div>
    );
}