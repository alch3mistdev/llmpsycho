import ReactECharts from "echarts-for-react";

import type { InterventionCausalTrace } from "../../lib/types";

interface CausalFlowGraphProps {
  trace: InterventionCausalTrace;
}

export function CausalFlowGraph({ trace }: CausalFlowGraphProps) {
  const nodeNames = [
    "Query Intent",
    "Profile Evidence",
    "Rule Triggers",
    "Prompt/System Transforms",
    "Result Deltas"
  ];

  const nodes = nodeNames.map((name) => ({ name }));
  const strength = Math.max(0.1, Math.min(1.0, trace.attribution.reduce((acc, row) => acc + row.primary_contribution, 0)));

  const links = [
    { source: "Query Intent", target: "Profile Evidence", value: 1.0 },
    { source: "Profile Evidence", target: "Rule Triggers", value: Math.max(0.3, trace.triggered_rules.length / 5) },
    { source: "Rule Triggers", target: "Prompt/System Transforms", value: Math.max(0.3, trace.transformations.length / 6) },
    { source: "Prompt/System Transforms", target: "Result Deltas", value: strength }
  ];

  const option = {
    animationDuration: 360,
    animationDurationUpdate: 320,
    tooltip: { trigger: "item" },
    series: [
      {
        type: "sankey",
        emphasis: { focus: "adjacency" },
        data: nodes,
        links,
        lineStyle: {
          color: "gradient",
          curveness: 0.5
        },
        itemStyle: {
          borderWidth: 1,
          borderColor: "#cbd5e1"
        },
        label: {
          color: "#0f172a",
          fontSize: 12
        },
        universalTransition: true
      }
    ]
  };

  return <ReactECharts option={option} style={{ width: "100%", height: 320 }} />;
}
