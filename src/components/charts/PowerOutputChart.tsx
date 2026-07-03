import Arrow from "../../assets/ArrowUp.svg?react"
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';

type EChartsOption = echarts.EChartsOption;

// Generate fake data outside the component to avoid recalculating on each render
const generateData = () => {
  let base = +new Date(2026, 9, 3);
  const oneDay = 24 * 3600 * 1000;
  const date = [];
  const data = [Math.random() * 300];

  for (let i = 1; i < 100; i++) {
    const now = new Date((base += oneDay));
    date.push([now.getFullYear(), now.getMonth() + 1, now.getDate()].join('/'));
    data.push(Math.round((Math.random() - 0.5) * 20 + data[i - 1]));
  }
  return { date, data };
};

const { date, data } = generateData();

const option: EChartsOption = {
  tooltip: {
    trigger: 'axis',
    position: function (pt) {
      return [pt[0], '10%'];
    }
  },
  title: {
    left: 'center',
    text: 'Large Area Chart',
    show: false // Title hidden since card has its own title
  },
  toolbox: {
    feature: {
      dataZoom: {
        yAxisIndex: 'none'
      },
      restore: {},
      saveAsImage: {}
    }
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: date
  },
  yAxis: {
    type: 'value',
    boundaryGap: [0, '100%']
  },
  dataZoom: [
    {
      type: 'inside',
      start: 0,
      end: 10
    },
    {
      start: 0,
      end: 10
    }
  ],
  grid: {
    right: 30,
    left: 50
  },
  series: [
    {
      name: 'Fake Data',
      type: 'line',
      symbol: 'none',
      sampling: 'lttb',
      itemStyle: {
        color: 'rgba(70, 86, 255, 1)'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          {
            offset: 0,
            color: 'rgba(68, 177, 255, 1)'
          },
          {
            offset: 1,
            color: 'rgba(70, 116, 255, 1)'
          }
        ])
      },
      data: data
    }
  ]
};

export function PowerOutputChart() {
    return (
        <div className="w-full h-full bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 flex flex-col justify-start items-start overflow-hidden">
            <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                <div className="card-title">Power Output</div>
            </div>
            <div className="self-stretch h-full inline-flex flex-col justify-start items-start overflow-hidden">
                <div className="self-stretch h-full w-full">
                    <ReactECharts 
                        option={option} 
                        style={{ height: '100%', width: '100%' }} 
                        opts={{ renderer: 'canvas' }} 
                    />
                </div>
                {/* <div className="self-stretch w-full inline-flex px-4 pb-4">
                <div className="self-stretch w-full px-4 py-2 bg-sky-50 rounded-lg outline outline-1 outline-offset-[-1px] outline-blue-100 inline-flex justify-center items-center gap-6">
                    <div className="text-center justify-start text-black text-lg font-semibold font-['Inter']">24W</div>
                    <div className="size- flex justify-center items-center gap-0.5">
                        <div className="size-3 relative overflow-hidden">
                            <Arrow className="size-2.5 text-green-800 stroke-green-800 stroke-[0.8px]" />
                        </div>
                        <div className="text-center justify-center text-green-800 text-xs font-medium font-['Inter'] uppercase">24%</div>
                    </div>
                </div>
                </div> */}
            </div>
        </div>
    )
}