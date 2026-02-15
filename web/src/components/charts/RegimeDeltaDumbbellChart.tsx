import ReactECharts from "echarts-for-react";

import type { RegimeDelta } from "../../lib/types";

interface RegimeDeltaDumbbellChartProps {
  rows: RegimeDelta[];
}

export function RegimeDeltaDumbbellChart({ rows }: RegimeDeltaDumbbellChartProps) {
  const top = rows.slice(0, 12).reverse();

  const option = {
    animationDuration: 320,
    animationDurationUpdate: 280,
    tooltip: { trigger: "axis" },
    grid: { left: 120, right: 30, top: 20, bottom: 40 },
    xAxis: {
      type: "value",
      min: -1,
      max: 1,
      axisLabel: { color: "#1f2937" }
    },
    yAxis: {
      type: "category",
      data: top.map((row) => row.name),
      axisLabel: { color: "#1f2937", fontSize: 11 }
    },
    series: [
      {
        type: "line",
        data: top.map((row) => [row.core, row.name]),
        lineStyle: { opacity: 0 },
        showSymbol: true,
        symbolSize: 8,
        itemStyle: { color: "#0284c7" },
        name: "Core",
        universalTransition: true
      },
      {
        type: "line",
        data: top.map((row) => [row.safety, row.name]),
        lineStyle: { opacity: 0 },
        showSymbol: true,
        symbolSize: 8,
        itemStyle: { color: "#ea580c" },
        name: "Safety",
        universalTransition: true
      },
      {
        type: "custom",
        name: "Delta",
        renderItem: (params: any, api: any) => {
          const name = top[params.dataIndex]?.name;
          const row = top.find((item) => item.name === name);
          if (!row) {
            return null;
          }
          const y = api.coord([0, row.name])[1];
          const x1 = api.coord([row.core, row.name])[0];
          const x2 = api.coord([row.safety, row.name])[0];
          return {
            type: "line",
            shape: { x1, y1: y, x2, y2: y },
            style: {
              stroke: "#64748b",
              lineWidth: 2,
              opacity: 0.7
            }
          };
        },
        data: top.map((row) => row.name)
      }
    ]
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 360 }} />;
}
