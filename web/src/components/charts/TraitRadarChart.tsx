import ReactECharts from "echarts-for-react";

import type { TraitEstimate } from "../../lib/types";

interface TraitRadarChartProps {
  title: string;
  traits: TraitEstimate[];
}

export function TraitRadarChart({ title, traits }: TraitRadarChartProps) {
  const indicators = traits.slice(0, 12).map((item) => ({
    name: item.trait,
    max: 1,
    min: -1
  }));

  const values = traits.slice(0, 12).map((item) => Number(item.mean.toFixed(3)));

  const option = {
    backgroundColor: "transparent",
    title: {
      text: title,
      left: "center",
      textStyle: {
        color: "#0f172a",
        fontFamily: "'Space Grotesk', sans-serif",
        fontWeight: 700,
        fontSize: 14
      }
    },
    tooltip: {},
    radar: {
      indicator: indicators,
      radius: "60%",
      splitNumber: 4,
      axisName: {
        color: "#1f2937",
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: ["#cbd5e1", "#dbeafe", "#bfdbfe", "#93c5fd"]
        }
      },
      splitArea: {
        areaStyle: {
          color: ["#ffffff", "#f8fafc"]
        }
      }
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: values,
            name: "mean",
            lineStyle: {
              color: "#0ea5a6",
              width: 2
            },
            areaStyle: {
              color: "rgba(14,165,166,0.25)"
            },
            symbolSize: 4,
            itemStyle: {
              color: "#ea580c"
            }
          }
        ]
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: 340, width: "100%" }} />;
}
