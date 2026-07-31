import Arrow from '../../assets/ArrowUp.svg?react'

interface ReadingProps {
    measurement: string;
    measureValue: number | string;
    measureUnit: string;
    percentChange?: number;
}

export function Reading({ measurement, measureValue, measureUnit, percentChange }: ReadingProps) {
    
    const isPositive = (percentChange ?? 0) >= 0;
    
    return (
        <div className="reading-container">
            <div className="text-center justify-start text-black/60 text-[10px] font-medium font-['Inter'] uppercase">{measurement}</div>
            <div className="self-stretch inline-flex justify-between items-end">
                <div className="text-center justify-start text-black text-lg font-semibold font-['Inter']">{measureValue}{measureUnit}</div>
                {percentChange !== undefined && (
                    <div className="size- flex justify-center items-center gap-0.4">
                    <div className="size-3 relative overflow-hidden">
                        <Arrow className={`size-2.5 stroke-[0.8px] ${
                            isPositive
                            ? 'text-green-800 stroke-green-800'
                            : 'text-red-600 stroke-red-600 rotate-180'
                        }`}
                        />
                    </div>
                    <div className={`text-center justify-center text-green-800 text-xs font-medium font-['Inter'] uppercase
                        ${isPositive ? 'text-green-800' : 'text-red-600'}`}>
                            {Math.abs(percentChange).toFixed(0)}%
                    </div>
                </div>
                )}
            </div>
        </div>
    )
}