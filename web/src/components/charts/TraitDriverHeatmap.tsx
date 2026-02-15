import ReactECharts from "echarts-for-react";

import type { TraitDriver } from "../../lib/types";

interface TraitDriverHeatmapProps {
  rows: TraitDriver[];
}

export function TraitDriverHeatmap({ rows }: TraitDriverHeatmapProps) {
  const traits = Array.from(new Set(rows.map((row) => row.trait_name)));
  const rules = Array.from(new Set(rows.map((row) => row.rule)));

  const data = rows.map((row) => {
    const x = traits.indexOf(row.trait_name);
    const y = rules.indexOf(row.rule);
    const signed = row.direction === "risk" ? -Math.abs(row.influence) : Math.abs(row.influence);
    return [x, y, Number(signed.toFixed(3))];
  });

  const option = {
    tooltip: {
      position: "top",
      formatter: (params: { value: [number, number, number] }) => {
        const [x, y, v] = params.value;
        return `${rules[y]} \u2194 ${traits[x]}<br/>Influence: ${v.toFixed(3)}`;
      }
    },
    grid: { left: 130, right: 30, top: 20, bottom: 70 },
    xAxis: {
      type: "category",
      data: traits,
      axisLabel: { rotate: 25, color: "#1f2937", fontSize: 11 }
    },
    yAxis: {
      type: "category",
      data: rules,
      axisLabel: { color: "#1f2937", fontSize: 11 }
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 10,
      inRange: {
        color: ["#b91c1c", "#f8fafc", "#0f766e"]
      }
    },
    series: [
      {
        type: "heatmap",
        data,
        label: {
          show: true,
          fontSize: 10,
          formatter: (params: { value: [number, number, number] }) => params.value[2].toFixed(2)
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 8,
            shadowColor: "rgba(15,23,42,0.3)"
          }
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 360 }} />;
}
