export type Provider = "openai" | "anthropic" | "simulated";
export type ExplanationMode = "Simple" | "Guided" | "Technical";

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

export interface ProfileStrengthOrRisk {
  trait: string;
  name: string;
  score: number;
  label: string;
  summary: string;
}

export interface ProfileSummary {
  strengths: ProfileStrengthOrRisk[];
  risks: ProfileStrengthOrRisk[];
  recommended_usage: string[];
  cautionary_usage: string[];
  quick_take: string;
}

export interface RegimeDelta {
  trait: string;
  name: string;
  core: number;
  safety: number;
  delta: number;
  direction: "up" | "down" | "flat";
}

export interface TraitDriver {
  trait: string;
  trait_name: string;
  rule: string;
  score: number;
  influence: number;
  direction: "risk" | "support";
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
      prompt_tokens?: number;
      completion_tokens?: number;
      tokens_prompt?: number;
      tokens_completion?: number;
    };
    regimes: Array<{
      regime_id: string;
      trait_estimates: TraitEstimate[];
    }>;
    records?: Array<Record<string, unknown>>;
  };
  profile_summary?: ProfileSummary;
  regime_deltas?: RegimeDelta[];
  trait_driver_map?: TraitDriver[];
  explainability_version?: number;
  trace_summary?: TraceSummary | null;
}

export interface ProfileExplainResponse {
  profile_id: string;
  index: ProfileIndex;
  regime_id: string;
  quick_take: string;
  summary: ProfileSummary;
  regime_delta_note: string;
  top_drivers: TraitDriver[];
  explainability_version: number;
}

export interface IngestionStatus {
  running: boolean;
  last_scan_at?: string | null;
  imported_count: number;
  error_count: number;
  recent: Array<Record<string, unknown>>;
}

export interface InterventionPlan {
  tier: string;
  strategy: string;
  decoding: Record<string, unknown>;
  system_addendum: string;
  query_prefix: string;
  max_tokens: number;
  rationale: string[];
  rules_applied: string[];
}

export interface QueryResult {
  response_text: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
}

export interface ResponseMetrics {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  intent_coverage: number;
  safety_score: number;
  structural_compliance: number;
}

export interface AlignmentRubricScore {
  name: string;
  weight: number;
  judge_score: number | null;
  deterministic_score: number;
  merged_score: number;
  confidence: number;
  confidence_label: "High" | "Medium" | "Low";
  rationale: string;
}

export interface AlignmentReport {
  overall_score: number;
  tier: "Excellent" | "Good" | "Weak" | "At Risk";
  rubric_scores: AlignmentRubricScore[];
  confidence: number;
  confidence_label: "High" | "Medium" | "Low";
  evaluator_model_id: string | null;
  mode: "hybrid" | "deterministic_only";
}

export interface InterventionAttribution {
  rule: string;
  traits: string[];
  primary_contribution: number;
  counterfactual_drop_estimate: number;
  confidence: number;
  direction: "positive" | "neutral";
}

export interface CausalRuleTrace {
  rule: string;
  condition: string;
  traits: string[];
  expected_effects: string[];
  triggered: boolean;
}

export interface InterventionCausalTrace {
  selected_traits: Array<{ trait: string; value: number }>;
  triggered_rules: CausalRuleTrace[];
  non_triggered_rules: CausalRuleTrace[];
  transformations: Array<{ type: string; value: unknown }>;
  expected_effects: string[];
  attribution: InterventionAttribution[];
}

export interface AbRequest {
  profile_id: string;
  provider: Provider;
  model_id: string;
  query_text: string;
  regime_id: string;
  ab_mode: "same_model";
  adapter_config?: Record<string, unknown>;
  disabled_rules?: string[];
}

export interface ApplyRequest {
  profile_id: string;
  provider: Provider;
  model_id: string;
  query_text: string;
  regime_id: string;
  adapter_config?: Record<string, unknown>;
  disabled_rules?: string[];
}

export interface QueryLabEvaluateRequest {
  query_text: string;
  response_text: string;
  provider: Provider;
  model_id: string;
  profile_id?: string;
  regime_id: string;
  adapter_config?: Record<string, unknown>;
}

