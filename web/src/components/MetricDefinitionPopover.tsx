interface MetricDefinitionPopoverProps {
  term: string;
  definition: string;
}

export function MetricDefinitionPopover({ term, definition }: MetricDefinitionPopoverProps) {
  return (
    <details className="metric-popover">
      <summary>{term}</summary>
      <p>{definition}</p>
    </details>
  );
}
