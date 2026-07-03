import { Reading } from "../ui/Reading";
import Arrow from "../../assets/ArrowUp.svg?react"
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';

type EChartsOption = echarts.EChartsOption;

const gaugeOption: EChartsOption = {
  series: [
    {
      type: 'gauge',
      center: ['40%', '70%'], // Shifted further down to maximize vertical arc space
      radius: '135%',          // Increased radius to scale up the gauge
      startAngle: 180,
      endAngle: 0,
      min: 0,
      max: 240,
      splitNumber: 6,         // Reduced splitNumber to prevent labels from overlapping
      itemStyle: {
        color: '#58D9F9',
        shadowColor: 'rgba(0,138,255,0.45)',
        shadowBlur: 10,
        shadowOffsetX: 2,
        shadowOffsetY: 2
      },
      progress: {
        show: true,
        roundCap: true,
        width: 10
      },
      pointer: {
        icon: 'path://M2090.36389,615.30999 L2090.36389,615.30999 C2091.48372,615.30999 2092.40383,616.194028 2092.44859,617.312956 L2096.90698,728.755929 C2097.05155,732.369577 2094.2393,735.416212 2090.62566,735.56078 C2090.53845,735.564269 2090.45117,735.566014 2090.36389,735.566014 L2090.36389,735.566014 C2086.74736,735.566014 2083.81557,732.63423 2083.81557,729.017692 C2083.81557,728.930412 2083.81732,728.84314 2083.82081,728.755929 L2088.2792,617.312956 C2088.32396,616.194028 2089.24407,615.30999 2090.36389,615.30999 Z',
        length: '75%',
        width: 6,
        offsetCenter: [0, '5%']
      },
      axisLine: {
        roundCap: true,
        lineStyle: {
          width: 10
        }
      },
      axisTick: {
        splitNumber: 4,
        lineStyle: {
          width: 1,
          color: '#999'
        }
      },
      splitLine: {
        length: 10,
        lineStyle: {
          width: 2,
          color: '#999'
        }
      },
      axisLabel: {
        distance: 12,
        color: '#999',
        fontSize: 10
      },
      title: {
        show: false
      },
      detail: {
        backgroundColor: '#fff',
        borderColor: '#999',
        borderWidth: 1,
        width: '60%',
        lineHeight: 22,
        height: 22,
        borderRadius: 4,
        offsetCenter: [0, '25%'], // Moved up slightly to not overlap the center pointer base
        valueAnimation: true,
        formatter: function (value: number) {
          return '{value|' + value.toFixed(0) + '}{unit|RPM}';
        },
        rich: {
          value: {
            fontSize: 20,
            fontWeight: 'bolder',
            color: '#777'
          },
          unit: {
            fontSize: 10,
            color: '#999',
            padding: [0, 0, -4, 4]
          }
        }
      },
      data: [
        {
          value: 100
        }
      ]
    }
  ]
};

export function DailyMetrics() {
    return (
        <div className="w-full h-full flex flex-col justify-start items-start overflow-hidden gap-2">
                    <div className="self-stretch bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 inline-flex flex-col justify-start items-start">
                        <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                                <div className="card-title">Power</div>
                        </div>
                        <div className="self-stretch p-4 inline-flex justify-start items-center gap-2">
                            <div className="w-full h-full p-2 bg-[#F4FAFF] rounded-lg outline outline-1 outline-blue-100 inline-flex flex-col justify-between items-start gap-1">
                    <div className="text-center justify-start text-black/60 text-[10px] font-medium font-['Inter'] uppercase">Current Power</div>
                    <div className="self-stretch inline-flex justify-between items-end">
                        <div className="text-center justify-start text-black text-5xl font-semibold font-['Inter']">24W</div>
                        <div className="size- flex justify-center items-center gap-0.4">
                            <div className="size-3 relative overflow-hidden">
                                <Arrow className="size-2.5 text-green-800 stroke-green-800 stroke-[0.8px]" />
                            </div>
                            <div className="text-center justify-center text-green-800 text-xs font-medium font-['Inter'] uppercase">24%</div>
                        </div>
                    </div>
                    </div>
                    <div className="self-stretch w-full inline-flex flex-col justify-start items-start gap-2">
                        <Reading measurement="peak" measureValue={56} measureUnit="W" />
                        <Reading measurement="average" measureValue={17} measureUnit="W"/>
                    </div>
                </div>
            </div>
            <div className="self-stretch min-h-[200px] h-full bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 inline-flex flex-col justify-start items-start">
                        <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                                <div className="card-title">Generator RPM</div>
                        </div>
                    <div className="self-stretch h-full p-4 inline-flex gap-1">
                        <div className="w-2/3 h-full">
                            <ReactECharts 
                                option={gaugeOption} 
                                style={{ height: '100%', width: '100%' }} 
                                opts={{ renderer: 'canvas' }} 
                            />
                        </div>
                        <div className="w-1/3 inline-flex flex-col justify-start items-start">
                            <div className="h-full"></div>
                            <Reading measurement="average" measureValue={104} measureUnit="rpm"/>
                        </div>
                    </div>
            </div>
        </div>
    )
}