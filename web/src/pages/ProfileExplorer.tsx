import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { InfoTooltip } from "../components/InfoTooltip";
import { MetricDefinitionPopover } from "../components/MetricDefinitionPopover";
import { PlainLanguageCard } from "../components/PlainLanguageCard";
import { ProbeTimeline } from "../components/ProbeTimeline";
import { ScoringBreakdownCard } from "../components/ScoringBreakdownCard";
import { TraitDeltaBars } from "../components/TraitDeltaBars";
import { ProbeDynamicsRailChart } from "../components/charts/ProbeDynamicsRailChart";
import { TraitRadarChart } from "../components/charts/TraitRadarChart";
import {
  getGlossary,
  getProbeCatalog,
  getProfile,
  getProfileExplain,
  getProfileProbeTrace,
  listProfiles
} from "../lib/api";
import { useStudioStore } from "../store/useStudioStore";

const tabs = ["Overview", "How It Works", "Probe Theater", "Evidence"] as const;
type ExplorerTab = (typeof tabs)[number];

function parseTab(value: string | null): ExplorerTab {
  if (value === "How It Works") {
    return "How It Works";
  }
  if (value === "Probe Theater") {
    return "Probe Theater";
  }
  if (value === "Evidence") {
    return "Evidence";
  }
  return "Overview";
}

