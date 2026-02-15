# llmpsycho

Adaptive psychometric profiling for LLMs, plus a local **Profile Studio** for creating, ingesting, exploring, and applying profiles with A/B intervention testing.

## Stage 2 Focus

Stage 2 prioritizes:

- **Intent-result alignment accuracy** via hybrid evaluation (deterministic checks + evaluator model rubric).
- **Explainability** via progressive disclosure (`Simple`, `Guided`, `Technical`) and full trace persistence.
- **Causal intervention transparency** linking profile traits/risk flags to rule triggers, transformations, and observed A/B deltas.

## What This Project Does

`llmpsycho` helps you measure an LLM as a latent trait profile (capability + alignment behavior), then operationalize that profile in an interactive UX.

Core outcomes:

- Estimate a 12-trait vector under adaptive probing with convergence-focused stopping.
- Persist and compare profiles across runs, regimes, and imported artifacts.
- Apply rule-based profile interventions to real queries.
- Run same-model A/B (`profile off` vs `profile on`) to measure safety/intent/cost tradeoffs.

## Project Components

### 1) Profiling Engine (`src/adaptive_profiler`)

- Multidimensional 2PL-style online updater.
- Adaptive item selection + uncertainty-driven stopping.
- Two-regime operation (`core`, `safety`).
- Robustness diagnostics (OOD/paraphrase/drift/overfit signals).

Default convergence-focused settings:

- `call_cap=60`
- `token_cap=14000`
- `min_calls_before_global_stop=40`
- `min_items_per_critical_trait=6`
- critical traits: `T4,T5,T8,T9,T10`

### 2) Backend API (`src/profile_studio_api`)

- FastAPI app with SQLite repository + JSON artifact store.
- Async run jobs with live SSE stream for Run Studio telemetry.
- Profile ingestion (watch folder + upload import) with schema validation and dedupe.
- Query Lab endpoints for apply-only and same-model A/B.
- Hybrid alignment scoring with confidence bands.
- Persisted evaluation traces + intervention causal traces for auditability.
- Model catalog loaded from live provider model endpoints on API startup (with fallback presets if unavailable).

### 3) Frontend UX (`web`)

React + TypeScript + Vite app with:

- **Dashboard**: health/risk/history snapshots.
- **Run Studio**: launch runs, watch stage timeline + budget burn + event feed.
- **Profile Explorer**: progressive-disclosure explainability (`Snapshot`, `Relationships`, `Derivation`, `Evidence`), regime deltas, trait-driver map.
- **Ingestion Center**: watch-folder status, scan, upload, error visibility.
- **Query Lab**: causal A/B pipeline, intent alignment score, rubric breakdown, counterfactual rule toggles, and trace drilldown.

## Repository Layout

```text
src/adaptive_profiler/        # profiling engine
src/profile_studio_api/       # FastAPI backend
web/                          # React frontend
schemas/profile_run.schema.json
docs/                          # product + interpretation + operations docs
data/                          # sqlite + artifacts + ingestion folders
examples/                      # runnable examples
tests/                         # unit/integration tests
```

## Requirements

- Python `>=3.11`
- Node.js `>=18` (for frontend)

## Installation

### Python package (editable)

```bash
pip install -e .
```

Optional extras:

```bash
# Studio backend deps (FastAPI, uvicorn, multipart, jsonschema)
pip install -e ".[studio]"

# Provider SDKs
pip install -e ".[openai]"
pip install -e ".[anthropic]"

# Everything
pip install -e ".[all]"
```

Provider keys (for real model calls):

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Quick Start

### A) Engine only (simulated)

```bash
PYTHONPATH=src python3 examples/hypothetical_run.py
```

### B) Full local product (API + UI)

1. Start API:

```bash
pip install -e ".[studio]"
uvicorn profile_studio_api.main:app --reload
```

API base: `http://localhost:8000`

2. Start frontend:

```bash
cd web
npm install
npm run dev
```

UI: `http://localhost:5173`

Frontend can target another API host with:

```bash
VITE_API_BASE=http://localhost:8000 npm run dev
```

## Data and Persistence

Created/used by backend startup:

- `data/profile_store.sqlite` (index/history/events)
- `data/profiles/*.json` (canonical artifacts)
- `data/ingestion/` (watched import folder)
- `data/quarantine/` (invalid ingestion payload snapshots)

## API Overview

- `GET /api/health`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events` (SSE)
- `GET /api/profiles`
- `GET /api/profiles/{profile_id}`
- `POST /api/profiles/import`
- `POST /api/ingestion/scan`
- `GET /api/ingestion/status`
- `POST /api/query-lab/ab`
- `POST /api/query-lab/apply`
- `POST /api/query-lab/evaluate`
- `GET /api/query-lab/traces/{trace_id}`
- `GET /api/query-lab/analytics`
- `GET /api/meta/models`
- `GET /api/meta/glossary`

## Model Catalog Behavior

On API startup, `/api/meta/models` is populated by querying provider model endpoints when keys/SDKs are available.

- OpenAI: `models.list()`
- Anthropic: `models.list()` (if supported by installed SDK)

If live fetch fails (missing key, SDK issue, endpoint error), fallback presets are returned with error metadata.

## Testing

Run backend/engine tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Note: API integration tests requiring FastAPI are skipped if `fastapi` is not installed.

## Documentation

- `docs/profile_studio_overview.md`
- `docs/profile_interpretation_guide.md`
- `docs/query_lab_ab_guide.md`
- `docs/use_cases_routing_and_alignment.md`
- `docs/operations_ingestion_and_history.md`
- `docs/examples_end_to_end_workflows.md`
- `docs/convergence_first_budget_update.md`
- `docs/stage2_explainable_alignment_ux.md`

## Typical Workflows

1. Create a new profile in Run Studio and watch convergence live.
2. Explore the resulting profile in Profile Explorer.
3. Import external profiles via ingestion folder/upload.
4. Use Query Lab to compare baseline vs profile-applied behavior.
5. Use measured deltas to tune routing/intervention policy.
