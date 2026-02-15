import ReactECharts from "echarts-for-react";

interface StageTimelineChartProps {
  events: Array<Record<string, unknown>>;
}

export function StageTimelineChart({ events }: StageTimelineChartProps) {
  const data = events
    .map((event, index) => {
      const stage = String(event.stage ?? "");
      if (stage !== "A" && stage !== "B" && stage !== "C") {
        return null;
      }
      return [index + 1, `Stage ${stage}`];
    })
    .filter((row): row is [number, string] => Array.isArray(row));

  const option = {
    tooltip: { trigger: "axis" },
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
      type: "category",
      data: ["Stage A", "Stage B", "Stage C"],
      axisLabel: {
        color: "#1f2937",
        fontFamily: "'Space Grotesk', sans-serif"
      }
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbolSize: 7,
        data,
        lineStyle: {
          color: "#0891b2",
          width: 3
        },
        areaStyle: {
          color: "rgba(8,145,178,0.2)"
        },
        itemStyle: {
          color: "#f97316"
        }
      }
    ]
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 260 }} />;
}
