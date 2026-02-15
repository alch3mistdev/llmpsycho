import type { InterventionAttribution } from "../lib/types";

interface AttributionListProps {
  rows: InterventionAttribution[];
}

export function AttributionList({ rows }: AttributionListProps) {
  if (rows.length === 0) {
    return <p className="hint">No attribution data yet.</p>;
  }

  return (
    <div className="attribution-list" role="list" aria-label="Top contributors">
      {rows.map((row) => (
        <article key={row.rule} className="attribution-item" role="listitem">
          <div className="attribution-head">
            <strong>{row.rule}</strong>
            <span className={row.direction === "positive" ? "tag good" : "tag"}>{row.direction}</span>
          </div>
          <div className="attribution-metrics">
            <span>Contribution: {row.primary_contribution.toFixed(2)}</span>
            <span>Counterfactual drop: {row.counterfactual_drop_estimate.toFixed(2)}</span>
            <span>Confidence: {row.confidence.toFixed(2)}</span>
          </div>
          <p className="hint">Traits: {row.traits.join(", ") || "none"}</p>
        </article>
      ))}
    </div>
  );
}
