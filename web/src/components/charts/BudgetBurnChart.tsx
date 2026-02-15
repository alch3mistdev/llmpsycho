import ReactECharts from "echarts-for-react";

interface BudgetBurnChartProps {
  events: Array<Record<string, unknown>>;
}

export function BudgetBurnChart({ events }: BudgetBurnChartProps) {
  let prompt = 0;
  let completion = 0;

  const series = events.map((event, index) => {
    prompt += Number(event.prompt_tokens ?? 0);
    completion += Number(event.completion_tokens ?? 0);
    return {
      call: index + 1,
      prompt,
      completion,
      total: prompt + completion
    };
  });

  const option = {
    animationDuration: 320,
    animationDurationUpdate: 280,
    tooltip: { trigger: "axis" },
    legend: {
      data: ["Prompt", "Completion", "Total"],
      textStyle: {
        fontFamily: "'Space Grotesk', sans-serif"
      }
    },
    xAxis: {
      type: "category",
      data: series.map((x) => x.call),
      name: "Call"
    },
    yAxis: {
      type: "value",
      name: "Tokens"
    },
    series: [
      {
        name: "Prompt",
        type: "line",
        data: series.map((x) => x.prompt),
        lineStyle: { color: "#0284c7" },
        universalTransition: true
      },
      {
        name: "Completion",
        type: "line",
        data: series.map((x) => x.completion),
        lineStyle: { color: "#eab308" },
        universalTransition: true
      },
      {
        name: "Total",
        type: "line",
        data: series.map((x) => x.total),
        lineStyle: { color: "#ea580c", width: 3 },
        areaStyle: { color: "rgba(234,88,12,0.16)" },
        universalTransition: true
      }
    ]
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 260 }} />;
}
