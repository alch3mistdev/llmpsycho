from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from profile_studio_api.ingestion_watcher import IngestionWatcher
from profile_studio_api.repository import ProfileStudioRepository
from profile_studio_api.settings import AppSettings


def _valid_profile_payload(run_id: str = "ing-run") -> dict:
    return {
        "run_id": run_id,
        "model_id": "simulated-local",
        "regimes": [
            {
                "regime_id": "core",
                "trait_estimates": [
                    {"trait": "T4", "mean": 0.3, "sd": 0.1, "ci95": [0.1, 0.5], "reliability": 0.9}
                ],
            }
        ],
        "diagnostics": {
            "critical_reliability_met": True,
            "critical_ci_met": True,
            "critical_coverage_met": True,
            "sentinel_items_sampled": 9,
            "bti": 0.2,
            "ood_gap": 0.1,
            "paraphrase_consistency": 0.9,
        },
        "risk_flags": {
            "benchmark_overfit": False,
            "instability": False,
            "calibration_risk": False,
            "refusal_risk": False,
        },
        "budget": {"calls_used": 42, "tokens_prompt": 4000, "tokens_completion": 1200},
        "stop_reason": "global_uncertainty_threshold_met",
    }


class IngestionWatcherTest(unittest.TestCase):
    def test_import_and_dedupe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            profiles_dir = data_dir / "profiles"
            ingestion_dir = data_dir / "ingestion"
            quarantine_dir = data_dir / "quarantine"
            for p in (profiles_dir, ingestion_dir, quarantine_dir):
                p.mkdir(parents=True, exist_ok=True)

            db_path = data_dir / "store.sqlite"
            schema_path = Path("/Users/alch3mist/openclaw/projects/llmpsycho/schemas/profile_run.schema.json")
            settings = AppSettings(
                workspace_root=root,
                data_dir=data_dir,
                profiles_dir=profiles_dir,
                ingestion_dir=ingestion_dir,
                quarantine_dir=quarantine_dir,
                db_path=db_path,
                schema_path=schema_path,
                ingestion_scan_interval_seconds=10,
            )

            repo = ProfileStudioRepository(db_path)
            watcher = IngestionWatcher(settings=settings, repository=repo)

            payload = _valid_profile_payload()
            path = ingestion_dir / "p1.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            result1 = watcher.import_file(path, source="ingestion")
            self.assertEqual(result1["status"], "imported")
            self.assertTrue((profiles_dir / f"{payload['run_id']}.json").exists())

            result2 = watcher.import_file(path, source="ingestion")
            self.assertEqual(result2["status"], "duplicate")

            status = watcher.status()
            self.assertIn("recent", status)
            self.assertGreaterEqual(len(status["recent"]), 1)


if __name__ == "__main__":
    unittest.main()
