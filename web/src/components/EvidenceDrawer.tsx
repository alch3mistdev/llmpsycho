import { useQuery } from "@tanstack/react-query";

import { getQueryLabTrace } from "../lib/api";

interface EvidenceDrawerProps {
  title: string;
  traceId?: string;
  fallback?: Record<string, unknown> | null;
}

export function EvidenceDrawer({ title, traceId, fallback }: EvidenceDrawerProps) {
  const traceQuery = useQuery({
    queryKey: ["trace", traceId],
    queryFn: () => getQueryLabTrace(traceId as string),
    enabled: Boolean(traceId)
  });

  return (
    <details className="evidence-drawer">
      <summary>{title}</summary>
      {traceQuery.isLoading && traceId && <p className="hint">Loading trace...</p>}
      {traceQuery.isError && traceId && <p className="error">Failed to load trace evidence.</p>}
      <pre>
        {JSON.stringify(
          traceQuery.data?.trace ?? fallback ?? { note: traceId ? "Trace unavailable" : "No trace selected" },
          null,
          2
        )}
      </pre>
    </details>
  );
}
