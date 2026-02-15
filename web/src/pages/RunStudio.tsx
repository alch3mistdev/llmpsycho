import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { BudgetBurnChart } from "../components/charts/BudgetBurnChart";
import { CriticalConfidenceChart } from "../components/charts/CriticalConfidenceChart";
import { StageTimelineChart } from "../components/charts/StageTimelineChart";
import { createRun, getMetaModels, getRun, subscribeRunEvents } from "../lib/api";
import type { Provider } from "../lib/types";
import { useStudioStore } from "../store/useStudioStore";

function mean(values: number[]) {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function RunStudio() {
  const {
    selectedModelId,
    selectedProvider,
    activeRunId,
    runEvents,
    setSelectedModelId,
    setSelectedProvider,
    setActiveRunId,
    pushRunEvent,
    clearRunEvents
  } = useStudioStore();
  const [errorText, setErrorText] = useState<string | null>(null);

  const modelsQuery = useQuery({
    queryKey: ["meta", "models"],
    queryFn: () => getMetaModels(true)
  });

  const runQuery = useQuery({
    queryKey: ["run", activeRunId],
    queryFn: () => getRun(activeRunId as string),
    enabled: Boolean(activeRunId),
    refetchInterval: 1500
  });

  const createRunMutation = useMutation({
    mutationFn: createRun,
    onSuccess: ({ run_id }) => {
      clearRunEvents();
      setErrorText(null);
      setActiveRunId(run_id);
    },
    onError: (error) => {
      setErrorText(String(error));
    }
  });

  useEffect(() => {
    if (!activeRunId) {
      return;
    }
    const close = subscribeRunEvents(
      activeRunId,
      (eventType, data) => {
        pushRunEvent({ eventType, ...(typeof data === "object" && data ? (data as object) : { data }) });
        if (eventType === "terminal" || eventType === "completed" || eventType === "failed") {
          setErrorText(null);
        }
      },
      () => {
        const status = String(runQuery.data?.status ?? "");
        if (status === "completed" || status === "failed") {
          return;
        }
        setErrorText("Live stream disconnected. Polling status instead.");
      }
    );
    return () => close();
  }, [activeRunId, pushRunEvent, runQuery.data?.status]);

  const stageSummary = useMemo(() => {
    const counts = { A: 0, B: 0, C: 0 };
    for (const event of runEvents) {
      if (String(event.eventType ?? "") !== "progress") {
        continue;
      }
      const stageCounts = event.stage_counts as Record<string, unknown> | undefined;
      if (stageCounts) {
        counts.A = Math.max(counts.A, Number(stageCounts.A ?? counts.A));
        counts.B = Math.max(counts.B, Number(stageCounts.B ?? counts.B));
        counts.C = Math.max(counts.C, Number(stageCounts.C ?? counts.C));
        continue;
      }
      const stage = String(event.stage ?? "");
      if (stage === "A" || stage === "B" || stage === "C") {
        counts[stage] += 1;
      }
    }
    return counts;
  }, [runEvents]);

  const latestProgress = useMemo(() => {
    const progress = runEvents.filter((event) => String(event.eventType ?? "") === "progress");
    return progress[progress.length - 1] ?? null;
  }, [runEvents]);

  const activeStage = String(latestProgress?.stage ?? "A");
  const confidenceScore = useMemo(() => {
    const reliability = latestProgress?.posterior_reliability as Record<string, unknown> | undefined;
    if (!reliability) {
      return 0;
    }
    return mean(Object.values(reliability).map((value) => Number(value ?? 0)));
  }, [latestProgress]);

  const providerModelOptions = useMemo(() => {
    const fallback: Record<Provider, string[]> = {
      simulated: ["simulated-local"],
      openai: ["gpt-4o", "gpt-4.1-mini"],
      anthropic: ["claude-3-5-sonnet-20241022"]
    };

    const fromApi = (modelsQuery.data?.models ?? [])
      .filter((model) => String(model.provider) === selectedProvider)
      .map((model) => String(model.model_id))
      .filter(Boolean);
    return fromApi.length > 0 ? fromApi : fallback[selectedProvider];
  }, [modelsQuery.data?.models, selectedProvider]);

  useEffect(() => {
    if (providerModelOptions.length === 0) {
      return;
    }
    if (!providerModelOptions.includes(selectedModelId)) {
      setSelectedModelId(providerModelOptions[0]);
    }
  }, [providerModelOptions, selectedModelId, setSelectedModelId]);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createRunMutation.mutate({
      model_id: selectedModelId,
      provider: selectedProvider,
      adapter_config: {
        max_tokens: 80
      },
      run_config_overrides: {
        call_cap: 60,
        token_cap: 14000,
        min_calls_before_global_stop: 40,
        min_items_per_critical_trait: 6
      }
    });
  };

  const runSummary = runQuery.data?.summary ?? {};

  return (
    <section className="stack" data-tour="run-studio">
      <div className="hero-card">
        <h2>Profiler Lab</h2>
        <p>
          Watch adaptive probing in motion. Each event includes previews of prompt/response and critical trait deltas
          so you can explain convergence, not just observe it.
        </p>
      </div>

      <form onSubmit={onSubmit} className="panel-card form-grid">
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
          <select value={selectedModelId} onChange={(event) => setSelectedModelId(event.target.value)}>
            {providerModelOptions.map((modelId) => (
              <option key={modelId} value={modelId}>
                {modelId}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={createRunMutation.isPending}>
          {createRunMutation.isPending ? "Starting..." : "Create Profile Run"}
        </button>
        {errorText && <p className="hint">{errorText}</p>}
      </form>

      <div className="grid-4">
        <div className="metric-card">
          <h3>Active Run</h3>
          <code>{activeRunId ?? "none"}</code>
        </div>
        <div className="metric-card">
          <h3>Status</h3>
          <strong>{runQuery.data?.status ?? "idle"}</strong>
        </div>
        <div className="metric-card">
          <h3>Events</h3>
          <strong>{runEvents.length}</strong>
        </div>
        <div className="metric-card">
          <h3>Convergence Confidence</h3>
          <strong>{confidenceScore.toFixed(3)}</strong>
        </div>
      </div>

      <article className="panel-card">
        <h3>Stage Animation Rail</h3>
        <div className="stage-rail">
          {[
            { stage: "A", label: "Coverage", count: stageSummary.A },
            { stage: "B", label: "Refinement", count: stageSummary.B },
            { stage: "C", label: "Robustness", count: stageSummary.C }
          ].map((row) => (
            <div key={row.stage} className={activeStage === row.stage ? "stage-node active" : "stage-node"}>
              <h4>
                Stage {row.stage}: {row.label}
              </h4>
              <strong>{row.count} probes</strong>
            </div>
          ))}
        </div>
      </article>

      <div className="grid-2">
        <article className="panel-card">
          <h3>Stage Timeline</h3>
          <StageTimelineChart events={runEvents} />
        </article>
        <article className="panel-card">
          <h3>Budget Burn</h3>
          <BudgetBurnChart events={runEvents} />
        </article>
      </div>

      <article className="panel-card">
        <h3>Critical Trait Confidence Trajectory</h3>
        <CriticalConfidenceChart events={runEvents} />
      </article>

      <article className="panel-card">
        <h3>Run Quality Summary</h3>
        <p>
          {runQuery.data?.status === "completed"
            ? "Run completed with convergence checks. Open Profile Anatomy to inspect full probe evidence."
            : "Run is active. Each probe event updates confidence, stage routing, and stop-condition readiness."}
        </p>
        <pre>{JSON.stringify(runSummary, null, 2)}</pre>
      </article>

      <article className="panel-card">
        <h3>Explainable Event Stream</h3>
        <div className="event-feed">
          {runEvents
            .slice(-80)
            .reverse()
            .map((event, index) => (
              <article key={index} className="attribution-item">
                <div className="attribution-head">
                  <strong>
                    {String(event.eventType ?? "event")} {typeof event.call_index === "number" ? `#${Number(event.call_index) + 1}` : ""}
                  </strong>
                  <span className="tag">{String(event.stage ?? "")}</span>
                </div>
                {"prompt_preview" in event && <p className="hint">Prompt: {String(event.prompt_preview ?? "")}</p>}
                {"response_preview" in event && <p className="hint">Response: {String(event.response_preview ?? "")}</p>}
                {"critical_delta_preview" in event && (
                  <pre>{JSON.stringify(event.critical_delta_preview ?? {}, null, 2)}</pre>
                )}
              </article>
            ))}
        </div>
      </article>
    </section>
  );
}
