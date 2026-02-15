import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import type { ProbeTraceRow } from "../lib/types";

interface ProbeTimelineProps {
  rows: ProbeTraceRow[];
  selectedCallIndex: number | null;
  onSelect: (row: ProbeTraceRow) => void;
}

export function ProbeTimeline({ rows, selectedCallIndex, onSelect }: ProbeTimelineProps) {
  const parentRef = useRef<HTMLDivElement | null>(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 54,
    overscan: 8
  });

  return (
    <div className="probe-timeline" ref={parentRef}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, width: "100%", position: "relative" }}>
        {virtualizer.getVirtualItems().map((virtualRow: { index: number; size: number; start: number }) => {
          const row = rows[virtualRow.index];
          const isActive = selectedCallIndex === row.call_index;
          return (
            <button
              type="button"
              key={`${row.call_index}-${row.item_id}`}
              className={isActive ? "probe-row active" : "probe-row"}
              onClick={() => onSelect(row)}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`
              }}
            >
              <span className="probe-row-call">#{row.call_index + 1}</span>
              <span>{row.stage}</span>
              <span>{row.family}</span>
              <span>{row.score.toFixed(2)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
