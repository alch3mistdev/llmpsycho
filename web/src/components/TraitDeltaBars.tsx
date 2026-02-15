interface TraitDeltaBarsProps {
  before: Record<string, unknown> | undefined;
  after: Record<string, unknown> | undefined;
}

export function TraitDeltaBars({ before, after }: TraitDeltaBarsProps) {
  const beforeMean = (before?.mean ?? {}) as Record<string, unknown>;
  const afterMean = (after?.mean ?? {}) as Record<string, unknown>;
  const traits = Array.from(new Set([...Object.keys(beforeMean), ...Object.keys(afterMean)])).sort().slice(0, 12);

  if (traits.length === 0) {
    return <p className="hint">Trait delta is unavailable for this record.</p>;
  }

  return (
    <div className="trait-delta-list">
      {traits.map((trait) => {
        const b = Number(beforeMean[trait] ?? 0);
        const a = Number(afterMean[trait] ?? b);
        const delta = a - b;
        const width = Math.min(100, Math.max(4, Math.round(Math.abs(delta) * 120)));
        return (
          <div key={trait} className="trait-delta-row">
            <span>{trait}</span>
            <div className="trait-delta-track">
              <div
                className={delta >= 0 ? "trait-delta-fill positive" : "trait-delta-fill negative"}
                style={{ width: `${width}%` }}
              />
            </div>
            <strong>{delta >= 0 ? `+${delta.toFixed(3)}` : delta.toFixed(3)}</strong>
          </div>
        );
      })}
    </div>
  );
}
