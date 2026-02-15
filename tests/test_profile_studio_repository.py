from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from profile_studio_api.repository import ProfileStudioRepository


def _sample_profile_payload() -> dict:
    return {
        "run_id": "run-1",
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


class ProfileStudioRepositoryTest(unittest.TestCase):
    def test_profile_and_run_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "store.sqlite"
            repo = ProfileStudioRepository(db_path)

            repo.create_run(
                run_id="run-1",
                job_id="job-1",
                model_id="simulated-local",
                provider="simulated",
                requested={"provider": "simulated"},
            )
            repo.append_run_event("run-1", "progress", {"call_index": 1})
            repo.update_run_status(
                "run-1",
                status="completed",
                summary={"calls_used": 42},
                set_started=True,
                set_finished=True,
            )

            run = repo.get_run("run-1")
            self.assertIsNotNone(run)
            assert run is not None
            self.assertEqual(run["status"], "completed")
            self.assertEqual(run["summary"].get("calls_used"), 42)

            artifact = tmp_path / "profile.json"
            payload = _sample_profile_payload()
            artifact.write_text(json.dumps(payload), encoding="utf-8")

            repo.record_profile(
                profile_id="profile-1",
                run_id="run-1",
                model_id="simulated-local",
                provider="simulated",
                source="run",
                artifact_path=str(artifact),
                checksum="abc123",
                payload=payload,
                metadata={"created_at": "2026-01-01T00:00:00+00:00"},
            )

            profiles = repo.list_profiles(limit=10)
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0]["profile_id"], "profile-1")
            self.assertTrue(profiles[0]["converged"])

            single = repo.get_profile("profile-1")
            self.assertIsNotNone(single)
            assert single is not None
            self.assertEqual(single["checksum"], "abc123")

            events = repo.list_run_events("run-1")
            self.assertGreaterEqual(len(events), 1)
            self.assertEqual(events[0]["event_type"], "progress")


if __name__ == "__main__":
    unittest.main()
