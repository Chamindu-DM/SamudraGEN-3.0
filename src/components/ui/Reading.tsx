import Arrow from '../../assets/ArrowUp.svg?react'

interface ReadingProps {
    measurement: string;
    measureValue: number | string;
    measureUnit: string;
}

export function Reading({ measurement, measureValue, measureUnit }: ReadingProps) {
    return (
        <div className="reading-container">
            <div className="text-center justify-start text-black/60 text-[10px] font-medium font-['Inter'] uppercase">{measurement}</div>
            <div className="self-stretch inline-flex justify-between items-end">
                <div className="text-center justify-start text-black text-lg font-semibold font-['Inter']">{measureValue}{measureUnit}</div>
                <div className="size- flex justify-center items-center gap-0.4">
                    <div className="size-3 relative overflow-hidden">
                        <Arrow className="size-2.5 text-green-800 stroke-green-800 stroke-[0.8px]" />
                    </div>
                    <div className="text-center justify-center text-green-800 text-xs font-medium font-['Inter'] uppercase">24%</div>
                </div>
            </div>
        </div>
    )
}