export function ProfileExplorer() {
  const [searchParams] = useSearchParams();
  const {
    selectedProfileId,
    setSelectedProfileId,
    explanationMode,
    selectedProbeCallIndex,
    setSelectedProbeCallIndex,
    playbackCallIndex,
    setPlaybackCallIndex
  } = useStudioStore();
  const [modelFilter, setModelFilter] = useState("");
  const [providerFilter, setProviderFilter] = useState("");
  const [activeRegimeId, setActiveRegimeId] = useState("core");
  const [activeTab, setActiveTab] = useState<ExplorerTab>(parseTab(searchParams.get("tab")));
  const [probeSearch, setProbeSearch] = useState("");

  useEffect(() => {
    setActiveTab(parseTab(searchParams.get("tab")));
  }, [searchParams]);

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

  const probeTraceQuery = useQuery({
    queryKey: ["profile", "probe-trace", selectedProfileId, activeRegimeId, probeSearch],
    queryFn: () =>
      getProfileProbeTrace(selectedProfileId as string, {
        regime_id: activeRegimeId,
        q: probeSearch || undefined,
        offset: 0,
        limit: 250
      }),
    enabled: Boolean(selectedProfileId)
  });

  const probeCatalogQuery = useQuery({
    queryKey: ["meta", "probe-catalog"],
    queryFn: getProbeCatalog
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

  const probeRows = probeTraceQuery.data?.items ?? [];
  useEffect(() => {
    if (probeRows.length === 0) {
      if (selectedProbeCallIndex !== null) {
        setSelectedProbeCallIndex(null);
      }
      if (playbackCallIndex !== null) {
        setPlaybackCallIndex(null);
      }
      return;
    }
    if (selectedProbeCallIndex === null || !probeRows.some((row) => row.call_index === selectedProbeCallIndex)) {
      setSelectedProbeCallIndex(probeRows[0].call_index);
      setPlaybackCallIndex(probeRows[0].call_index);
    }
  }, [probeRows, selectedProbeCallIndex, setPlaybackCallIndex, setSelectedProbeCallIndex]);

  const selectedProbe = probeRows.find((row) => row.call_index === selectedProbeCallIndex) ?? probeRows[0] ?? null;

  const callsUsed = Number(profileDetailQuery.data?.profile.budget.calls_used ?? 0);
  const tokensPrompt = Number(
    profileDetailQuery.data?.profile.budget.tokens_prompt ?? profileDetailQuery.data?.profile.budget.prompt_tokens ?? 0
  );
  const tokensCompletion = Number(
    profileDetailQuery.data?.profile.budget.tokens_completion ?? profileDetailQuery.data?.profile.budget.completion_tokens ?? 0
  );
  const totalTokens = tokensPrompt + tokensCompletion;
  const traceSummary = profileDetailQuery.data?.trace_summary;

  return (
    <section className="stack" data-tour="profile-anatomy">
      <div className="hero-card">
        <h2>Profile Anatomy</h2>
        <p>
          Move from TLDR to causal explanation to technical proof. Every probe can be inspected as prompt, response,
          score decomposition, and trait effect.
        </p>
      </div>

      <div className="panel-card form-grid">
        <label>
          Model filter
          <input value={modelFilter} onChange={(event) => setModelFilter(event.target.value)} placeholder="gpt-4o" />
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
          <h3>Profile History</h3>
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
          <h3>Run Snapshot</h3>
          {!profileDetailQuery.data && <p>Select a profile to inspect.</p>}
          {profileDetailQuery.data && (
            <>
              <div className="status-row">
                <span>Stop reason</span>
                <strong>{profileDetailQuery.data.profile.stop_reason}</strong>
              </div>
              <div className="status-row">
                <span>Calls used</span>
                <strong>{callsUsed}</strong>
              </div>
              <div className="status-row">
                <span>Total tokens</span>
                <strong>{totalTokens}</strong>
              </div>
              <div className="status-row">
                <span>Trace completeness</span>
                <strong>
                  {traceSummary
                    ? `${traceSummary.records_with_full_transcript}/${traceSummary.total_records} full transcripts`
                    : "n/a"}
                </strong>
              </div>
              <div className="regime-tabs">
                {(profileDetailQuery.data.profile.regimes ?? []).map((entry) => (
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
            </>
          )}
        </article>
      </div>

      <div className="tab-row" role="tablist" aria-label="Profile anatomy sections">
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

      {activeTab === "Overview" && (
        <div className="stack">
          <PlainLanguageCard
            title="What happened"
            summary={
              profileExplainQuery.data?.quick_take ??
              profileDetailQuery.data?.profile_summary?.quick_take ??
              "Profile interpretation is not available yet."
            }
          >
            <p className="hint">Use Probe Theater to inspect the exact probes behind this summary.</p>
          </PlainLanguageCard>
          <div className="grid-2">
            <article className="panel-card">
              <h3>Strengths</h3>
              <ul className="flat-list">
                {(profileDetailQuery.data?.profile_summary?.strengths ?? []).map((item) => (
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
                {(profileDetailQuery.data?.profile_summary?.risks ?? []).map((item) => (
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
              <h3>Trace Summary</h3>
              {!traceSummary && <p className="hint">Trace summary unavailable.</p>}
              {traceSummary && (
                <>
                  <div className="status-row">
                    <span>Total probes</span>
                    <strong>{traceSummary.total_records}</strong>
                  </div>
                  <div className="status-row">
                    <span>Full transcripts</span>
                    <strong>{traceSummary.records_with_full_transcript}</strong>
                  </div>
                  <div className="status-row">
                    <span>Partial trace</span>
                    <strong>{traceSummary.partial_trace ? "Yes" : "No"}</strong>
                  </div>
                </>
              )}
            </article>
            <article className="panel-card">
              {regime && <TraitRadarChart title={`Trait Profile (${regime.regime_id})`} traits={regime.trait_estimates} />}
            </article>
          </div>
        </div>
      )}

      {activeTab === "How It Works" && (
        <div className="stack" data-tour="how-it-works">
          <article className="panel-card">
            <h3>Stage Walkthrough</h3>
            <div className="stage-rail">
              {Object.entries(probeCatalogQuery.data?.stage_semantics ?? {}).map(([stage, detail]) => (
                <div key={stage} className={activeRegimeId === "safety" && stage === "C" ? "stage-node active" : "stage-node"}>
                  <h4>Stage {stage}</h4>
                  <p className="hint">{detail}</p>
                  <strong>{traceSummary?.stage_counts?.[stage] ?? 0} probes in this profile</strong>
                </div>
              ))}
            </div>
          </article>

          <div className="grid-2">
            <article className="panel-card">
              <h3>Probe Families</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Family</th>
                      <th>Primary Traits</th>
                      <th>Items</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(probeCatalogQuery.data?.probe_families ?? []).map((row) => (
                      <tr key={row.family}>
                        <td>{row.family}</td>
                        <td>{row.primary_traits.join(", ")}</td>
                        <td>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
            <article className="panel-card">
              <h3>Scoring Mechanics</h3>
              <ul className="flat-list">
                {(probeCatalogQuery.data?.scoring_mechanics ?? []).map((item) => (
                  <li key={item.scoring_type}>
                    <InfoTooltip
                      id={`score-${item.scoring_type}`}
                      title={item.scoring_type}
                      definition={item.description}
                      whyItMatters="Scoring type determines how evidence affects trait updates."
                      decisionImplication="Low scores in critical families should trigger deeper review or stricter intervention."
                    >
                      <code>{item.scoring_type}</code>
                    </InfoTooltip>
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </div>
      )}

      {activeTab === "Probe Theater" && (
        <div className="stack">
          <div className="panel-card form-grid">
            <label>
              Search probes
              <input value={probeSearch} onChange={(event) => setProbeSearch(event.target.value)} placeholder="item id, family, text..." />
            </label>
            <label>
              Playback call index
              <input
                type="number"
                value={playbackCallIndex ?? ""}
                onChange={(event) => setPlaybackCallIndex(event.target.value ? Number(event.target.value) : null)}
                placeholder="optional"
              />
            </label>
            {probeTraceQuery.data?.partial_trace && <p className="hint">Legacy profile: some response transcripts are unavailable.</p>}
          </div>

          <article className="panel-card">
            <h3>Trait Dynamics Rail</h3>
            <ProbeDynamicsRailChart
              rows={probeRows}
              activeCallIndex={selectedProbe?.call_index ?? null}
              onSelectCallIndex={(callIndex) => setSelectedProbeCallIndex(callIndex)}
            />
          </article>

          <div className="grid-2">
            <article className="panel-card">
              <h3>Probe Timeline</h3>
              <ProbeTimeline
                rows={probeRows}
                selectedCallIndex={selectedProbe?.call_index ?? null}
                onSelect={(row) => {
                  setSelectedProbeCallIndex(row.call_index);
                  setPlaybackCallIndex(row.call_index);
                }}
              />
            </article>

            <div className="stack">
              <article className="panel-card">
                <h3>Selected Probe</h3>
                {!selectedProbe && <p className="hint">No probe selected.</p>}
                {selectedProbe && (
                  <>
                    <div className="status-row">
                      <span>Call</span>
                      <strong>#{selectedProbe.call_index + 1}</strong>
                    </div>
                    <div className="status-row">
                      <span>Family</span>
                      <strong>{selectedProbe.family}</strong>
                    </div>
                    <div className="status-row">
                      <span>Expected vs observed</span>
                      <strong>
                        {selectedProbe.expected_probability.toFixed(3)} -&gt; {selectedProbe.score.toFixed(3)}
                      </strong>
                    </div>
                    <h4>Prompt</h4>
                    <pre>{selectedProbe.prompt_text ?? "Prompt unavailable in this artifact."}</pre>
                    <h4>Response</h4>
                    <pre>{selectedProbe.response_text ?? "Response transcript unavailable for this legacy profile."}</pre>
                  </>
                )}
              </article>
              <ScoringBreakdownCard row={selectedProbe} />
              <article className="panel-card">
                <h3>Trait Delta (this probe)</h3>
                <TraitDeltaBars before={selectedProbe?.posterior_before} after={selectedProbe?.posterior_after} />
              </article>
            </div>
          </div>
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
            <article className="panel-card">
              <h3>Technical Proof</h3>
              <pre>
                {JSON.stringify(
                  {
                    profile: profileDetailQuery.data?.profile,
                    trace_summary: profileDetailQuery.data?.trace_summary,
                    selected_probe: selectedProbe
                  },
                  null,
                  2
                )}
              </pre>
            </article>
          )}
          {explanationMode !== "Technical" && (
            <article className="panel-card">
              <h3>Evidence Summary</h3>
              <p>
                This profile used {callsUsed} probes and {totalTokens} total tokens. Probe Theater provides direct
                evidence for each score and trait update.
              </p>
            </article>
          )}
        </div>
      )}
    </section>
  );
}
