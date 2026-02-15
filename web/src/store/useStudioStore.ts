import { create } from "zustand";

import type { ExplanationMode, Provider } from "../lib/types";

interface StudioState {
  selectedProfileId: string | null;
  selectedProvider: Provider;
  selectedModelId: string;
  explanationMode: ExplanationMode;
  activeRunId: string | null;
  runEvents: Array<Record<string, unknown>>;
  setSelectedProfileId: (profileId: string | null) => void;
  setSelectedProvider: (provider: Provider) => void;
  setSelectedModelId: (modelId: string) => void;
  setExplanationMode: (mode: ExplanationMode) => void;
  setActiveRunId: (runId: string | null) => void;
  pushRunEvent: (event: Record<string, unknown>) => void;
  clearRunEvents: () => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  selectedProfileId: null,
  selectedProvider: "simulated",
  selectedModelId: "simulated-local",
  explanationMode: "Simple",
  activeRunId: null,
  runEvents: [],
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
  clearRunEvents: () => set({ runEvents: [] })
}));
