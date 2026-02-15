import ReactECharts from "echarts-for-react";

interface CriticalConfidenceChartProps {
  events: Array<Record<string, unknown>>;
}

export function CriticalConfidenceChart({ events }: CriticalConfidenceChartProps) {
  const progressEvents = events.filter((event) => String(event.eventType ?? "") === "progress");

  const traitSet = new Set<string>();
  for (const event of progressEvents) {
    const reliability = event.posterior_reliability;
    if (!reliability || typeof reliability !== "object") {
      continue;
    }
    for (const trait of Object.keys(reliability as Record<string, unknown>)) {
      traitSet.add(trait);
    }
  }

  const traits = Array.from(traitSet).sort();

  const option = {
    tooltip: { trigger: "axis" },
    legend: { data: traits, bottom: 0 },
    xAxis: {
      type: "category",
      data: progressEvents.map((event) => Number(event.call_index ?? 0) + 1),
      name: "Call"
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      name: "Reliability"
    },
    series: traits.map((trait) => ({
      name: trait,
      type: "line",
      smooth: true,
      showSymbol: false,
      data: progressEvents.map((event) => {
        const reliability = event.posterior_reliability as Record<string, unknown> | undefined;
        return Number(reliability?.[trait] ?? 0);
      })
    }))
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 280 }} />;
}
