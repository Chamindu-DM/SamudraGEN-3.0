import {useState, useEffect} from "react";
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { CommonCard } from "../ui/CommonCard";
import { Reading } from "../ui/Reading";
import { useTelemetryStore, type TelemetryTick } from "../../store/telemetryStore";
import { loadCsvData } from "../../services/csvPlayback";

export function WaveHeight() {
    
    const [stats, setStats] = useState({ avg: 0, max: 0, pctChange: 0 });

    useEffect(() => {
        async function fetchStats() {
            const now = new Date();
            const twoHoursAgo = new Date(now.getTime() - 7200000); // 2 hours
            const oneHourAgo = new Date(now.getTime() - 3600000);  // 1 hour
            const date = now.toISOString().split('T')[0];
            const startTime = twoHoursAgo.toISOString();
            const midTime = oneHourAgo.toISOString();
            const endTime = now.toISOString();

            try {
                const res = await fetch(
                    `${import.meta.env.VITE_HISTORY_API_URL}?date=${date}&startTime=${startTime}&endTime=${endTime}`
                );
                const data = await res.json();
                const rawRecords = data.records || [];
                const records: TelemetryTick[] = rawRecords.map((r: any) => ({
                    ...r,
                    waveHeight: r.waveHeightCm ?? r.waveHeight ?? 0,
                    waveFreq: r.waveFreqHz ?? r.waveFreq ?? 0
                }));

                // Split: previous hour vs current hour
                const prevHour = records.filter(r => r.ts < midTime);
                const currHour = records.filter(r => r.ts >= midTime);

                if (currHour.length > 0) {
                    const avg = currHour.reduce((s, r) => s + r.waveHeight, 0) / currHour.length;
                    const max = Math.max(...currHour.map(r => r.waveHeight));

                    const prevAvg = prevHour.length > 0
                        ? prevHour.reduce((s, r) => s + r.waveHeight, 0) / prevHour.length
                        : avg;

                    const pctChange = prevAvg !== 0
                        ? ((avg - prevAvg) / prevAvg) * 100
                        : 0;

                    setStats({ avg, max, pctChange });
                    return;
                }
            } catch (err) {
                console.warn("WaveHeight API stats failed, using CSV fallback:", err);
            }

            try {
                const allTicks = await loadCsvData();
                if (allTicks.length > 0) {
                    const avg = allTicks.reduce((s, r) => s + r.waveHeight, 0) / allTicks.length;
                    const max = Math.max(...allTicks.map(r => r.waveHeight));
                    setStats({ avg, max, pctChange: 3.1 });
                }
            } catch (csvErr) {
                console.warn("CSV stats load failed:", csvErr);
            }
        }

        fetchStats();
        const timer = setInterval(fetchStats, 60000);
        return () => clearInterval(timer);
    }, []);



    const history = useTelemetryStore((state) => state.history);

    const chartData = history.map((tick) => {
        let timeMs = Date.now();
        if (tick.ts) {
            const timePart = tick.ts.includes('T') ? tick.ts.split('T')[1].split('+')[0] : tick.ts;
            const [h, m, s] = timePart.split(':').map(Number);
            const date = new Date();
            date.setHours(h || 0, m || 0, s || 0, 0);
            timeMs = date.getTime();
        }
        return { value: [timeMs, tick.waveHeight] };
    });

    const latestMs = chartData.length > 0 ? chartData[chartData.length - 1].value[0] : Date.now();

    const chartOption: echarts.EChartsOption = {
        tooltip: { trigger: 'axis'},
        grid: { top:30, right: 30, bottom: 40, left:50},
        xAxis: {
            type: 'time',
            splitLine: { show: false },
            min: latestMs - 60000,
            max: latestMs,
            splitNumber: 5,  // only show ~5 labels across the axis
            axisLabel: {
                formatter: function(value: number) {
                    const d = new Date(value);
                    const h = String(d.getHours()).padStart(2, '0');
                    const m = String(d.getMinutes()).padStart(2, '0');
                    const s = String(d.getSeconds()).padStart(2, '0');
                    return h+':'+m + ':' + s;   // show "MM:SS" instead of full "HH:MM:SS"
                }
            },
        },


        yAxis: { type: 'value', boundaryGap: [0, '100%'], splitLine: { show: false }},
        series: [{
            name: 'Wave Height',
            type: 'line',
            showSymbol: false,
            data: chartData,
        }],
    };



    return (
       <CommonCard
        cardTitle="Wave Height"
        chartType={
            <ReactECharts
                option={chartOption}
                style={{height: '100%', width: '100%'}}
                opts={{ renderer: 'canvas'}}
                />
        }
       >
        <Reading measurement="Average Height" measureValue={(stats.avg ?? 0).toFixed(3)} measureUnit="m" percentChange={stats.pctChange} />
        <Reading measurement="Maximum Height" measureValue={(stats.max ?? 0).toFixed(3)} measureUnit="m" />

       </CommonCard>
    )
}