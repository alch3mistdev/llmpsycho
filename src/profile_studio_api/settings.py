"""Runtime settings for the Profile Studio backend."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    workspace_root: Path
    data_dir: Path
    profiles_dir: Path
    ingestion_dir: Path
    quarantine_dir: Path
    db_path: Path
    schema_path: Path
    ingestion_scan_interval_seconds: int = 10

    @classmethod
    def load(cls) -> "AppSettings":
        workspace_root = Path(__file__).resolve().parents[2]
        data_dir = Path(os.environ.get("LLMPSYCHO_DATA_DIR", str(workspace_root / "data"))).resolve()
        profiles_dir = data_dir / "profiles"
        ingestion_dir = data_dir / "ingestion"
        quarantine_dir = data_dir / "quarantine"
        db_path = Path(os.environ.get("LLMPSYCHO_DB_PATH", str(data_dir / "profile_store.sqlite"))).resolve()
        schema_path = Path(
            os.environ.get(
                "LLMPSYCHO_SCHEMA_PATH",
                str(workspace_root / "schemas" / "profile_run.schema.json"),
            )
        ).resolve()
        scan_interval = int(os.environ.get("LLMPSYCHO_INGESTION_SCAN_SECONDS", "10"))
        return cls(
            workspace_root=workspace_root,
            data_dir=data_dir,
            profiles_dir=profiles_dir,
            ingestion_dir=ingestion_dir,
            quarantine_dir=quarantine_dir,
            db_path=db_path,
            schema_path=schema_path,
            ingestion_scan_interval_seconds=max(1, scan_interval),
        )

    def ensure_paths(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.ingestion_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
