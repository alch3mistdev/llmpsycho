# Profile Studio Overview

## Purpose

Profile Studio turns the psychometric engine into an operational product for three workflows:

1. Create fresh profiles for a target model/provider with live adaptive-run telemetry.
2. Explore historical or imported profiles to understand capability/alignment tradeoffs.
3. Apply profile-informed intervention policies to real queries and measure A/B impact.

## Product surfaces

- **Dashboard**: profile inventory, convergence health, risk distribution, ingestion watcher status.
- **Run Studio**: launch profiling jobs, stream per-call progress, inspect stage transitions and token burn.
- **Profile Explorer**: filter/search history, inspect regime-specific trait estimates, confidence, diagnostics, and risk flags.
- **Ingestion Center**: watch-folder sync, manual scan, upload JSON imports, error/quarantine feedback.
- **Query Lab**: run same-model A/B (`off` vs `on` intervention), review response + metric deltas.

## Runtime model

- Local single-user setup.
- FastAPI backend on `localhost:8000`.
- React frontend on `localhost:5173`.
- SQLite-backed index plus JSON profile artifacts on disk.

## End-to-end data flow

1. User starts a run from Run Studio.
2. Backend creates a run job, streams events via SSE, and stores events in SQLite.
3. Engine completes and writes canonical profile artifact (`data/profiles/<profile_id>.json`).
4. SQLite profile index row points to artifact path and caches searchable metadata.
5. UI uses list/detail APIs for history and drilldown.
6. Query Lab loads selected profile, derives deterministic intervention plan, and executes A/B.

## Intervention objective

Default objective is:

1. Safety and intent fidelity first.
2. Token and latency efficiency second.

This objective is encoded in the rule-based intervention tiers (`L0`..`L3`) in `src/profile_studio_api/interventions.py`.
