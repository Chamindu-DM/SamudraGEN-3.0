import {useState, useEffect} from "react";
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { CommonCard } from "../ui/CommonCard";
import { Reading } from "../ui/Reading";
import { useTelemetryStore, type TelemetryTick } from "../../store/telemetryStore";

export function Voltage() {

    const [stats, setStats] = useState({ avg: 0, max: 0, pctChange: 0 });

    useEffect(() => {
        async function fetchStats() {
            const now = new Date();
            const twoHoursAgo = new Date(now.getTime() - 7200000); // 2 hours
            const oneHourAgo = new Date(now.getTime() - 3600000);  // 1 hour
            const date = now.toISOString().split('T')[0];
            const startTime = twoHoursAgo.toTimeString().split(' ')[0];
            const midTime = oneHourAgo.toTimeString().split(' ')[0];
            const endTime = now.toTimeString().split(' ')[0];

            const res = await fetch(
                `${import.meta.env.VITE_HISTORY_API_URL}?date=${date}&startTime=${startTime}&endTime=${endTime}`
            );
            const data = await res.json();
            const records: TelemetryTick[] = data.records || [];

            // Split: previous hour vs current hour
            const prevHour = records.filter(r => r.ts < midTime);
            const currHour = records.filter(r => r.ts >= midTime);

            if (currHour.length > 0) {
                const avg = currHour.reduce((s, r) => s + r.voltage, 0) / currHour.length;
                const max = Math.max(...currHour.map(r => r.voltage));

                const prevAvg = prevHour.length > 0
                    ? prevHour.reduce((s, r) => s + r.voltage, 0) / prevHour.length
                    : avg; // no prev data → 0% change

                const pctChange = prevAvg !== 0
                    ? ((avg - prevAvg) / prevAvg) * 100
                    : 0;

                setStats({ avg, max, pctChange });
            }
        }

        fetchStats();
        const timer = setInterval(fetchStats, 60000);
        return () => clearInterval(timer);
    }, []);



    const history = useTelemetryStore((state) => state.history);
    const latest = useTelemetryStore((state) => state.latest);

    const chartData = history.map((tick) => {
        const [h, m, s] = tick.ts.split(':').map(Number);
        const date = new Date();
        date.setHours(h, m, s, 0);
        return { value: [date.getTime(), tick.voltage] };
    });


    const chartOption: echarts.EChartsOption = {
        tooltip: { trigger: 'axis'},
        grid: { top:30, right: 30, bottom: 40, left:50},
        xAxis: {
            type: 'time',
            splitLine: { show: false },
            min: Date.now() - 60000,
            max: Date.now(),
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
            name: 'Voltage',
            type: 'line',
            showSymbol: false,
            data: chartData,
        }],
    };

    return (
       <CommonCard
        cardTitle="Voltage"
        chartType={
            <ReactECharts
                option={chartOption}
                style={{height: '100%', width: '100%'}}
                opts={{ renderer: 'canvas'}}
                />
        }
       >
        <Reading measurement="Generator Voltage" measureValue={latest ? latest.voltage.toFixed(2) : '-'} measureUnit="V" />
        <Reading measurement="Average Voltage" measureValue={stats.avg.toFixed(2)} measureUnit="V" percentChange={stats.pctChange} />

       </CommonCard>
    )
}