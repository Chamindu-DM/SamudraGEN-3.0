export function LiveBadge() {
    return(
        <div className="size- px-3 py-2 bg-green-100 rounded-lg outline outline-1 outline-offset-[-1px] outline-green-800/10 flex justify-center items-center gap-2">
            <div className="size-2 bg-green-500 rounded-full" />
            <div className="text-center justify-start text-green-800 text-xs font-semibold font-['Inter'] uppercase">Live</div>
        </div>
    )
}