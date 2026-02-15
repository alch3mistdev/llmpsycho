import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { AttributionList } from "../components/AttributionList";
import { ConfidenceBadge } from "../components/ConfidenceBadge";
import { EvidenceDrawer } from "../components/EvidenceDrawer";
import { InfoTooltip } from "../components/InfoTooltip";
import { MetricDefinitionPopover } from "../components/MetricDefinitionPopover";
import { PlainLanguageCard } from "../components/PlainLanguageCard";
import { CausalFlowGraph } from "../components/charts/CausalFlowGraph";
import { RubricBreakdownBar } from "../components/charts/RubricBreakdownBar";
import { applyProfile, getGlossary, listProfiles, runAb } from "../lib/api";
import type { AbResponse, ApplyResponse, Provider } from "../lib/types";
import { useStudioStore } from "../store/useStudioStore";

const ruleOptions = [
  "low_refusal_or_jailbreak",
  "low_intent_understanding",
  "low_calibration",
  "low_truthfulness_or_overfit",
  "high_capability_compact_mode"
];

export function QueryLab() {
  const {
    selectedProfileId,
    setSelectedProfileId,
    selectedProvider,
    setSelectedProvider,
    selectedModelId,
    setSelectedModelId,
    explanationMode
  } = useStudioStore();

  const [queryText, setQueryText] = useState("Summarize likely causes of elevated API latency and suggest next checks.");
  const [regimeId, setRegimeId] = useState("core");
  const [disabledRules, setDisabledRules] = useState<string[]>([]);

  const profilesQuery = useQuery({
    queryKey: ["profiles", "query-lab"],
    queryFn: () => listProfiles({ limit: 300 })
  });
  const glossaryQuery = useQuery({
    queryKey: ["meta", "glossary"],
    queryFn: getGlossary
  });
  const abMutation = useMutation({ mutationFn: runAb });
  const applyMutation = useMutation({ mutationFn: applyProfile });

  const abData = abMutation.data as AbResponse | undefined;
  const applyData = applyMutation.data as ApplyResponse | undefined;
  const treatedAlignment = abData?.alignment_report?.treated ?? applyData?.alignment_report;
  const baselineAlignment = abData?.alignment_report?.baseline;

  const verdict = useMemo(() => {
    const delta = abData?.alignment_report?.delta?.overall_delta ?? 0;
    if (delta > 0.03) {
      return "Intervention improved alignment";
    }
    if (delta < -0.03) {
      return "Possible over-constraint";
    }
    return "No meaningful change";
  }, [abData]);

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
      ab_mode: "same_model",
      disabled_rules: disabledRules
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
      regime_id: regimeId,
      disabled_rules: disabledRules
    });
  };

  const toggleRule = (rule: string) => {
    setDisabledRules((current) => (current.includes(rule) ? current.filter((value) => value !== rule) : [...current, rule]));
  };

  const causalSteps = [
    {
      title: "1. Query Intent",
      body: queryText
    },
    {
      title: "2. Profile Evidence",
      body: selectedProfileId ? `Using profile ${selectedProfileId} (${regimeId})` : "Select a profile to continue."
    },
    {
      title: "3. Rule Triggers",
      body: (abData?.intervention_plan?.rules_applied ?? applyData?.intervention_plan?.rules_applied ?? []).join(", ") || "No rules yet."
    },
    {
      title: "4. Transformations",
      body:
        (abData?.intervention_plan?.system_addendum ?? applyData?.intervention_plan?.system_addendum ?? "No system addendum yet.") ||
        "No transform."
    },
    {
      title: "5. Result Deltas",
      body: abData
        ? `intent ${abData.diff.intent_delta.toFixed(3)}, safety ${abData.diff.safety_delta.toFixed(3)}, token ${abData.diff.token_delta}`
        : "Run A/B to produce deltas."
    }
  ];

  return (
    <section className="stack" data-tour="query-lab">
      <div className="hero-card">
        <h2>Intervention Simulator</h2>
        <p>
          Step through intent, profile evidence, rules, and output deltas. Use counterfactual toggles to understand
          what each rule contributes.
        </p>
      </div>

      <div className="lab-grid">
        <form className="panel-card stack" onSubmit={onRunAb}>
          <h3>Configuration</h3>
          <label>
            Profile
            <select value={selectedProfileId ?? ""} onChange={(event) => setSelectedProfileId(event.target.value || null)}>
              <option value="">Select profile</option>
              {(profilesQuery.data?.profiles ?? []).map((profile) => (
                <option key={profile.profile_id} value={profile.profile_id}>
                  {profile.profile_id} - {profile.model_id} - {profile.provider}
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
          <label>
            Query
            <textarea value={queryText} onChange={(event) => setQueryText(event.target.value)} rows={5} />
          </label>

          <fieldset className="rule-toggle-group">
            <legend>Counterfactual controls (disable rules)</legend>
            {ruleOptions.map((rule) => (
              <label key={rule} className="check-row">
                <input type="checkbox" checked={disabledRules.includes(rule)} onChange={() => toggleRule(rule)} />
                <span>{rule}</span>
              </label>
            ))}
          </fieldset>

          <div className="inline-actions">
            <button type="submit" disabled={abMutation.isPending || !selectedProfileId}>
              {abMutation.isPending ? "Running A/B..." : "Run A/B"}
            </button>
            <button type="button" onClick={onApplyOnly} disabled={applyMutation.isPending || !selectedProfileId}>
              {applyMutation.isPending ? "Applying..." : "Apply Profile Only"}
            </button>
          </div>

          <InfoTooltip
            id="overall-delta"
            title="Overall Alignment Delta"
            definition="Difference between treated and baseline overall alignment scores."
            whyItMatters="Positive deltas imply intervention improved response quality."
            decisionImplication="Sustained negative deltas indicate over-constraining rules."
          >
            <span className="tag">Metric help</span>
          </InfoTooltip>

          {abData && (
            <PlainLanguageCard title="Verdict" summary={verdict}>
              <p className="hint">Overall alignment delta: {abData.alignment_report.delta.overall_delta.toFixed(3)}</p>
            </PlainLanguageCard>
          )}
        </form>

        <div className="stack">
          <article className="panel-card">
            <h3>Causal Stepper</h3>
            <div className="stepper">
              {causalSteps.map((step) => (
                <div key={step.title} className="stepper-row">
                  <strong>{step.title}</strong>
                  <p className="hint">{step.body}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="panel-card">
            <h3>Causal Flow</h3>
            {(abData?.causal_trace || applyData?.causal_trace) ? (
              <CausalFlowGraph trace={(abData?.causal_trace ?? applyData?.causal_trace)!} />
            ) : (
              <p className="hint">Run Query Lab to generate trace.</p>
            )}
          </article>

          <article className="panel-card">
            <h3>Alignment Confidence</h3>
            {!treatedAlignment && <p className="hint">No alignment report yet.</p>}
            {treatedAlignment && (
              <>
                <div className="status-row">
                  <span>Treated score</span>
                  <strong>{treatedAlignment.overall_score.toFixed(3)}</strong>
                </div>
                <div className="status-row">
                  <span>Tier</span>
                  <strong>{treatedAlignment.tier}</strong>
                </div>
                <div className="status-row">
                  <span>Confidence</span>
                  <ConfidenceBadge label={treatedAlignment.confidence_label} score={treatedAlignment.confidence} />
                </div>
                {baselineAlignment && (
                  <div className="status-row">
                    <span>Baseline score</span>
                    <strong>{baselineAlignment.overall_score.toFixed(3)}</strong>
                  </div>
                )}
              </>
            )}
          </article>

          {treatedAlignment && <RubricBreakdownBar baseline={baselineAlignment} treated={treatedAlignment} />}
        </div>
      </div>

      <div className="grid-2">
        <article className="panel-card">
          <h3>Baseline Output</h3>
          <pre>{abData?.baseline.response_text ?? ""}</pre>
          <h4>Metrics</h4>
          <pre>{JSON.stringify(abData?.metrics.baseline ?? {}, null, 2)}</pre>
          <EvidenceDrawer
            title="Baseline Evidence"
            traceId={abData?.evaluation_trace_ids?.baseline}
            fallback={abData?.alignment_report?.baseline as unknown as Record<string, unknown>}
          />
        </article>
        <article className="panel-card">
          <h3>Treated Output</h3>
          <pre>{abData?.treated.response_text ?? applyData?.result.response_text ?? ""}</pre>
          <h4>Metrics</h4>
          <pre>{JSON.stringify(abData?.metrics.treated ?? applyData?.metrics ?? {}, null, 2)}</pre>
          <EvidenceDrawer
            title="Treated Evidence"
            traceId={abData?.evaluation_trace_ids?.treated ?? applyData?.evaluation_trace_id}
            fallback={treatedAlignment as unknown as Record<string, unknown>}
          />
        </article>
      </div>

      <article className="panel-card">
        <h3>Rule Attribution</h3>
        <AttributionList rows={(abData?.attribution ?? applyData?.causal_trace?.attribution ?? []).slice(0, 8)} />
      </article>

      <article className="panel-card">
        <h3>Intervention Plan + Deltas</h3>
        <div className="grid-2">
          <pre>{JSON.stringify(abData?.intervention_plan ?? applyData?.intervention_plan ?? {}, null, 2)}</pre>
          <pre>{JSON.stringify(abData?.diff ?? {}, null, 2)}</pre>
        </div>
        <EvidenceDrawer
          title="Intervention Causal Trace"
          traceId={abData?.evaluation_trace_ids?.intervention ?? applyData?.intervention_trace_id}
          fallback={(abData?.causal_trace ?? applyData?.causal_trace) as unknown as Record<string, unknown>}
        />
      </article>

      <article className="panel-card">
        <h3>Metrics Glossary</h3>
        <div className="glossary-grid">
          {Object.entries(glossaryQuery.data?.metrics ?? {}).map(([term, definition]) => (
            <MetricDefinitionPopover key={term} term={term} definition={definition} />
          ))}
        </div>
      </article>

      {explanationMode === "Technical" && (
        <article className="panel-card">
          <h3>Technical Proof</h3>
          <pre>{JSON.stringify({ ab: abData, apply: applyData }, null, 2)}</pre>
        </article>
      )}
    </section>
  );
}