export interface ApplyResponse {
  profile_id: string;
  provider: Provider;
  model_id: string;
  intervention_plan: InterventionPlan;
  result: QueryResult;
  metrics: ResponseMetrics;
  alignment_report: AlignmentReport;
  causal_trace: InterventionCausalTrace;
  confidence: number;
  evaluation_trace_id: string;
  intervention_trace_id: string;
}

export interface AbResponse {
  session_id: string;
  profile_id: string;
  provider: Provider;
  model_id: string;
  intervention_plan: InterventionPlan;
  baseline: QueryResult;
  treated: QueryResult;
  metrics: {
    baseline: ResponseMetrics;
    treated: ResponseMetrics;
  };
  alignment_report: {
    baseline: AlignmentReport;
    treated: AlignmentReport;
    delta: {
      overall_delta: number;
      rubric_deltas: Record<string, number>;
    };
  };
  attribution: InterventionAttribution[];
  causal_trace: InterventionCausalTrace;
  evaluation_trace_ids: {
    baseline: string;
    treated: string;
    intervention: string;
  };
  diff: {
    latency_delta_ms: number;
    token_delta: number;
    intent_delta: number;
    safety_delta: number;
    structure_delta: number;
    response_diff: string;
  };
}

export interface EvaluateResponse {
  trace_id: string;
  alignment_report: AlignmentReport;
  confidence: number;
}

export interface QueryLabTraceResponse {
  trace_type: "evaluation" | "intervention";
  trace: Record<string, unknown>;
}

export interface MetaModel {
  provider: Provider;
  model_id: string;
  label: string;
  available_hint: string;
  source: string;
}

export interface MetaModelsResponse {
  models: MetaModel[];
  refreshed_at?: string;
  errors?: Record<string, string>;
}

export interface QueryLabAnalyticsResponse {
  trend: Array<{
    timestamp: string;
    session_id: string;
    intent_delta: number;
    safety_delta: number;
    token_delta: number;
  }>;
  effective_interventions: Array<{
    rule: string;
    count: number;
    avg_intent_delta: number;
    avg_safety_delta: number;
    score: number;
  }>;
  total_ab_runs: number;
}

export interface GlossaryResponse {
  traits: Record<string, { name: string; simple: string }>;
  metrics: Record<string, string>;
  risk_flags: Record<string, string>;
  confidence_labels: Record<string, string>;
  feature_flags: {
    explainability_v2: boolean;
    explainability_v3?: boolean;
  };
}

export interface ProbeTraceRow {
  call_index: number;
  stage: string;
  regime_id: string;
  item_id: string;
  family: string;
  prompt_tokens: number;
  completion_tokens: number;
  expected_probability: number;
  score: number;
  score_components: Record<string, number>;
  prompt_text?: string;
  response_text?: string;
  scoring_type?: string;
  trait_loadings?: Record<string, number>;
  item_metadata?: Record<string, unknown>;
  posterior_before?: Record<string, unknown>;
  posterior_after?: Record<string, unknown>;
  selection_context?: Record<string, unknown>;
  has_full_transcript?: boolean;
}

export interface ProfileProbeTraceResponse {
  profile_id: string;
  count: number;
  total: number;
  offset: number;
  limit: number;
  partial_trace: boolean;
  items: ProbeTraceRow[];
}

export interface ProbeCatalogFamily {
  family: string;
  count: number;
  primary_traits: string[];
  primary_trait_names: string[];
  examples: Array<{
    item_id: string;
    prompt: string;
    scoring_type: string;
    trait_loadings: Record<string, number>;
    regime_tags: string[];
    is_ood: boolean;
    is_sentinel: boolean;
    paraphrase_group?: string | null;
  }>;
}

export interface ProbeCatalog {
  feature_enabled: boolean;
  message?: string;
  stage_semantics?: Record<string, string>;
  stopping_logic?: Record<string, unknown>;
  probe_families?: ProbeCatalogFamily[];
  scoring_mechanics?: Array<{ scoring_type: string; description: string }>;
}

export interface TraceSummary {
  total_records: number;
  records_with_full_transcript: number;
  records_with_enriched_fields: number;
  partial_trace: boolean;
  stage_counts: Record<string, number>;
  top_families: Array<{ family: string; count: number }>;
}

export interface TourState {
  never_show_auto: boolean;
  last_step: number;
  completed_at?: string | null;
}

export interface PinnedTooltip {
  id: string;
  title: string;
  content: string;
}
