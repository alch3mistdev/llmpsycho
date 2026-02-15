import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { applyProfile, listProfiles, runAb } from "../lib/api";
import type { Provider } from "../lib/types";
import { useStudioStore } from "../store/useStudioStore";

export function QueryLab() {
  const { selectedProfileId, setSelectedProfileId, selectedProvider, setSelectedProvider, selectedModelId, setSelectedModelId } =
    useStudioStore();

  const [queryText, setQueryText] = useState("Summarize the likely causes of elevated API latency and suggest next checks.");
  const [regimeId, setRegimeId] = useState("core");

  const profilesQuery = useQuery({
    queryKey: ["profiles", "query-lab"],
    queryFn: () => listProfiles({ limit: 300 })
  });

  const abMutation = useMutation({
    mutationFn: runAb
  });

  const applyMutation = useMutation({
    mutationFn: applyProfile
  });

  const onRunAb = (event: FormEvent) => {
    event.preventDefault();
    if (!selectedProfileId) {
      return;
    }

    abMutation.mutate({
      profile_id: selectedProfileId,
      provider: selectedProvider,
      model_id: selectedModelId,
      query_text: queryText,
      regime_id: regimeId,
      ab_mode: "same_model"
    });
  };

  const onApplyOnly = () => {
    if (!selectedProfileId) {
      return;
    }
    applyMutation.mutate({
      profile_id: selectedProfileId,
      provider: selectedProvider,
      model_id: selectedModelId,
      query_text: queryText,
      regime_id: regimeId
    });
  };

  return (
    <section className="stack">
      <div className="hero-card">
        <h2>Query Lab</h2>
        <p>Apply profile-derived intervention plans to live queries and compare baseline vs treated responses.</p>
      </div>

      <form className="panel-card form-grid" onSubmit={onRunAb}>
        <label>
          Profile
          <select value={selectedProfileId ?? ""} onChange={(event) => setSelectedProfileId(event.target.value || null)}>
            <option value="">Select profile</option>
            {(profilesQuery.data?.profiles ?? []).map((profile) => (
              <option key={profile.profile_id} value={profile.profile_id}>
                {profile.profile_id} · {profile.model_id} · {profile.provider}
              </option>
            ))}
          </select>
        </label>
        <label>
          Provider
          <select value={selectedProvider} onChange={(event) => setSelectedProvider(event.target.value as Provider)}>
            <option value="simulated">simulated</option>
            <option value="openai">openai</option>
            <option value="anthropic">anthropic</option>
          </select>
        </label>
        <label>
          Model
          <input value={selectedModelId} onChange={(event) => setSelectedModelId(event.target.value)} />
        </label>
        <label>
          Regime
          <select value={regimeId} onChange={(event) => setRegimeId(event.target.value)}>
            <option value="core">core</option>
            <option value="safety">safety</option>
          </select>
        </label>
        <label className="full">
          Query
          <textarea value={queryText} onChange={(event) => setQueryText(event.target.value)} rows={4} />
        </label>
        <div className="inline-actions full">
          <button type="submit" disabled={abMutation.isPending || !selectedProfileId}>
            {abMutation.isPending ? "Running A/B..." : "Run A/B"}
          </button>
          <button type="button" onClick={onApplyOnly} disabled={applyMutation.isPending || !selectedProfileId}>
            {applyMutation.isPending ? "Applying..." : "Apply Profile Only"}
          </button>
        </div>
      </form>

      <div className="grid-2">
        <article className="panel-card">
          <h3>Intervention Plan</h3>
          <pre>
            {JSON.stringify(
              (abMutation.data as Record<string, unknown> | undefined)?.intervention_plan ??
                (applyMutation.data as Record<string, unknown> | undefined)?.intervention_plan ??
                {},
              null,
              2
            )}
          </pre>
        </article>
        <article className="panel-card">
          <h3>A/B Deltas</h3>
          <pre>{JSON.stringify((abMutation.data as Record<string, unknown> | undefined)?.diff ?? {}, null, 2)}</pre>
        </article>
      </div>

      <div className="grid-2">
        <article className="panel-card">
          <h3>Baseline Output</h3>
          <pre>{String((abMutation.data as Record<string, any> | undefined)?.baseline?.response_text ?? "")}</pre>
          <h4>Metrics</h4>
          <pre>{JSON.stringify((abMutation.data as Record<string, any> | undefined)?.metrics?.baseline ?? {}, null, 2)}</pre>
        </article>
        <article className="panel-card">
          <h3>Treated Output</h3>
          <pre>
            {String(
              (abMutation.data as Record<string, any> | undefined)?.treated?.response_text ??
                (applyMutation.data as Record<string, any> | undefined)?.result?.response_text ??
                ""
            )}
          </pre>
          <h4>Metrics</h4>
          <pre>
            {JSON.stringify(
              (abMutation.data as Record<string, any> | undefined)?.metrics?.treated ??
                (applyMutation.data as Record<string, any> | undefined)?.metrics ??
                {},
              null,
              2
            )}
          </pre>
        </article>
      </div>
    </section>
  );
}
