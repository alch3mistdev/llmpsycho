import { screen } from "@testing-library/react";
import { vi } from "vitest";

import { ProfileExplorer } from "./ProfileExplorer";
import { renderWithProviders } from "../test/test-utils";
import { useStudioStore } from "../store/useStudioStore";

vi.mock("../lib/api", () => ({
  listProfiles: vi.fn(async () => ({
    profiles: [
      {
        profile_id: "p-1",
        model_id: "simulated-local",
        provider: "simulated",
        converged: true,
        source: "run",
        created_at: "2026-02-15T00:00:00+00:00",
        checksum: "x",
        diagnostics: {},
        risk_flags: {},
        artifact_path: "/tmp/p-1.json"
      }
    ],
    count: 1
  })),
  getProfile: vi.fn(async () => ({
    profile_id: "p-1",
    metadata: {},
    index: {
      profile_id: "p-1",
      model_id: "simulated-local",
      provider: "simulated",
      source: "run",
      created_at: "2026-02-15T00:00:00+00:00",
      converged: true,
      checksum: "x",
      diagnostics: {},
      risk_flags: {},
      artifact_path: "/tmp/p-1.json"
    },
    profile: {
      model_id: "simulated-local",
      stop_reason: "global_uncertainty_threshold_met",
      diagnostics: {},
      risk_flags: {},
      budget: { calls_used: 1, tokens_prompt: 20, tokens_completion: 10 },
      regimes: [
        {
          regime_id: "core",
          trait_estimates: [
            { trait: "T1", mean: 0.1, sd: 0.2, ci95: [-0.2, 0.3], reliability: 0.8 }
          ]
        }
      ]
    },
    trace_summary: {
      total_records: 1,
      records_with_full_transcript: 0,
      records_with_enriched_fields: 1,
      partial_trace: true,
      stage_counts: { A: 1, B: 0, C: 0 },
      top_families: [{ family: "intent_clarification", count: 1 }]
    }
  })),
  getProfileExplain: vi.fn(async () => ({
    profile_id: "p-1",
    regime_id: "core",
    quick_take: "Quick take",
    summary: {
      strengths: [],
      risks: [],
      recommended_usage: [],
      cautionary_usage: [],
      quick_take: "Quick take"
    },
    regime_delta_note: "",
    top_drivers: [],
    explainability_version: 2,
    index: {}
  })),
  getProfileProbeTrace: vi.fn(async () => ({
    profile_id: "p-1",
    count: 1,
    total: 1,
    offset: 0,
    limit: 250,
    partial_trace: true,
    items: [
      {
        call_index: 0,
        stage: "A",
        regime_id: "core",
        item_id: "I08",
        family: "intent_clarification",
        prompt_tokens: 20,
        completion_tokens: 10,
        expected_probability: 0.4,
        score: 0.1,
        score_components: { single_question: 0.0 },
        prompt_text: "Ask one question",
        scoring_type: "single_question",
        trait_loadings: { T5: 0.9 },
        has_full_transcript: false
      }
    ]
  })),
  getProbeCatalog: vi.fn(async () => ({
    feature_enabled: true,
    stage_semantics: { A: "Coverage", B: "Refine", C: "Robustness" },
    stopping_logic: {},
    probe_families: [],
    scoring_mechanics: []
  })),
  getGlossary: vi.fn(async () => ({
    traits: {},
    metrics: { overall_score: "desc" },
    risk_flags: {},
    confidence_labels: {},
    feature_flags: { explainability_v2: true, explainability_v3: true }
  }))
}));

describe("ProfileExplorer", () => {
  it("shows legacy fallback text when response transcript is missing", async () => {
    useStudioStore.setState({
      selectedProfileId: null,
      selectedProbeCallIndex: null,
      playbackCallIndex: null
    });
    renderWithProviders(<ProfileExplorer />, "/profiles?tab=Probe%20Theater");
    expect(await screen.findByText("Response transcript unavailable for this legacy profile.")).toBeInTheDocument();
  });
});
