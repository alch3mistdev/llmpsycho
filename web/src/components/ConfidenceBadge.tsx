interface ConfidenceBadgeProps {
  label?: string;
  score?: number;
}

function normalizeLabel(label?: string, score?: number): "High" | "Medium" | "Low" {
  const normalized = (label ?? "").trim();
  if (normalized === "High" || normalized === "Medium" || normalized === "Low") {
    return normalized;
  }
  const numeric = Number(score ?? 0);
  if (numeric >= 0.8) {
    return "High";
  }
  if (numeric >= 0.6) {
    return "Medium";
  }
  return "Low";
}

export function ConfidenceBadge({ label, score }: ConfidenceBadgeProps) {
  const resolved = normalizeLabel(label, score);
  return <span className={`confidence-badge ${resolved.toLowerCase()}`}>{resolved} confidence</span>;
}
