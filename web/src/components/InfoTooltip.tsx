import { ReactNode, useState } from "react";
import {
  FloatingPortal,
  autoUpdate,
  flip,
  offset,
  shift,
  useDismiss,
  useFloating,
  useFocus,
  useHover,
  useInteractions,
  useRole
} from "@floating-ui/react";

import { useStudioStore } from "../store/useStudioStore";

interface InfoTooltipProps {
  id: string;
  title: string;
  definition: string;
  whyItMatters: string;
  decisionImplication: string;
  children: ReactNode;
}

export function InfoTooltip({
  id,
  title,
  definition,
  whyItMatters,
  decisionImplication,
  children
}: InfoTooltipProps) {
  const [open, setOpen] = useState(false);
  const { setPinnedTooltip } = useStudioStore();

  const { refs, floatingStyles, context } = useFloating({
    open,
    onOpenChange: setOpen,
    placement: "top",
    middleware: [offset(10), flip(), shift({ padding: 10 })],
    whileElementsMounted: autoUpdate
  });

  const hover = useHover(context, { move: false });
  const focus = useFocus(context);
  const dismiss = useDismiss(context);
  const role = useRole(context, { role: "tooltip" });
  const { getReferenceProps, getFloatingProps } = useInteractions([hover, focus, dismiss, role]);

  return (
    <>
      <span
        ref={refs.setReference}
        className="info-anchor"
        tabIndex={0}
        aria-label={`Explain ${title}`}
        {...getReferenceProps()}
      >
        {children}
      </span>
      {open && (
        <FloatingPortal>
          <div ref={refs.setFloating} style={floatingStyles} className="info-tooltip" {...getFloatingProps()}>
            <div className="info-tooltip-head">
              <strong>{title}</strong>
              <button
                type="button"
                className="pin-button"
                onClick={() =>
                  setPinnedTooltip({
                    id,
                    title,
                    content: `${definition}\n\nWhy it matters: ${whyItMatters}\n\nDecision: ${decisionImplication}`
                  })
                }
              >
                Pin
              </button>
            </div>
            <p>{definition}</p>
            <p>
              <strong>Why it matters:</strong> {whyItMatters}
            </p>
            <p>
              <strong>Decision implication:</strong> {decisionImplication}
            </p>
          </div>
        </FloatingPortal>
      )}
    </>
  );
}
