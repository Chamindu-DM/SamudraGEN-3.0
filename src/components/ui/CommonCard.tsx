import {Reading} from "../ui/Reading"

export function CommonCard (){
    return(
         <div className="w-full h-full bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 flex flex-col justify-start items-start overflow-hidden">
                    <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                        <div className="text-left text-black text-lg font-medium">Voltage &amp; Current</div>
                    </div>
                    <div className="w-full h-full p-4">
                        <p>chart goes here</p>
                    </div>
                    <div className="self-stretch px-4 pt-2 pb-4 inline-flex justify-start items-center gap-2">
                        <Reading/>
                        <Reading/>
                    </div>
                </div>
    )
}