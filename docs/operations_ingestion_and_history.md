# Operations: Ingestion and History

## Storage layout

- SQLite index: `data/profile_store.sqlite`
- Canonical artifacts: `data/profiles/*.json`
- Ingestion watch folder: `data/ingestion/`
- Quarantine (invalid payload snapshots): `data/quarantine/`

## Ingestion modes

1. Watch-folder ingest (automatic):
- Drop JSON files into `data/ingestion/`.
- Watcher scans every 10 seconds.
- Valid payloads import into canonical profile store.

2. Manual upload ingest:
- Use `POST /api/profiles/import` from UI upload flow.
- Payload is validated and canonicalized the same way.

## Validation and dedupe

- Profile payloads are validated against `schemas/profile_run.schema.json`.
- Deduplication uses artifact checksum.
- Duplicate payloads are indexed as `duplicate` in ingestion logs.

## Troubleshooting ingestion failures

Common causes:

1. Missing required top-level fields (`run_id`, `diagnostics`, etc.).
2. Non-object JSON root.
3. Invalid field types (e.g., numeric fields provided as strings).

Operational response:

- Check Ingestion Center error row details.
- Review quarantined file copy in `data/quarantine/`.
- Correct payload and re-import.

## History behavior

- History lists and filters are served from SQLite for fast UX.
- Profile detail view loads canonical JSON artifact referenced by `artifact_path`.
- Artifact+index can be backed up by copying both `data/profile_store.sqlite` and `data/profiles/`.

## Run lifecycle statuses

- `queued`
- `running`
- `completed`
- `failed`

SSE stream endpoint (`/api/runs/{run_id}/events`) exposes progress events for live dashboards.
