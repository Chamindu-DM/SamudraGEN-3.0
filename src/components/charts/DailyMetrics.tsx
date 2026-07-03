import { CommonCard } from "../ui/CommonCard";
import { Reading } from "../ui/Reading";
import Arrow from "../../assets/ArrowUp.svg?react"

export function DailyMetrics() {
    return (
        <div className="w-full h-full flex flex-col justify-start items-start overflow-hidden gap-2">
                    <div className="self-stretch h-full bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 inline-flex flex-col justify-start items-start">
                        <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                                <div className="text-left text-black text-lg font-medium">Daily Energy Metrics</div>
                        </div>
                        <div className="self-stretch p-4 inline-flex justify-start items-center gap-2">
                            <div className="w-full h-full p-2 bg-[#F4FAFF] rounded-lg outline outline-1 outline-blue-100 inline-flex flex-col justify-start items-start gap-1">
                    <div className="text-center justify-start text-black/60 text-[10px] font-medium font-['Inter'] uppercase">Voltage</div>
                    <div className="self-stretch inline-flex justify-between items-end">
                        <div className="text-center justify-start text-black text-lg font-semibold font-['Inter']">24V</div>
                        <div className="size- flex justify-center items-center gap-0.4">
                            <div className="size-3 relative overflow-hidden">
                                <Arrow className="size-2.5 text-green-800 stroke-green-800 stroke-[0.8px]" />
                            </div>
                            <div className="text-center justify-center text-green-800 text-xs font-medium font-['Inter'] uppercase">24%</div>
                        </div>
                    </div>
                    </div>
                    <Reading/>
                </div>
            </div>
            <CommonCard/>
        </div>
    )
}