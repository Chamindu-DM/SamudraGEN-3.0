export function Simulation(){
    return(
        <div className="w-full h-full bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 flex flex-col justify-start items-start overflow-hidden">
            <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                <div className="text-left text-black text-lg font-medium font-['Inter']">Real-time Ocean Simulation</div>
            </div>
            <div className="bg-blue-100 w-full h-full p-4 inline-flex flex-col justify-start items-start gap-2">
                <p>Chart goes here</p>
            </div>
        </div>
    )
}