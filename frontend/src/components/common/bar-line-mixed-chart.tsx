'use client';

import React, { useEffect, useRef } from 'react';
import { BarChart, LineChart } from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import type { EChartsOption } from 'echarts/types/dist/shared';

type EChartsInstance = ReturnType<typeof echarts.init>;

echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  BarChart,
  LineChart,
  CanvasRenderer,
  ToolboxComponent,
]);

type ChartDataSeries = {
  name: string;
  units: string;
  data: (number | null | undefined)[];
};

interface MixedChartProps {
  data_x: ChartDataSeries;
  data_y: ChartDataSeries;
  xAxisData: (string | number)[];
}

export default function MixedChart({
  data_x,
  data_y,
  xAxisData,
}: MixedChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<EChartsInstance | null>(null);

  useEffect(() => {
    if (!chartRef.current) {
      console.warn('Chart container ref is not available.');
      return;
    }

    if (chartInstanceRef.current) {
      chartInstanceRef.current.dispose();
    }
    const newChartInstance = echarts.init(chartRef.current);
    chartInstanceRef.current = newChartInstance;

    const option: EChartsOption = {
      toolbox: {
        show: true,
        name: `VyomOS Fleet Manager - ${data_x.name} vs ${data_y.name}`,
        feature: {
          saveAsImage: {
            name: `VyomOS Fleet Manager - ${data_x.name} vs ${data_y.name}`,
          },
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      valueFormatter: (value: number) => {
        return `${Math.round(value)}`;
      },
      legend: {
        data: [data_x.name, data_y.name],
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: [
        {
          type: 'category',
          data: xAxisData,
          axisTick: {
            alignWithLabel: true,
          },
        },
      ],
      yAxis: [
        {
          type: 'value',
          name: data_x.name,
          position: 'left',
          axisLabel: { formatter: `{value} ${data_x.units}` },
        },
        {
          type: 'value',
          name: data_y.name,
          position: 'right',
          axisLabel: { formatter: `{value} ${data_y.units}` },
        },
      ],
      series: [
        {
          name: data_x.name,
          type: 'bar',
          yAxisIndex: 0,
          data: data_x.data,
          // itemStyle: { color: '#5470C6' }
        },
        {
          name: data_y.name,
          type: 'line',
          yAxisIndex: 1,
          data: data_y.data,
          smooth: true,
          // itemStyle: { color: '#91CC75' },
          // lineStyle: { width: 2 }
        },
      ],
    };

    newChartInstance.setOption(option);

    const handleResize = () => {
      chartInstanceRef.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstanceRef.current?.dispose();
      chartInstanceRef.current = null;
    };
  }, [data_x, data_y, xAxisData]);

  return <div ref={chartRef} className="h-96 w-full" />;
}
