import ReactECharts from "echarts-for-react";

import type { AlignmentReport } from "../../lib/types";

interface RubricBreakdownBarProps {
  baseline?: AlignmentReport | null;
  treated: AlignmentReport;
}

export function RubricBreakdownBar({ baseline, treated }: RubricBreakdownBarProps) {
  const labels = treated.rubric_scores.map((row) => row.name.replace(/_/g, " "));
  const treatedScores = treated.rubric_scores.map((row) => Number(row.merged_score.toFixed(3)));
  const baselineScores = baseline ? baseline.rubric_scores.map((row) => Number(row.merged_score.toFixed(3))) : [];

  const option = {
    animationDuration: 300,
    animationDurationUpdate: 260,
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: {
      data: baseline ? ["Baseline", "Treated"] : ["Score"]
    },
    grid: { left: 50, right: 20, top: 30, bottom: 70 },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { rotate: 25, fontSize: 11 }
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1
    },
    series: baseline
      ? [
          {
            name: "Baseline",
            type: "bar",
            data: baselineScores,
            itemStyle: { color: "#64748b" },
            universalTransition: true
          },
          {
            name: "Treated",
            type: "bar",
            data: treatedScores,
            itemStyle: { color: "#0ea5a6" },
            universalTransition: true
          }
        ]
      : [
          {
            name: "Score",
            type: "bar",
            data: treatedScores,
            itemStyle: { color: "#0ea5a6" },
            universalTransition: true
          }
        ]
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 320 }} />;
}
