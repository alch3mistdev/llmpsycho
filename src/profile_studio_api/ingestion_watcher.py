"""Folder watcher and import pipeline for profile JSON ingestion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import threading
import time
from typing import Any
import uuid

from .repository import ProfileStudioRepository
from .settings import AppSettings
from .validation import validate_profile_payload


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class IngestionWatcher:
    """Background scanner for profile artifacts dropped in ingestion folder."""

    def __init__(self, settings: AppSettings, repository: ProfileStudioRepository) -> None:
        self.settings = settings
        self.repository = repository
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last_scan_at: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="ingestion-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.scan_once()
            except Exception:
                # Keep watcher alive; errors are visible in ingestion log rows.
                pass
            self._stop.wait(self.settings.ingestion_scan_interval_seconds)

    def status(self) -> dict[str, Any]:
        recent = self.repository.list_ingestion_files(limit=25)
        imported_count = sum(1 for row in recent if row.get("status") == "imported")
        error_count = sum(1 for row in recent if row.get("status") == "error")
        return {
            "running": self._thread.is_alive() if self._thread else False,
            "last_scan_at": self._last_scan_at,
            "imported_count": imported_count,
            "error_count": error_count,
            "recent": recent,
        }

    def scan_once(self) -> list[dict[str, Any]]:
        imported: list[dict[str, Any]] = []
        files = sorted(self.settings.ingestion_dir.glob("*.json"))
        for path in files:
            result = self.import_file(path, source="ingestion")
            imported.append(result)
        with self._lock:
            self._last_scan_at = _utc_now()
        return imported

    def import_upload_bytes(self, filename: str, data: bytes) -> dict[str, Any]:
        temp_path = self.settings.ingestion_dir / f"upload-{uuid.uuid4()}-{filename}"
        temp_path.write_bytes(data)
        try:
            return self.import_file(temp_path, source="upload")
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def import_file(self, path: Path, *, source: str) -> dict[str, Any]:
        try:
            raw = path.read_bytes()
            checksum = _sha256(raw)
            existing = self.repository.get_profile_by_checksum(checksum)
            if existing:
                self.repository.record_ingestion_file(
                    path=str(path),
                    checksum=checksum,
                    status="duplicate",
                    profile_id=existing["profile_id"],
                )
                return {
                    "status": "duplicate",
                    "profile_id": existing["profile_id"],
                    "path": str(path),
                    "checksum": checksum,
                }

            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("JSON root must be an object")

            metadata: dict[str, Any]
            profile_payload: dict[str, Any]

            if "profile" in parsed and isinstance(parsed["profile"], dict):
                profile_payload = parsed["profile"]
                metadata = dict(parsed.get("metadata") or {})
            else:
                profile_payload = parsed
                metadata = {}

            profile_id = str(metadata.get("profile_id") or profile_payload.get("run_id") or uuid.uuid4())
            run_id = profile_payload.get("run_id")
            existing_by_id = self.repository.get_profile(profile_id)
            existing_by_run = (
                self.repository.find_profile_by_run_id(str(run_id))
                if isinstance(run_id, str) and run_id
                else None
            )
            if existing_by_id or existing_by_run:
                duplicate = existing_by_id or existing_by_run
                self.repository.record_ingestion_file(
                    path=str(path),
                    checksum=duplicate["checksum"],
                    status="duplicate",
                    profile_id=duplicate["profile_id"],
                )
                return {
                    "status": "duplicate",
                    "profile_id": duplicate["profile_id"],
                    "path": str(path),
                    "checksum": duplicate["checksum"],
                }

            valid, errors = validate_profile_payload(profile_payload, self.settings.schema_path)
            if not valid:
                raise ValueError("; ".join(errors))

            model_id = str(metadata.get("model_id") or profile_payload.get("model_id") or "unknown-model")
            provider = str(metadata.get("provider") or "unknown")

            canonical_metadata = {
                "profile_id": profile_id,
                "run_id": profile_payload.get("run_id"),
                "model_id": model_id,
                "provider": provider,
                "source": source,
                "created_at": metadata.get("created_at") or _utc_now(),
                "ingested_from": str(path),
                "version": int(metadata.get("version", 1)),
            }
            envelope = {
                "metadata": canonical_metadata,
                "profile": profile_payload,
            }
            artifact_bytes = json.dumps(envelope, indent=2, sort_keys=True).encode("utf-8")
            artifact_path = self.settings.profiles_dir / f"{profile_id}.json"
            artifact_path.write_bytes(artifact_bytes)
            artifact_checksum = _sha256(artifact_bytes)

            self.repository.record_profile(
                profile_id=profile_id,
                run_id=canonical_metadata.get("run_id"),
                model_id=model_id,
                provider=provider,
                source=source,
                artifact_path=str(artifact_path),
                checksum=artifact_checksum,
                payload=profile_payload,
                metadata=canonical_metadata,
            )
            self.repository.record_ingestion_file(
                path=str(path),
                checksum=artifact_checksum,
                status="imported",
                profile_id=profile_id,
            )
            return {
                "status": "imported",
                "profile_id": profile_id,
                "path": str(path),
                "artifact_path": str(artifact_path),
                "checksum": artifact_checksum,
            }
        except Exception as exc:
            quarantine_path = self.settings.quarantine_dir / path.name
            if path.exists() and source == "ingestion":
                shutil.copy2(path, quarantine_path)
            self.repository.record_ingestion_file(
                path=str(path),
                checksum=None,
                status="error",
                error_text=str(exc),
            )
            return {
                "status": "error",
                "path": str(path),
                "error": str(exc),
            }
