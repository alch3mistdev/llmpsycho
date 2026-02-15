import type {
  AbRequest,
  ApplyRequest,
  IngestionStatus,
  ProfileDetail,
  ProfileIndex,
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
    // EventSource emits "error" when the stream closes; treat terminal close
    // as expected behavior instead of surfacing a UX error.
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

export function getMetaModels(): Promise<{ models: Array<Record<string, unknown>> }> {
  return request<{ models: Array<Record<string, unknown>> }>("/api/meta/models");
}

export function runAb(body: AbRequest): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/query-lab/ab", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export function applyProfile(body: ApplyRequest): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/query-lab/apply", {
    method: "POST",
    body: JSON.stringify(body)
  });
}
