import { ReactNode } from "react";

interface CommonCardProps {
    cardTitle: string;
    chartType?: ReactNode; // A React component or element for the chart
    children?: ReactNode;  // For passing Reading components inside
}

export function CommonCard({ cardTitle, chartType, children }: CommonCardProps) {
    return (
        <div className="w-full h-full bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 flex flex-col justify-start items-start overflow-hidden">
            <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                <div className="card-title">{cardTitle}</div>
            </div>
            <div className="w-full h-full">
                {chartType ? chartType : <p>chart goes here</p>}
            </div>
            {children && (
                <div className="self-stretch px-4 pb-4 inline-flex justify-start items-center gap-2">
                    {children}
                </div>
            )}
        </div>
    )
}