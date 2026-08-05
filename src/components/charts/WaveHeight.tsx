import {useState, useEffect} from "react";
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { CommonCard } from "../ui/CommonCard";
import { Reading } from "../ui/Reading";
import { useTelemetryStore, type TelemetryTick } from "../../store/telemetryStore";

export function WaveHeight() {

    //const [chartOption, setChartOption] = useState<echarts.EChartsOption>({});

    // useEffect(() => {
    //     let data: {name: string; value: [string, number]}[] = [];
    //     let now = new Date(2026, 7, 3);
    //     let oneDay = 24*3600*1000;
    //     let value = Math.random()*0.4;

    //     function randomData(){
    //         now = new Date(+now + oneDay);
    //         value = value + Math.random()* 21 - 10;
    //         return{
    //             name : now.toString(),
    //             value : [
    //                 [now.getFullYear(), now.getMonth() + 1, now.getDate()].join('/'),
    //                 Math.round(value)
    //             ] as [string, number]
    //         };
    //     }

    //     for (var i=0; i<1000; i++){
    //         data.push(randomData());
    //     }

    //     setChartOption({
    //         tooltip: { trigger: 'axis' },
    //         grid: {
    //             top: 30,
    //             right: 30,
    //             bottom: 40,
    //             left: 50
    //         },
    //         xAxis : { type: 'time', splitLine: {show: false}},
    //         yAxis: { type: 'value', boundaryGap: [0, '100%'], splitLine: {show: false}},
    //         series: [{ name: 'Fake Data', type: 'line', showSymbol: false, data:data}]
    //     });

    //     const timer = setInterval(() => {
    //         for (var i=0; i<5; i++){
    //             data.shift();
    //             data.push(randomData());
    //         }

    //         setChartOption((prevOption) => ({
    //             ...prevOption,
    //             series: [{ data: [...data], type: 'line', showSymbol: false}]
    //         }));
    //     }, 1000);

    //     return () => clearInterval(timer);
    // }, []);
    
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

            const res = await fetch(
                `${import.meta.env.VITE_HISTORY_API_URL}?date=${date}&startTime=${startTime}&endTime=${endTime}`
            );
            const data = await res.json();
            const records: TelemetryTick[] = data.records || [];

            // Split: previous hour vs current hour
            const prevHour = records.filter(r => r.ts < midTime);
            const currHour = records.filter(r => r.ts >= midTime);

            if (currHour.length > 0) {
                const avg = currHour.reduce((s, r) => s + r.waveHeight, 0) / currHour.length;
                const max = Math.max(...currHour.map(r => r.waveHeight));

                const prevAvg = prevHour.length > 0
                    ? prevHour.reduce((s, r) => s + r.waveHeight, 0) / prevHour.length
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

    const chartData = history.map((tick) => {
        const [h, m, s] = tick.ts.split(':').map(Number);
        const date = new Date();
        date.setHours(h, m, s, 0);
        return { value: [date.getTime(), tick.waveHeight] };
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
        <Reading measurement="Average Height" measureValue={stats.avg.toFixed(2)} measureUnit="m" percentChange={stats.pctChange} />
        <Reading measurement="Maximum Height" measureValue={stats.max.toFixed(2)} measureUnit="m" />

       </CommonCard>
    )
}