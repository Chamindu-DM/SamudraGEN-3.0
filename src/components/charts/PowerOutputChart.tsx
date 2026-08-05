import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import { useEffect, useState } from 'react';
import { fetchLast24HoursPowerData } from '../../services/dynamoClient';

export function PowerOutputChart() {
    const [chartData, setChartData] = useState<{ date: string[], data: number[] }>({ date: [], data: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let mounted = true;
        
        async function loadData() {
            try {
                const results = await fetchLast24HoursPowerData();
                if (!mounted) return;
                
                const date = results.map(r => {
                    // Extract HH:mm:ss for x-axis
                    const t = r.ts;
                    if (t.includes('T')) {
                        const timeStr = t.split('T')[1].split('+')[0];
                        return timeStr;
                    }
                    return t;
                });
                const data = results.map(r => r.power);
                
                setChartData({ date, data });
            } catch (err) {
                console.error("Failed to load power data", err);
            } finally {
                if (mounted) setLoading(false);
            }
        }
        
        loadData();
        return () => { mounted = false; };
    }, []);

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        position: function (pt) {
          return [pt[0], '10%'];
        }
      },
      title: {
        show: false
      },
      toolbox: {
        feature: {
          dataZoom: { yAxisIndex: 'none' },
          restore: {},
          saveAsImage: {}
        }
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: chartData.date
      },
      yAxis: {
        type: 'value',
        boundaryGap: [0, '100%'],
        name: 'Watts'
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { start: 0, end: 100 }
      ],
      grid: {
        right: 30,
        left: 50,
        top: 40,
        bottom: 80
      },
      series: [
        {
          name: 'Power (W)',
          type: 'line',
          symbol: 'none',
          sampling: 'lttb', // Essential for performance with massive data points
          itemStyle: { color: 'rgba(70, 86, 255, 1)' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(68, 177, 255, 1)' },
              { offset: 1, color: 'rgba(70, 116, 255, 1)' }
            ])
          },
          data: chartData.data
        }
      ]
    };

    return (
        <div className="w-full h-full bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-sky-500/20 flex flex-col justify-start items-start overflow-hidden relative">
            <div className="self-stretch px-4 pt-3 inline-flex justify-start">
                <div className="card-title">Power Output
                </div>
            </div>
            
            {loading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/80">
                    <div className="text-sm font-semibold text-sky-600 animate-pulse">Loading DB Data...</div>
                </div>
            )}
            
            <div className="self-stretch h-full inline-flex flex-col justify-start items-start overflow-hidden">
                <div className="self-stretch h-full w-full">
                    <ReactECharts 
                        option={option} 
                        style={{ height: '100%', width: '100%' }} 
                        opts={{ renderer: 'canvas' }} 
                        notMerge={true}
                        lazyUpdate={true}
                    />
                </div>
            </div>
        </div>
    )
}