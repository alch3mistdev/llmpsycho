import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getProfile, listProfiles } from "../lib/api";
import { TraitRadarChart } from "../components/charts/TraitRadarChart";
import { useStudioStore } from "../store/useStudioStore";

export function ProfileExplorer() {
  const { selectedProfileId, setSelectedProfileId } = useStudioStore();
  const [modelFilter, setModelFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [activeRegimeId, setActiveRegimeId] = useState("core");

  const profilesQuery = useQuery({
    queryKey: ["profiles", modelFilter, providerFilter],
    queryFn: () => listProfiles({ model_id: modelFilter || undefined, provider: providerFilter || undefined, limit: 500 })
  });

  useEffect(() => {
    if (!selectedProfileId && profilesQuery.data?.profiles?.[0]) {
      setSelectedProfileId(profilesQuery.data.profiles[0].profile_id);
    }
  }, [profilesQuery.data, selectedProfileId, setSelectedProfileId]);

  const profileDetailQuery = useQuery({
    queryKey: ["profile", selectedProfileId],
    queryFn: () => getProfile(selectedProfileId as string),
    enabled: Boolean(selectedProfileId)
  });

  const regime = useMemo(() => {
    const regimes = profileDetailQuery.data?.profile.regimes ?? [];
    return regimes.find((entry) => entry.regime_id === activeRegimeId) ?? regimes[0];
  }, [profileDetailQuery.data, activeRegimeId]);

  useEffect(() => {
    if (regime?.regime_id) {
      setActiveRegimeId(regime.regime_id);
    }
  }, [regime?.regime_id]);

  return (
    <section className="stack">
      <div className="hero-card">
        <h2>Profile Explorer</h2>
        <p>Filter profile history, inspect trait confidence, and review diagnostics and risk flags.</p>
      </div>

      <div className="panel-card form-grid">
        <label>
          Model filter
          <input value={modelFilter} onChange={(event) => setModelFilter(event.target.value)} placeholder="e.g., gpt-4o" />
        </label>
        <label>
          Provider filter
          <input
            value={providerFilter}
            onChange={(event) => setProviderFilter(event.target.value)}
            placeholder="openai / anthropic / simulated"
          />
        </label>
      </div>

      <div className="grid-2">
        <article className="panel-card">
          <h3>History</h3>
          <div className="table-wrap tall-table">
            <table>
              <thead>
                <tr>
                  <th>Profile ID</th>
                  <th>Model</th>
                  <th>Provider</th>
                  <th>Converged</th>
                </tr>
              </thead>
              <tbody>
                {(profilesQuery.data?.profiles ?? []).map((profile) => (
                  <tr
                    key={profile.profile_id}
                    className={selectedProfileId === profile.profile_id ? "selected" : ""}
                    onClick={() => setSelectedProfileId(profile.profile_id)}
                  >
                    <td>{profile.profile_id}</td>
                    <td>{profile.model_id}</td>
                    <td>{profile.provider}</td>
                    <td>{profile.converged ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel-card">
          <h3>Profile Detail</h3>
          {!profileDetailQuery.data && <p>Select a profile from history.</p>}
          {profileDetailQuery.data && (
            <>
              <div className="status-row">
                <span>Stop Reason</span>
                <strong>{profileDetailQuery.data.profile.stop_reason}</strong>
              </div>
              <div className="status-row">
                <span>Calls Used</span>
                <strong>{profileDetailQuery.data.profile.budget.calls_used}</strong>
              </div>
              <div className="status-row">
                <span>Tokens</span>
                <strong>
                  {profileDetailQuery.data.profile.budget.tokens_prompt +
                    profileDetailQuery.data.profile.budget.tokens_completion}
                </strong>
              </div>

              <div className="regime-tabs">
                {profileDetailQuery.data.profile.regimes.map((entry) => (
                  <button
                    key={entry.regime_id}
                    className={activeRegimeId === entry.regime_id ? "chip active" : "chip"}
                    onClick={() => setActiveRegimeId(entry.regime_id)}
                  >
                    {entry.regime_id}
                  </button>
                ))}
              </div>

              {regime && <TraitRadarChart title={`Trait Profile (${regime.regime_id})`} traits={regime.trait_estimates} />}

              <h4>Risk Flags</h4>
              <pre>{JSON.stringify(profileDetailQuery.data.profile.risk_flags, null, 2)}</pre>
            </>
          )}
        </article>
      </div>
    </section>
  );
}
