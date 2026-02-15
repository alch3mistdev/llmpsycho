import { create } from "zustand";

import type { Provider } from "../lib/types";

interface StudioState {
  selectedProfileId: string | null;
  selectedProvider: Provider;
  selectedModelId: string;
  activeRunId: string | null;
  runEvents: Array<Record<string, unknown>>;
  setSelectedProfileId: (profileId: string | null) => void;
  setSelectedProvider: (provider: Provider) => void;
  setSelectedModelId: (modelId: string) => void;
  setActiveRunId: (runId: string | null) => void;
  pushRunEvent: (event: Record<string, unknown>) => void;
  clearRunEvents: () => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  selectedProfileId: null,
  selectedProvider: "simulated",
  selectedModelId: "simulated-local",
  activeRunId: null,
  runEvents: [],
  setSelectedProfileId: (selectedProfileId) => set({ selectedProfileId }),
  setSelectedProvider: (selectedProvider) => set({ selectedProvider }),
  setSelectedModelId: (selectedModelId) => set({ selectedModelId }),
  setActiveRunId: (activeRunId) => set({ activeRunId }),
  pushRunEvent: (event) => set((state) => ({ runEvents: [...state.runEvents, event] })),
  clearRunEvents: () => set({ runEvents: [] })
}));
