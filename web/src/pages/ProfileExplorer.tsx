import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ConfidenceBadge } from "../components/ConfidenceBadge";
import { MetricDefinitionPopover } from "../components/MetricDefinitionPopover";
import { PlainLanguageCard } from "../components/PlainLanguageCard";
import { RegimeDeltaDumbbellChart } from "../components/charts/RegimeDeltaDumbbellChart";
import { TraitDriverHeatmap } from "../components/charts/TraitDriverHeatmap";
import { TraitRadarChart } from "../components/charts/TraitRadarChart";
import { getGlossary, getProfile, getProfileExplain, listProfiles } from "../lib/api";
import { useStudioStore } from "../store/useStudioStore";

const tabs = ["Snapshot", "Relationships", "Derivation", "Evidence"] as const;

type ExplorerTab = (typeof tabs)[number];

function reliabilityConfidence(reliability: number): "High" | "Medium" | "Low" {
  if (reliability >= 0.85) {
    return "High";
  }
  if (reliability >= 0.7) {
    return "Medium";
  }
  return "Low";
}

export function ProfileExplorer() {
  const { selectedProfileId, setSelectedProfileId, explanationMode } = useStudioStore();
  const [modelFilter, setModelFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [activeRegimeId, setActiveRegimeId] = useState("core");
  const [activeTab, setActiveTab] = useState<ExplorerTab>("Snapshot");

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

  const profileExplainQuery = useQuery({
    queryKey: ["profile", "explain", selectedProfileId, activeRegimeId],
    queryFn: () => getProfileExplain(selectedProfileId as string, activeRegimeId),
    enabled: Boolean(selectedProfileId)
  });

  const glossaryQuery = useQuery({
    queryKey: ["meta", "glossary"],
    queryFn: getGlossary
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

  const callsUsed = Number(profileDetailQuery.data?.profile.budget.calls_used ?? 0);
  const tokensPrompt = Number(
    profileDetailQuery.data?.profile.budget.tokens_prompt ?? profileDetailQuery.data?.profile.budget.prompt_tokens ?? 0
  );
  const tokensCompletion = Number(
    profileDetailQuery.data?.profile.budget.tokens_completion ?? profileDetailQuery.data?.profile.budget.completion_tokens ?? 0
  );
  const totalTokens = tokensPrompt + tokensCompletion;

  const diagnostics = profileDetailQuery.data?.profile.diagnostics ?? {};
  const runRecords = profileDetailQuery.data?.profile.records ?? [];

  return (
    <section className="stack">
      <div className="hero-card">
        <h2>Profile Explorer</h2>
        <p>
          Understand what the profile means, why interventions trigger, and how confidence converged. Use the tabs to
          move from plain-language summary to technical proof.
        </p>
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

      <div className="grid-2 explorer-layout">
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
          <h3>Profile Snapshot</h3>
          {!profileDetailQuery.data && <p>Select a profile from history.</p>}
          {profileDetailQuery.data && (
            <>
              <div className="status-row">
                <span>Stop Reason</span>
                <strong>{profileDetailQuery.data.profile.stop_reason}</strong>
              </div>
              <div className="status-row">
                <span>Calls Used</span>
                <strong>{callsUsed}</strong>
              </div>
              <div className="status-row">
                <span>Total Tokens</span>
                <strong>{totalTokens}</strong>
              </div>
              <div className="status-row">
                <span>Quick Take</span>
                <strong>{profileExplainQuery.data?.quick_take ?? profileDetailQuery.data.profile_summary?.quick_take ?? "n/a"}</strong>
              </div>

              <div className="regime-tabs">
                {profileDetailQuery.data.profile.regimes.map((entry) => (
                  <button
                    key={entry.regime_id}
                    className={activeRegimeId === entry.regime_id ? "chip active" : "chip"}
                    onClick={() => setActiveRegimeId(entry.regime_id)}
                    type="button"
                  >
                    {entry.regime_id}
                  </button>
                ))}
              </div>

              {regime && (
                <div className="confidence-chip-row" aria-label="Trait confidence chips">
                  {regime.trait_estimates.slice(0, 8).map((trait) => (
                    <div key={trait.trait} className="confidence-chip">
                      <span>{trait.trait}</span>
                      <ConfidenceBadge label={reliabilityConfidence(trait.reliability)} />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </article>
      </div>

      {profileDetailQuery.data && regime && (
        <>
          <div className="tab-row" role="tablist" aria-label="Profile explorer sections">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={activeTab === tab}
                className={activeTab === tab ? "chip active" : "chip"}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === "Snapshot" && (
            <div className="stack">
              <PlainLanguageCard
                title="Quick Take"
                summary={
                  profileExplainQuery.data?.quick_take ??
                  profileDetailQuery.data.profile_summary?.quick_take ??
                  "This profile summary is not available yet."
                }
              >
                {explanationMode !== "Simple" && (
                  <p className="hint">
                    Why it works: intervention tiers are selected from low-trait risk concentration and safety flags.
                  </p>
                )}
              </PlainLanguageCard>

              <div className="grid-2">
                <article className="panel-card">
                  <h3>Strengths</h3>
                  <ul className="flat-list">
                    {(profileDetailQuery.data.profile_summary?.strengths ?? []).map((item) => (
                      <li key={item.trait}>
                        <strong>{item.name}</strong> ({item.score.toFixed(2)})
                        <p className="hint">{item.summary}</p>
                      </li>
                    ))}
                  </ul>
                </article>
                <article className="panel-card">
                  <h3>Risks</h3>
                  <ul className="flat-list">
                    {(profileDetailQuery.data.profile_summary?.risks ?? []).map((item) => (
                      <li key={item.trait}>
                        <strong>{item.name}</strong> ({item.score.toFixed(2)})
                        <p className="hint">{item.summary}</p>
                      </li>
                    ))}
                  </ul>
                </article>
              </div>

              <div className="grid-2">
                <article className="panel-card">
                  <h3>What this means for users</h3>
                  <h4>Recommended usage</h4>
                  <ul className="flat-list">
                    {(profileDetailQuery.data.profile_summary?.recommended_usage ?? []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <h4>Cautionary usage</h4>
                  <ul className="flat-list">
                    {(profileDetailQuery.data.profile_summary?.cautionary_usage ?? []).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </article>
                <article className="panel-card">
                  <TraitRadarChart title={`Trait Profile (${regime.regime_id})`} traits={regime.trait_estimates} />
                </article>
              </div>
            </div>
          )}

          {activeTab === "Relationships" && (
            <div className="stack">
              <div className="grid-2">
                <article className="panel-card">
                  <h3>Regime Delta</h3>
                  <p className="hint">Dumbbell view of core vs safety trait shifts.</p>
                  <RegimeDeltaDumbbellChart rows={profileDetailQuery.data.regime_deltas ?? []} />
                </article>
                <article className="panel-card">
                  <h3>Trait Driver Matrix</h3>
                  <p className="hint">Links profile traits to likely intervention rule activation.</p>
                  <TraitDriverHeatmap rows={profileDetailQuery.data.trait_driver_map ?? []} />
                </article>
              </div>

              <article className="panel-card">
                <h3>Top Drivers</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Trait</th>
                        <th>Rule</th>
                        <th>Influence</th>
                        <th>Direction</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(profileExplainQuery.data?.top_drivers ?? []).map((driver) => (
                        <tr key={`${driver.trait}-${driver.rule}`}>
                          <td>{driver.trait_name}</td>
                          <td>{driver.rule}</td>
                          <td>{Number(driver.influence).toFixed(3)}</td>
                          <td>{driver.direction}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            </div>
          )}

          {activeTab === "Derivation" && (
            <div className="stack">
              <article className="panel-card">
                <h3>Profile Derivation Timeline</h3>
                <p className="hint">
                  Probe accumulation across stages. Stage-level calls are read from diagnostics and response records.
                </p>
                <div className="grid-3">
                  <div className="metric-card">
                    <h3>Stage A</h3>
                    <strong>{Number(diagnostics.calls_in_stage_a ?? 0)}</strong>
                  </div>
                  <div className="metric-card">
                    <h3>Stage B</h3>
                    <strong>{Number(diagnostics.calls_in_stage_b ?? 0)}</strong>
                  </div>
                  <div className="metric-card">
                    <h3>Stage C</h3>
                    <strong>{Number(diagnostics.calls_in_stage_c ?? 0)}</strong>
                  </div>
                </div>
              </article>

              <article className="panel-card">
                <h3>Critical Trait Reliability</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Trait</th>
                        <th>Mean</th>
                        <th>Reliability</th>
                        <th>95% CI</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {regime.trait_estimates.slice(0, 12).map((row) => (
                        <tr key={row.trait}>
                          <td>{row.trait}</td>
                          <td>{row.mean.toFixed(3)}</td>
                          <td>{row.reliability.toFixed(3)}</td>
                          <td>
                            [{row.ci95[0].toFixed(3)}, {row.ci95[1].toFixed(3)}]
                          </td>
                          <td>
                            <ConfidenceBadge label={reliabilityConfidence(row.reliability)} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              {explanationMode !== "Simple" && (
                <article className="panel-card">
                  <h3>Probe Evidence Sample</h3>
                  <pre>{JSON.stringify(runRecords.slice(0, 10), null, 2)}</pre>
                </article>
              )}
            </div>
          )}

          {activeTab === "Evidence" && (
            <div className="stack">
              <article className="panel-card">
                <h3>Glossary</h3>
                <div className="glossary-grid">
                  {Object.entries(glossaryQuery.data?.metrics ?? {}).map(([term, definition]) => (
                    <MetricDefinitionPopover key={term} term={term} definition={definition} />
                  ))}
                </div>
              </article>

              {explanationMode === "Technical" && (
                <>
                  <article className="panel-card">
                    <h3>Technical Proof: Profile Payload</h3>
                    <pre>{JSON.stringify(profileDetailQuery.data.profile, null, 2)}</pre>
                  </article>
                  <article className="panel-card">
                    <h3>Technical Proof: Explainability Payload</h3>
                    <pre>{JSON.stringify(profileExplainQuery.data ?? {}, null, 2)}</pre>
                  </article>
                </>
              )}

              {explanationMode !== "Technical" && (
                <article className="panel-card">
                  <h3>Evidence Summary</h3>
                  <p>
                    This profile is derived from {callsUsed} probes and {totalTokens} tokens with stage sampling,
                    reliability checks, and robustness sentinels.
                  </p>
                </article>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
