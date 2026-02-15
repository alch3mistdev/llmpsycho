import type {
  AbRequest,
  AbResponse,
  ApplyRequest,
  ApplyResponse,
  EvaluateResponse,
  GlossaryResponse,
  IngestionStatus,
  MetaModelsResponse,
  ProbeCatalog,
  ProfileProbeTraceResponse,
  ProfileDetail,
  ProfileExplainResponse,
  ProfileIndex,
  QueryLabAnalyticsResponse,
  QueryLabEvaluateRequest,
  QueryLabTraceResponse,
  RunCreateRequest,
  RunCreateResponse,
  RunStatus
} from "./types";

const API_BASE = (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function health() {
  return request<{ status: string }>("/api/health");
}

export function createRun(body: RunCreateRequest): Promise<RunCreateResponse> {
  return request<RunCreateResponse>("/api/runs", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function getRun(runId: string): Promise<RunStatus> {
  return request<RunStatus>(`/api/runs/${runId}`);
}

export function subscribeRunEvents(
  runId: string,
  onEvent: (eventType: string, data: unknown) => void,
  onError?: (error: Event) => void
): () => void {
  const source = new EventSource(`${API_BASE}/api/runs/${runId}/events`);
  let closedByTerminal = false;

  source.onmessage = (event) => {
    try {
      onEvent("message", JSON.parse(event.data));
    } catch {
      onEvent("message", event.data);
    }
  };

  source.addEventListener("progress", (event: MessageEvent) => {
    onEvent("progress", JSON.parse(event.data));
  });
  source.addEventListener("completed", (event: MessageEvent) => {
    onEvent("completed", JSON.parse(event.data));
  });
  source.addEventListener("failed", (event: MessageEvent) => {
    onEvent("failed", JSON.parse(event.data));
  });
  source.addEventListener("terminal", (event: MessageEvent) => {
    onEvent("terminal", JSON.parse(event.data));
    closedByTerminal = true;
    source.close();
  });

  source.onerror = (error) => {
    if (closedByTerminal || source.readyState === EventSource.CLOSED) {
      return;
    }
    onError?.(error);
  };

  return () => {
    source.close();
  };
}

export function listProfiles(params?: {
  model_id?: string;
  provider?: string;
  converged?: boolean;
  limit?: number;
}): Promise<{ profiles: ProfileIndex[]; count: number }> {
  const url = new URL(`${API_BASE}/api/profiles`);
  if (params?.model_id) {
    url.searchParams.set("model_id", params.model_id);
  }
  if (params?.provider) {
    url.searchParams.set("provider", params.provider);
  }
  if (typeof params?.converged === "boolean") {
    url.searchParams.set("converged", String(params.converged));
  }
  if (params?.limit) {
    url.searchParams.set("limit", String(params.limit));
  }

  return fetch(url.toString()).then(async (response) => {
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return (await response.json()) as { profiles: ProfileIndex[]; count: number };
  });
}

export function getProfile(profileId: string): Promise<ProfileDetail> {
  return request<ProfileDetail>(`/api/profiles/${profileId}`);
}

export function getProfileExplain(profileId: string, regimeId = "core"): Promise<ProfileExplainResponse> {
  return request<ProfileExplainResponse>(`/api/profiles/${profileId}/explain?regime_id=${encodeURIComponent(regimeId)}`);
}

export function getProfileProbeTrace(
  profileId: string,
  params?: {
    regime_id?: string;
    stage?: string;
    family?: string;
    q?: string;
    offset?: number;
    limit?: number;
  }
): Promise<ProfileProbeTraceResponse> {
  const query = new URLSearchParams();
  if (params?.regime_id) {
    query.set("regime_id", params.regime_id);
  }
  if (params?.stage) {
    query.set("stage", params.stage);
  }
  if (params?.family) {
    query.set("family", params.family);
  }
  if (params?.q) {
    query.set("q", params.q);
  }
  if (typeof params?.offset === "number") {
    query.set("offset", String(params.offset));
  }
  if (typeof params?.limit === "number") {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString();
  return request<ProfileProbeTraceResponse>(
    `/api/profiles/${profileId}/probe-trace${suffix ? `?${suffix}` : ""}`
  );
}

export async function importProfile(file: File): Promise<{ profile_id: string; status: string; source: string }> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${API_BASE}/api/profiles/import`, {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as { profile_id: string; status: string; source: string };
}

export function scanIngestion(): Promise<{ scanned: number; results: unknown[] }> {
  return request<{ scanned: number; results: unknown[] }>("/api/ingestion/scan", {
    method: "POST"
  });
}

export function getIngestionStatus(): Promise<IngestionStatus> {
  return request<IngestionStatus>("/api/ingestion/status");
}

export function getMetaModels(forceRefresh = false): Promise<MetaModelsResponse> {
  const query = forceRefresh ? "?force_refresh=true" : "";
  return request<MetaModelsResponse>(`/api/meta/models${query}`);
}

export function getGlossary(): Promise<GlossaryResponse> {
  return request<GlossaryResponse>("/api/meta/glossary");
}

export function getProbeCatalog(): Promise<ProbeCatalog> {
  return request<ProbeCatalog>("/api/meta/probe-catalog");
}

export function getQueryLabAnalytics(): Promise<QueryLabAnalyticsResponse> {
  return request<QueryLabAnalyticsResponse>("/api/query-lab/analytics");
}

export function runAb(body: AbRequest): Promise<AbResponse> {
  return request<AbResponse>("/api/query-lab/ab", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function applyProfile(body: ApplyRequest): Promise<ApplyResponse> {
  return request<ApplyResponse>("/api/query-lab/apply", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function evaluateQueryResponse(body: QueryLabEvaluateRequest): Promise<EvaluateResponse> {
  return request<EvaluateResponse>("/api/query-lab/evaluate", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function getQueryLabTrace(traceId: string): Promise<QueryLabTraceResponse> {
  return request<QueryLabTraceResponse>(`/api/query-lab/traces/${traceId}`);
}
