# Stage 2: Explainable Alignment UX

## Why this stage exists

Stage 2 changes the product goal from "profile generation only" to **alignment-quality decision support**.

Primary goal:
- maximize intent-result accuracy and alignment quality.

Secondary goal:
- make it clear why specific models/interventions work and how profile evidence produced those interventions.

## UX model: progressive disclosure

All major views use three explanation layers:

1. Quick Take (`Simple`): plain-language verdict and what it means.
2. Why it Works (`Guided`): causal and comparative visuals.
3. Technical Proof (`Technical`): formulas, thresholds, rubric details, and raw trace payloads.

Global mode toggle in app header:
- `Simple`
- `Guided`
- `Technical`

## Profile Explorer (v2)

Profile Explorer now emphasizes four analysis tabs:

1. **Snapshot**
- quick summary
- top strengths/risks
- confidence chips by trait
- practical usage guidance

2. **Relationships**
- regime delta dumbbell chart (core vs safety)
- trait-driver heatmap (trait ↔ intervention rule coupling)
- top driver table

3. **Derivation**
- stage-level probe accumulation signals
- trait reliability/CI summary
- probe evidence sample for guided/technical users

4. **Evidence**
- glossary-assisted metric definitions
- full raw payloads in technical mode

## Query Lab (v2)

A/B is presented as a causal pipeline:

`Query intent -> Profile evidence -> Rule triggers -> Transformations -> Result deltas`

Core additions:
- intent alignment score with confidence
- rubric breakdown (intent fidelity, completeness, safety, factual caution, format)
- rule-level attribution with counterfactual drop estimates
- counterfactual controls (disable specific rules)
- evidence drawers backed by persisted trace IDs

Verdict states:
- Intervention improved alignment
- No meaningful change
- Possible over-constraint

## Hybrid alignment evaluation

Each scored response now combines:

1. Deterministic checks
- intent keyword coverage
- safety heuristic score
- structural compliance
- token/latency metrics

2. Evaluator-model rubric pass
- semantic rubric scoring and rationales

3. Hybrid merge
- per-dimension merged score plus confidence
- fallback to deterministic-only mode with explicit degraded confidence if evaluator is unavailable

## Explainability trace model

For each intervention run, traces capture:
- selected trait values and risk flags
- triggered and non-triggered rules
- prompt/system transformations
- expected effect tags
- observed A/B deltas and attribution ranking

Persistence includes:
- `evaluation_traces`
- `intervention_traces`
- trace references in `ab_results`

## New API surfaces

- `GET /api/profiles/{profile_id}` now includes summary/deltas/driver map.
- `GET /api/profiles/{profile_id}/explain` returns plain-language interpretation.
- `POST /api/query-lab/apply` and `POST /api/query-lab/ab` include alignment report + causal trace + confidence.
- `POST /api/query-lab/evaluate` evaluates single output text.
- `GET /api/query-lab/traces/{trace_id}` returns persisted evidence payload.
- `GET /api/query-lab/analytics` provides trend/effectiveness aggregates.
- `GET /api/meta/glossary` serves user-friendly metric/trait/risk definitions.

## Operational notes

- Explainability v2 is additive and backward compatible for profile artifacts.
- Existing psychometric core remains unchanged.
- The evaluator model/provider can be configured by environment settings.
