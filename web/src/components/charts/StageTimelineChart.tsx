import ReactECharts from "echarts-for-react";

interface StageTimelineChartProps {
  events: Array<Record<string, unknown>>;
}

function stagePoints(events: Array<Record<string, unknown>>, stage: "A" | "B" | "C"): Array<[number, number]> {
  const rows: Array<[number, number]> = [];
  for (const event of events) {
    if (String(event.eventType ?? "") !== "progress") {
      continue;
    }
    if (String(event.stage ?? "") !== stage) {
      continue;
    }
    const call = Number(event.call_index ?? 0) + 1;
    const y = stage === "A" ? 1 : stage === "B" ? 2 : 3;
    rows.push([call, y]);
  }
  return rows;
}

export function StageTimelineChart({ events }: StageTimelineChartProps) {
  const aPoints = stagePoints(events, "A");
  const bPoints = stagePoints(events, "B");
  const cPoints = stagePoints(events, "C");

  const option = {
    tooltip: {
      trigger: "item",
      formatter: (params: { value: [number, number]; seriesName: string }) => {
        return `${params.seriesName}<br/>Call ${params.value[0]}`;
      }
    },
    xAxis: {
      type: "value",
      name: "Call",
      nameLocation: "middle",
      nameGap: 28,
      axisLabel: {
        color: "#1f2937",
        fontFamily: "'IBM Plex Mono', monospace"
      }
    },
    yAxis: {
      type: "value",
      min: 0.5,
      max: 3.5,
      interval: 1,
      axisLabel: {
        formatter: (value: number) => {
          if (value === 1) {
            return "Stage A";
          }
          if (value === 2) {
            return "Stage B";
          }
          if (value === 3) {
            return "Stage C";
          }
          return "";
        },
        color: "#1f2937",
        fontFamily: "'Space Grotesk', sans-serif"
      }
    },
    legend: {
      data: ["Stage A", "Stage B", "Stage C"],
      bottom: 0
    },
    series: [
      {
        name: "Stage A",
        type: "scatter",
        symbolSize: 9,
        itemStyle: { color: "#0284c7" },
        data: aPoints
      },
      {
        name: "Stage B",
        type: "scatter",
        symbolSize: 9,
        itemStyle: { color: "#ea580c" },
        data: bPoints
      },
      {
        name: "Stage C",
        type: "scatter",
        symbolSize: 9,
        itemStyle: { color: "#0f766e" },
        data: cPoints
      }
    ]
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 260 }} />;
}
