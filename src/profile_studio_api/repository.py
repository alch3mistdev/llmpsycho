"""SQLite repository for profile studio state and artifacts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import threading
from typing import Any


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).isoformat()


class ProfileStudioRepository:
    """Persistence and query operations used by the API and workers."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._apply_migrations()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS profiles (
                    profile_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    model_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    converged INTEGER NOT NULL,
                    risk_flags_json TEXT NOT NULL,
                    diagnostics_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_profiles_model_provider ON profiles(model_id, provider);
                CREATE INDEX IF NOT EXISTS idx_profiles_checksum ON profiles(checksum);

                CREATE TABLE IF NOT EXISTS profile_artifacts (
                    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    run_id TEXT,
                    artifact_path TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    source TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error_text TEXT,
                    requested_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);

                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_run_events_run_id_id ON run_events(run_id, id);

                CREATE TABLE IF NOT EXISTS ingestion_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    checksum TEXT,
                    status TEXT NOT NULL,
                    profile_id TEXT,
                    error_text TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS query_lab_sessions (
                    session_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ab_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    baseline_json TEXT NOT NULL,
                    treated_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    diff_json TEXT NOT NULL,
                    intervention_json TEXT NOT NULL,
                    baseline_trace_id TEXT,
                    treated_trace_id TEXT,
                    intervention_trace_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evaluation_traces (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    profile_id TEXT,
                    run_id TEXT,
                    context_json TEXT NOT NULL,
                    alignment_report_json TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_evaluation_traces_session_id ON evaluation_traces(session_id);
                CREATE INDEX IF NOT EXISTS idx_evaluation_traces_profile_id ON evaluation_traces(profile_id);

                CREATE TABLE IF NOT EXISTS intervention_traces (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    profile_id TEXT NOT NULL,
                    regime_id TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    causal_trace_json TEXT NOT NULL,
                    attribution_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_intervention_traces_session_id ON intervention_traces(session_id);
                """
            )

    def _apply_migrations(self) -> None:
        with self._lock, self._connect() as conn:
            # Additive migration for older stage-1 DBs.
            table_info = conn.execute("PRAGMA table_info(ab_results)").fetchall()
            cols = {row["name"] for row in table_info}
            if "baseline_trace_id" not in cols:
                conn.execute("ALTER TABLE ab_results ADD COLUMN baseline_trace_id TEXT")
            if "treated_trace_id" not in cols:
                conn.execute("ALTER TABLE ab_results ADD COLUMN treated_trace_id TEXT")
            if "intervention_trace_id" not in cols:
                conn.execute("ALTER TABLE ab_results ADD COLUMN intervention_trace_id TEXT")

    def create_run(
        self,
        *,
        run_id: str,
        job_id: str,
        model_id: str,
        provider: str,
        requested: dict[str, Any],
    ) -> None:
        now = _utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, job_id, model_id, provider, status, created_at, requested_json, summary_json
                ) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)
                """,
                (run_id, job_id, model_id, provider, now, json.dumps(requested), json.dumps({})),
            )

    def update_run_status(
        self,
        run_id: str,
        *,
        status: str,
        summary: dict[str, Any] | None = None,
        error_text: str | None = None,
        set_started: bool = False,
        set_finished: bool = False,
    ) -> None:
        now = _utc_now()
        summary_json = json.dumps(summary or {})
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT started_at, finished_at FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return
            started_at = now if set_started and not row["started_at"] else row["started_at"]
            finished_at = now if set_finished else row["finished_at"]
            conn.execute(
                """
                UPDATE runs
                SET status = ?, started_at = ?, finished_at = ?, error_text = ?, summary_json = ?
                WHERE run_id = ?
                """,
                (status, started_at, finished_at, error_text, summary_json, run_id),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            return {
                "run_id": row["run_id"],
                "job_id": row["job_id"],
                "model_id": row["model_id"],
                "provider": row["provider"],
                "status": row["status"],
                "created_at": row["created_at"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "error_text": row["error_text"],
                "requested": json.loads(row["requested_json"]),
                "summary": json.loads(row["summary_json"]),
            }

    def append_run_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO run_events (run_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, event_type, json.dumps(payload), _utc_now()),
            )
            return int(cur.lastrowid)

    def list_run_events(self, run_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM run_events WHERE run_id = ? AND id > ? ORDER BY id ASC",
                (run_id, after_id),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def record_profile(
        self,
        *,
        profile_id: str,
        run_id: str | None,
        model_id: str,
        provider: str,
        source: str,
        artifact_path: str,
        checksum: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        created_at = metadata.get("created_at") or _utc_now()
        diagnostics = payload.get("diagnostics", {})
        risk_flags = payload.get("risk_flags", {})
        converged = bool(payload.get("stop_reason") == "global_uncertainty_threshold_met")

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO profiles (
                    profile_id, run_id, model_id, provider, source, created_at,
                    artifact_path, checksum, converged, risk_flags_json, diagnostics_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    run_id,
                    model_id,
                    provider,
                    source,
                    created_at,
                    artifact_path,
                    checksum,
                    1 if converged else 0,
                    json.dumps(risk_flags),
                    json.dumps(diagnostics),
                    json.dumps(metadata),
                ),
            )
            conn.execute(
                """
                INSERT INTO profile_artifacts (
                    profile_id, run_id, artifact_path, provider, source, checksum, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (profile_id, run_id, artifact_path, provider, source, checksum, _utc_now()),
            )

    def get_profile_by_checksum(self, checksum: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE checksum = ? LIMIT 1", (checksum,)).fetchone()
            if row is None:
                return None
            return {
                "profile_id": row["profile_id"],
                "run_id": row["run_id"],
                "model_id": row["model_id"],
                "provider": row["provider"],
                "source": row["source"],
                "created_at": row["created_at"],
                "artifact_path": row["artifact_path"],
                "checksum": row["checksum"],
                "converged": bool(row["converged"]),
                "risk_flags": json.loads(row["risk_flags_json"]),
                "diagnostics": json.loads(row["diagnostics_json"]),
                "metadata": json.loads(row["metadata_json"]),
            }

    def list_profiles(
        self,
        *,
        model_id: str | None = None,
        provider: str | None = None,
        converged: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM profiles WHERE 1=1"
        params: list[Any] = []

        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)
        if provider:
            query += " AND provider = ?"
            params.append(provider)
        if converged is not None:
            query += " AND converged = ?"
            params.append(1 if converged else 0)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(limit, 1000)))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "profile_id": row["profile_id"],
                    "run_id": row["run_id"],
                    "model_id": row["model_id"],
                    "provider": row["provider"],
                    "source": row["source"],
                    "created_at": row["created_at"],
                    "artifact_path": row["artifact_path"],
                    "checksum": row["checksum"],
                    "converged": bool(row["converged"]),
                    "risk_flags": json.loads(row["risk_flags_json"]),
                    "diagnostics": json.loads(row["diagnostics_json"]),
                    "metadata": json.loads(row["metadata_json"]),
                }
            )
        return out

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
        if row is None:
            return None
        return {
            "profile_id": row["profile_id"],
            "run_id": row["run_id"],
            "model_id": row["model_id"],
            "provider": row["provider"],
            "source": row["source"],
            "created_at": row["created_at"],
            "artifact_path": row["artifact_path"],
            "checksum": row["checksum"],
            "converged": bool(row["converged"]),
            "risk_flags": json.loads(row["risk_flags_json"]),
            "diagnostics": json.loads(row["diagnostics_json"]),
            "metadata": json.loads(row["metadata_json"]),
        }

    def find_profile_by_run_id(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE run_id = ? LIMIT 1", (run_id,)).fetchone()
        if row is None:
            return None
        return {
            "profile_id": row["profile_id"],
            "run_id": row["run_id"],
            "model_id": row["model_id"],
            "provider": row["provider"],
            "source": row["source"],
            "created_at": row["created_at"],
            "artifact_path": row["artifact_path"],
            "checksum": row["checksum"],
            "converged": bool(row["converged"]),
            "risk_flags": json.loads(row["risk_flags_json"]),
            "diagnostics": json.loads(row["diagnostics_json"]),
            "metadata": json.loads(row["metadata_json"]),
        }

    def record_ingestion_file(
        self,
        *,
        path: str,
        checksum: str | None,
        status: str,
        profile_id: str | None = None,
        error_text: str | None = None,
    ) -> None:
        now = _utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_files (path, checksum, status, profile_id, error_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    checksum=excluded.checksum,
                    status=excluded.status,
                    profile_id=excluded.profile_id,
                    error_text=excluded.error_text,
                    updated_at=excluded.updated_at
                """,
                (path, checksum, status, profile_id, error_text, now, now),
            )

    def list_ingestion_files(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ingestion_files ORDER BY updated_at DESC LIMIT ?",
                (max(1, min(limit, 1000)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_query_lab_session(
        self,
        *,
        session_id: str,
        profile_id: str,
        model_id: str,
        provider: str,
        query_text: str,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO query_lab_sessions (session_id, profile_id, model_id, provider, query_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, profile_id, model_id, provider, query_text, _utc_now()),
            )

    def save_ab_result(
        self,
        *,
        session_id: str,
        baseline: dict[str, Any],
        treated: dict[str, Any],
        metrics: dict[str, Any],
        diff: dict[str, Any],
        intervention: dict[str, Any],
        baseline_trace_id: str | None = None,
        treated_trace_id: str | None = None,
        intervention_trace_id: str | None = None,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ab_results (
                    session_id, baseline_json, treated_json, metrics_json, diff_json, intervention_json,
                    baseline_trace_id, treated_trace_id, intervention_trace_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    json.dumps(baseline),
                    json.dumps(treated),
                    json.dumps(metrics),
                    json.dumps(diff),
                    json.dumps(intervention),
                    baseline_trace_id,
                    treated_trace_id,
                    intervention_trace_id,
                    _utc_now(),
                ),
            )

    def list_ab_results(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM ab_results WHERE session_id = ? ORDER BY id ASC", (session_id,)).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "baseline": json.loads(row["baseline_json"]),
                    "treated": json.loads(row["treated_json"]),
                    "metrics": json.loads(row["metrics_json"]),
                    "diff": json.loads(row["diff_json"]),
                    "intervention": json.loads(row["intervention_json"]),
                    "baseline_trace_id": row["baseline_trace_id"] if "baseline_trace_id" in row.keys() else None,
                    "treated_trace_id": row["treated_trace_id"] if "treated_trace_id" in row.keys() else None,
                    "intervention_trace_id": (
                        row["intervention_trace_id"] if "intervention_trace_id" in row.keys() else None
                    ),
                    "created_at": row["created_at"],
                }
            )
        return out

    def list_recent_ab_results(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ab_results ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 2000)),),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "baseline": json.loads(row["baseline_json"]),
                    "treated": json.loads(row["treated_json"]),
                    "metrics": json.loads(row["metrics_json"]),
                    "diff": json.loads(row["diff_json"]),
                    "intervention": json.loads(row["intervention_json"]),
                    "baseline_trace_id": row["baseline_trace_id"] if "baseline_trace_id" in row.keys() else None,
                    "treated_trace_id": row["treated_trace_id"] if "treated_trace_id" in row.keys() else None,
                    "intervention_trace_id": (
                        row["intervention_trace_id"] if "intervention_trace_id" in row.keys() else None
                    ),
                    "created_at": row["created_at"],
                }
            )
        return out

    def create_evaluation_trace(
        self,
        *,
        trace_id: str,
        session_id: str | None,
        profile_id: str | None,
        run_id: str | None,
        context: dict[str, Any],
        alignment_report: dict[str, Any],
        trace: dict[str, Any],
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evaluation_traces (
                    trace_id, session_id, profile_id, run_id, context_json, alignment_report_json, trace_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    session_id,
                    profile_id,
                    run_id,
                    json.dumps(context),
                    json.dumps(alignment_report),
                    json.dumps(trace),
                    _utc_now(),
                ),
            )

    def get_evaluation_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM evaluation_traces WHERE trace_id = ?", (trace_id,)).fetchone()
        if row is None:
            return None
        return {
            "trace_id": row["trace_id"],
            "session_id": row["session_id"],
            "profile_id": row["profile_id"],
            "run_id": row["run_id"],
            "context": json.loads(row["context_json"]),
            "alignment_report": json.loads(row["alignment_report_json"]),
            "trace": json.loads(row["trace_json"]),
            "created_at": row["created_at"],
        }

    def create_intervention_trace(
        self,
        *,
        trace_id: str,
        session_id: str | None,
        profile_id: str,
        regime_id: str,
        plan: dict[str, Any],
        causal_trace: dict[str, Any],
        attribution: list[dict[str, Any]],
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO intervention_traces (
                    trace_id, session_id, profile_id, regime_id, plan_json, causal_trace_json, attribution_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    session_id,
                    profile_id,
                    regime_id,
                    json.dumps(plan),
                    json.dumps(causal_trace),
                    json.dumps(attribution),
                    _utc_now(),
                ),
            )

    def get_intervention_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM intervention_traces WHERE trace_id = ?", (trace_id,)).fetchone()
        if row is None:
            return None
        return {
            "trace_id": row["trace_id"],
            "session_id": row["session_id"],
            "profile_id": row["profile_id"],
            "regime_id": row["regime_id"],
            "plan": json.loads(row["plan_json"]),
            "causal_trace": json.loads(row["causal_trace_json"]),
            "attribution": json.loads(row["attribution_json"]),
            "created_at": row["created_at"],
        }
