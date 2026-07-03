import { useState, useEffect } from "react";
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { CommonCard } from '../ui/CommonCard'
import { Reading } from '../ui/Reading'

export function VoltageCurrent() {
    const [chartOption, setChartOption] = useState<echarts.EChartsOption>({});

    useEffect(() => {
        let dataVoltage:{name: string; value: [string, number]}[] = [];
        let dataCurrent:{name: string; value: [string, number]}[] = [];
        
        let now = new Date(2026, 7, 3);
        let oneDay = 24 * 3600 * 1000;
        let voltageValue = 12.0;
        let currentValue = 2.0;

        function randomVoltage(date: Date) {
            voltageValue = voltageValue + Math.random() * 0.4 - 0.2; // Hover around 12V
            return {
                name: date.toString(),
                value: [
                    [date.getFullYear(), date.getMonth() + 1, date.getDate()].join('/'),
                    Math.round(voltageValue * 100) / 100
                ] as [string, number]
            };
        }

        function randomCurrent(date: Date) {
            currentValue = currentValue + Math.random() * 0.2 - 0.1; // Hover around 2A
            return {
                name: date.toString(),
                value: [
                    [date.getFullYear(), date.getMonth() + 1, date.getDate()].join('/'),
                    Math.round(currentValue * 100) / 100
                ] as [string, number]
            };
        }

        for (var i = 0; i < 1000; i++) {
            now = new Date(+now + oneDay);
            dataVoltage.push(randomVoltage(now));
            dataCurrent.push(randomCurrent(now));
        }

        setChartOption({
            tooltip: { trigger: 'axis' },
            grid: {
                top: 40,
                right: 40,
                bottom: 40,
                left: 40
            },
            xAxis: { type: 'time', splitLine: { show: false } },
            yAxis: [
                {
                    type: 'value',
                    name: 'V',
                    boundaryGap: [0, '100%'],
                    splitLine: { show: false },
                    position: 'left'
                },
                {
                    type: 'value',
                    name: 'A',
                    boundaryGap: [0, '100%'],
                    splitLine: { show: false },
                    position: 'right'
                }
            ],
            series: [
                { name: 'Voltage', type: 'line', showSymbol: false, data: dataVoltage, yAxisIndex: 0 },
                { name: 'Current', type: 'line', showSymbol: false, data: dataCurrent, yAxisIndex: 1 }
            ]
        });

        const timer = setInterval(() => {
            for (var i = 0; i < 5; i++) {
                now = new Date(+now + oneDay);
                dataVoltage.shift();
                dataVoltage.push(randomVoltage(now));
                
                dataCurrent.shift();
                dataCurrent.push(randomCurrent(now));
            }

            setChartOption((prevOption) => ({
                ...prevOption,
                series: [
                    { name: 'Voltage', data: [...dataVoltage], type: 'line', showSymbol: false, yAxisIndex: 0 },
                    { name: 'Current', data: [...dataCurrent], type: 'line', showSymbol: false, yAxisIndex: 1 }
                ]
            }));
        }, 1000);

        return () => clearInterval(timer);
    }, []);

    return (
        <CommonCard
            cardTitle='Voltage & Current'
            chartType={
                <ReactECharts
                    option={chartOption}
                    style={{ height: '100%', width: '100%' }}
                    opts={{ renderer: 'canvas' }}
                />
            }
        >
            <Reading measurement="Voltage" measureValue={12} measureUnit="V" />
            <Reading measurement="Current" measureValue={2} measureUnit="A" />
        </CommonCard>
    )
}