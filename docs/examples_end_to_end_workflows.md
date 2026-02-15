# End-to-End Workflow Examples

## Workflow A: Create a fresh profile and inspect results

1. Open Run Studio.
2. Select provider/model.
3. Start run and watch SSE progress updates.
4. Wait for terminal event (`completed` or `failed`).
5. Open Profile Explorer and inspect trait/risk results.
6. Confirm convergence diagnostics before making routing decisions.

## Workflow B: Ingest external profile and compare with local history

1. Copy external profile JSON into `data/ingestion/` or upload in Ingestion Center.
2. Trigger manual scan if needed.
3. Confirm imported status and profile ID.
4. Open Profile Explorer and compare diagnostics/risk flags with existing profiles.

## Workflow C: A/B test intervention for a production-like query

1. Open Query Lab.
2. Select profile and target provider/model.
3. Enter representative query text.
4. Run A/B (`same_model` mode).
5. Inspect `token_delta`, `latency_delta_ms`, `intent_delta`, and `safety_delta`.
6. Keep or adjust intervention based on measured tradeoff.

## Workflow D: Build an alignment compensator policy

1. Identify models with low `T8/T9` or high `benchmark_overfit` risk.
2. Run Query Lab across a representative prompt set.
3. Track intervention tier behavior and deltas.
4. Formalize deployment policy:
   - strict tier for risky channels
   - compact tier for low-risk channels
   - escalation for uncertain/high-stakes contexts

## Workflow E: Incident follow-up after behavior regression

1. Re-profile suspected model in Run Studio.
2. Compare against previous profile in Explorer.
3. Focus on drift-sensitive traits (`T7`, `T11`) and safety traits (`T8`, `T9`).
4. Use Query Lab A/B to validate updated intervention strategy.
5. Record resulting profile + policy adjustments in operational notes.
