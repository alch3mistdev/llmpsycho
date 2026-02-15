import type { ProbeTraceRow } from "../lib/types";

interface ScoringBreakdownCardProps {
  row: ProbeTraceRow | null;
}

export function ScoringBreakdownCard({ row }: ScoringBreakdownCardProps) {
  if (!row) {
    return (
      <article className="panel-card">
        <h3>Scoring Breakdown</h3>
        <p className="hint">Select a probe to inspect score decomposition.</p>
      </article>
    );
  }

  return (
    <article className="panel-card">
      <h3>Scoring Breakdown</h3>
      <div className="status-row">
        <span>Item</span>
        <strong>{row.item_id}</strong>
      </div>
      <div className="status-row">
        <span>Scoring Type</span>
        <strong>{row.scoring_type ?? "unknown"}</strong>
      </div>
      <div className="status-row">
        <span>Expected Probability</span>
        <strong>{row.expected_probability.toFixed(3)}</strong>
      </div>
      <div className="status-row">
        <span>Observed Score</span>
        <strong>{row.score.toFixed(3)}</strong>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(row.score_components ?? {}).map(([name, value]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>{Number(value).toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
