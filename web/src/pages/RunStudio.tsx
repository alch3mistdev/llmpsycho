import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { createRun, getMetaModels, getRun, subscribeRunEvents } from "../lib/api";
import { BudgetBurnChart } from "../components/charts/BudgetBurnChart";
import { StageTimelineChart } from "../components/charts/StageTimelineChart";
import { useStudioStore } from "../store/useStudioStore";
import type { Provider } from "../lib/types";

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
    queryFn: getMetaModels
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
      },
      (error) => {
        setErrorText(`SSE error: ${String(error.type)}`);
      }
    );

    return () => close();
  }, [activeRunId, pushRunEvent]);

  const stageSummary = useMemo(() => {
    const counts = { A: 0, B: 0, C: 0 };
    for (const event of runEvents) {
      const stage = String(event.stage ?? "");
      if (stage === "A" || stage === "B" || stage === "C") {
        counts[stage] += 1;
      }
    }
    return counts;
  }, [runEvents]);

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

    if (fromApi.length > 0) {
      return fromApi;
    }
    return fallback[selectedProvider];
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
        token_cap: 14000
      }
    });
  };

  return (
    <section className="stack">
      <div className="hero-card">
        <h2>Run Studio</h2>
        <p>Launch adaptive profiling jobs and monitor stage progression, uncertainty convergence, and budget burn.</p>
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
        {errorText && <p className="error">{errorText}</p>}
      </form>

      <div className="grid-3">
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
      </div>

      <div className="grid-3">
        <div className="metric-card">
          <h3>Stage A</h3>
          <strong>{stageSummary.A}</strong>
        </div>
        <div className="metric-card">
          <h3>Stage B</h3>
          <strong>{stageSummary.B}</strong>
        </div>
        <div className="metric-card">
          <h3>Stage C</h3>
          <strong>{stageSummary.C}</strong>
        </div>
      </div>

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
        <h3>Run Events</h3>
        <div className="event-feed">
          {runEvents.slice(-80).reverse().map((event, index) => (
            <pre key={index}>{JSON.stringify(event, null, 2)}</pre>
          ))}
        </div>
      </article>

      <article className="panel-card">
        <h3>Model Availability Hints</h3>
        <ul className="flat-list">
          {(modelsQuery.data?.models ?? []).map((model, index) => (
            <li key={index}>
              <strong>{String(model.model_id)}</strong> <code>{String(model.provider)}</code>
              <div className="hint">{String(model.available_hint ?? "")}</div>
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}
