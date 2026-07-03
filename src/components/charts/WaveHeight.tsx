import {useState, useEffect} from "react";
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { CommonCard } from "../ui/CommonCard";
import { Reading } from "../ui/Reading";

export function WaveHeight() {

    const [chartOption, setChartOption] = useState<echarts.EChartsOption>({});

    useEffect(() => {
        let data: {name: string; value: [string, number]}[] = [];
        let now = new Date(2026, 7, 3);
        let oneDay = 24*3600*1000;
        let value = Math.random()*0.4;

        function randomData(){
            now = new Date(+now + oneDay);
            value = value + Math.random()* 21 - 10;
            return{
                name : now.toString(),
                value : [
                    [now.getFullYear(), now.getMonth() + 1, now.getDate()].join('/'),
                    Math.round(value)
                ] as [string, number]
            };
        }

        for (var i=0; i<1000; i++){
            data.push(randomData());
        }

        setChartOption({
            tooltip: { trigger: 'axis' },
            grid: {
                top: 30,
                right: 30,
                bottom: 40,
                left: 50
            },
            xAxis : { type: 'time', splitLine: {show: false}},
            yAxis: { type: 'value', boundaryGap: [0, '100%'], splitLine: {show: false}},
            series: [{ name: 'Fake Data', type: 'line', showSymbol: false, data:data}]
        });

        const timer = setInterval(() => {
            for (var i=0; i<5; i++){
                data.shift();
                data.push(randomData());
            }

            setChartOption((prevOption) => ({
                ...prevOption,
                series: [{ data: [...data], type: 'line', showSymbol: false}]
            }));
        }, 1000);

        return () => clearInterval(timer);
    }, []);
    
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
        <Reading measurement="Average Height" measureValue={2} measureUnit="m" />
        <Reading measurement="Maximum Height" measureValue={3.5} measureUnit="m" />
       </CommonCard>
    )
}