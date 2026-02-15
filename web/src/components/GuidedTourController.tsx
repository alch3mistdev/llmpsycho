import { useEffect } from "react";
import Shepherd from "shepherd.js";
import type { Tour } from "shepherd.js";
import "shepherd.js/dist/css/shepherd.css";

import { useStudioStore } from "../store/useStudioStore";

let activeTour: Tour | null = null;

function buildTour(): Tour {
  const tour = new Shepherd.Tour({
    useModalOverlay: true,
    defaultStepOptions: {
      scrollTo: true,
      cancelIcon: {
        enabled: true
      }
    }
  });

  tour.addStep({
    id: "mission-control",
    title: "Mission Control",
    text: "Track profile health and intervention outcomes at a glance.",
    attachTo: { element: "[data-tour='mission-control']", on: "bottom" },
    buttons: [{ text: "Next", action: tour.next }]
  });
  tour.addStep({
    id: "run-studio",
    title: "Profiler Lab",
    text: "Launch adaptive runs and watch confidence converge in real time.",
    attachTo: { element: "[data-tour='run-studio']", on: "bottom" },
    buttons: [
      { text: "Back", action: tour.back },
      { text: "Next", action: tour.next }
    ]
  });
  tour.addStep({
    id: "profile-anatomy",
    title: "Profile Anatomy",
    text: "Open a profile and inspect probe-by-probe evidence, scoring, and trait movement.",
    attachTo: { element: "[data-tour='profile-anatomy']", on: "bottom" },
    buttons: [
      { text: "Back", action: tour.back },
      { text: "Next", action: tour.next }
    ]
  });
  tour.addStep({
    id: "query-lab",
    title: "Intervention Simulator",
    text: "Compare baseline vs treated behavior with a causal trace.",
    attachTo: { element: "[data-tour='query-lab']", on: "bottom" },
    buttons: [
      { text: "Back", action: tour.back },
      { text: "Next", action: tour.next }
    ]
  });
  tour.addStep({
    id: "help",
    title: "Pinned Help",
    text: "Pin tooltips to keep definitions visible while you work.",
    attachTo: { element: "[data-tour='help-launcher']", on: "bottom" },
    buttons: [
      { text: "Back", action: tour.back },
      { text: "Done", action: tour.complete }
    ]
  });
  return tour;
}

export function GuidedTourController() {
  const { setTourState } = useStudioStore();

  useEffect(() => {
    if (!activeTour) {
      activeTour = buildTour();
      activeTour.on("show", () => {
        setTourState({
          last_step:
            activeTour?.steps?.findIndex((step: { isOpen: () => boolean }) => step.isOpen()) ?? 0
        });
      });
      activeTour.on("complete", () => {
        setTourState({
          completed_at: new Date().toISOString(),
          never_show_auto: true
        });
      });
      activeTour.on("cancel", () => {
        setTourState({ never_show_auto: true });
      });
    }

    const handler = () => {
      activeTour?.start();
    };
    window.addEventListener("studio:start-tour", handler);
    return () => {
      window.removeEventListener("studio:start-tour", handler);
    };
  }, [setTourState]);

  return null;
}
