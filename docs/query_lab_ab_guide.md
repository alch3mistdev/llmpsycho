# Query Lab A/B Guide

## Goal

Query Lab measures intervention effect by keeping the provider/model fixed and comparing:

- **Baseline**: profile intervention disabled.
- **Treated**: profile-derived rule plan enabled.

This isolates policy impact from model selection confounds.

## Intervention tiers

- `L0`: minimal transform, compact efficiency mode.
- `L1`: light guardrails.
- `L2`: moderate compensators (calibration/clarification/grounding additions).
- `L3`: strict safe mode with refusal emphasis.

## A/B execution contract

Request endpoint: `POST /api/query-lab/ab`

Required fields:

- `profile_id`
- `provider`
- `model_id`
- `query_text`
- `regime_id`
- `ab_mode="same_model"`

Returns:

- `baseline`
- `treated`
- `intervention_plan`
- `metrics.baseline`
- `metrics.treated`
- `diff`

## Metric definitions

- `total_tokens`: prompt + completion tokens.
- `latency_ms`: end-to-end response latency.
- `intent_coverage`: lexical proxy for query intent coverage.
- `safety_score`: heuristic based on unsafe content + refusal behavior.
- `structural_compliance`: length/format sanity proxy.

## Reading A/B outcomes

1. Positive `safety_delta` with small token increase usually indicates desirable compensator behavior.
2. Large token increase with negligible quality gain suggests over-constraining intervention.
3. Negative `intent_delta` indicates intervention may be too defensive; inspect tier/rules.
4. Repeatedly unstable deltas across similar queries suggest profile instability or overly coarse rules.

## Apply-only mode

`POST /api/query-lab/apply` runs the treated path only.

Use this for production-style invocation when you already trust the intervention policy and do not need a baseline comparison each time.
