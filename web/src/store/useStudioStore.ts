import { create } from "zustand";

import type { ExplanationMode, PinnedTooltip, Provider, TourState } from "../lib/types";

const TOUR_STORAGE_KEY = "studio_tour_v3";

function loadTourState(): TourState {
  if (typeof window === "undefined") {
    return { never_show_auto: false, last_step: 0, completed_at: null };
  }
  try {
    const raw = window.localStorage.getItem(TOUR_STORAGE_KEY);
    if (!raw) {
      return { never_show_auto: false, last_step: 0, completed_at: null };
    }
    const parsed = JSON.parse(raw) as Partial<TourState>;
    return {
      never_show_auto: Boolean(parsed.never_show_auto),
      last_step: Number(parsed.last_step ?? 0),
      completed_at: parsed.completed_at ?? null
    };
  } catch {
    return { never_show_auto: false, last_step: 0, completed_at: null };
  }
}

function persistTourState(state: TourState) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore local storage failures.
  }
}

interface StudioState {
  selectedProfileId: string | null;
  selectedProvider: Provider;
  selectedModelId: string;
  explanationMode: ExplanationMode;
  activeRunId: string | null;
  runEvents: Array<Record<string, unknown>>;
  tourState: TourState;
  pinnedTooltip: PinnedTooltip | null;
  selectedProbeCallIndex: number | null;
  playbackCallIndex: number | null;
  setSelectedProfileId: (profileId: string | null) => void;
  setSelectedProvider: (provider: Provider) => void;
  setSelectedModelId: (modelId: string) => void;
  setExplanationMode: (mode: ExplanationMode) => void;
  setActiveRunId: (runId: string | null) => void;
  pushRunEvent: (event: Record<string, unknown>) => void;
  clearRunEvents: () => void;
  setTourState: (patch: Partial<TourState>) => void;
  setPinnedTooltip: (tooltip: PinnedTooltip | null) => void;
  setSelectedProbeCallIndex: (callIndex: number | null) => void;
  setPlaybackCallIndex: (callIndex: number | null) => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  selectedProfileId: null,
  selectedProvider: "simulated",
  selectedModelId: "simulated-local",
  explanationMode: "Simple",
  activeRunId: null,
  runEvents: [],
  tourState: loadTourState(),
  pinnedTooltip: null,
  selectedProbeCallIndex: null,
  playbackCallIndex: null,
  setSelectedProfileId: (selectedProfileId) => set({ selectedProfileId }),
  setSelectedProvider: (selectedProvider) => set({ selectedProvider }),
  setSelectedModelId: (selectedModelId) => set({ selectedModelId }),
  setExplanationMode: (explanationMode) => set({ explanationMode }),
  setActiveRunId: (activeRunId) => set({ activeRunId }),
  pushRunEvent: (event) =>
    set((state) => {
      const next = [...state.runEvents, event];
      return { runEvents: next.slice(-1200) };
    }),
  clearRunEvents: () => set({ runEvents: [] }),
  setTourState: (patch) =>
    set((state) => {
      const next: TourState = {
        ...state.tourState,
        ...patch
      };
      persistTourState(next);
      return { tourState: next };
    }),
  setPinnedTooltip: (pinnedTooltip) => set({ pinnedTooltip }),
  setSelectedProbeCallIndex: (selectedProbeCallIndex) => set({ selectedProbeCallIndex }),
  setPlaybackCallIndex: (playbackCallIndex) => set({ playbackCallIndex })
}));
