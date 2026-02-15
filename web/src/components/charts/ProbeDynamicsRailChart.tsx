import ReactECharts from "echarts-for-react";

import type { ProbeTraceRow } from "../../lib/types";

interface ProbeDynamicsRailChartProps {
  rows: ProbeTraceRow[];
  activeCallIndex: number | null;
  onSelectCallIndex: (callIndex: number) => void;
}

export function ProbeDynamicsRailChart({ rows, activeCallIndex, onSelectCallIndex }: ProbeDynamicsRailChartProps) {
  const sorted = [...rows].sort((a, b) => a.call_index - b.call_index);
  const calls = sorted.map((row) => row.call_index + 1);

  const option = {
    tooltip: {
      trigger: "axis"
    },
    xAxis: {
      type: "category",
      data: calls,
      name: "Probe"
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: "Score"
    },
    series: [
      {
        name: "Observed Score",
        type: "line",
        smooth: true,
        data: sorted.map((row) => Number(row.score.toFixed(3))),
        lineStyle: { color: "#0e7490", width: 3 },
        areaStyle: { color: "rgba(14,116,144,0.18)" }
      },
      {
        name: "Expected Probability",
        type: "line",
        smooth: true,
        data: sorted.map((row) => Number(row.expected_probability.toFixed(3))),
        lineStyle: { color: "#f97316", type: "dashed", width: 2 }
      }
    ],
    graphic:
      activeCallIndex === null
        ? []
        : [
            {
              type: "text",
              left: "center",
              top: 6,
              style: {
                text: `Selected Probe #${activeCallIndex + 1}`,
                fill: "#0f172a",
                fontWeight: 700
              }
            }
          ]
  };

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: 280 }}
      onEvents={{
        click: (params: { dataIndex?: number }) => {
          if (typeof params.dataIndex === "number" && sorted[params.dataIndex]) {
            onSelectCallIndex(sorted[params.dataIndex].call_index);
          }
        }
      }}
    />
  );
}
