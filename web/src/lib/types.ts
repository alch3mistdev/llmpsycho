export type Provider = "openai" | "anthropic" | "simulated";

export interface RunCreateRequest {
  model_id: string;
  provider: Provider;
  adapter_config?: Record<string, unknown>;
  run_config_overrides?: Record<string, unknown>;
  regimes?: Record<string, unknown>[];
}

export interface RunCreateResponse {
  job_id: string;
  run_id: string;
}

export interface RunStatus {
  run_id: string;
  status: string;
  model_id: string;
  provider: string;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error_text?: string | null;
  summary: Record<string, unknown>;
}

export interface ProfileIndex {
  profile_id: string;
  run_id?: string | null;
  model_id: string;
  provider: string;
  source: string;
  created_at: string;
  converged: boolean;
  checksum: string;
  diagnostics: Record<string, unknown>;
  risk_flags: Record<string, boolean>;
  artifact_path: string;
}

export interface TraitEstimate {
  trait: string;
  mean: number;
  sd: number;
  ci95: [number, number];
  reliability: number;
}

export interface ProfileDetail {
  profile_id: string;
  metadata: Record<string, unknown>;
  index: ProfileIndex;
  profile: {
    model_id: string;
    stop_reason: string;
    diagnostics: Record<string, unknown>;
    risk_flags: Record<string, boolean>;
    budget: {
      calls_used: number;
      tokens_prompt: number;
      tokens_completion: number;
    };
    regimes: Array<{
      regime_id: string;
      trait_estimates: TraitEstimate[];
    }>;
    records?: Array<Record<string, unknown>>;
  };
}

export interface IngestionStatus {
  running: boolean;
  last_scan_at?: string | null;
  imported_count: number;
  error_count: number;
  recent: Array<Record<string, unknown>>;
}

export interface AbRequest {
  profile_id: string;
  provider: Provider;
  model_id: string;
  query_text: string;
  regime_id: string;
  ab_mode: "same_model";
  adapter_config?: Record<string, unknown>;
}

export interface ApplyRequest {
  profile_id: string;
  provider: Provider;
  model_id: string;
  query_text: string;
  regime_id: string;
  adapter_config?: Record<string, unknown>;
}
