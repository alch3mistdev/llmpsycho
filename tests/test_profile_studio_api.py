from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi not installed")
class ProfileStudioApiIntegrationTest(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from profile_studio_api.main import create_app

        app = create_app()
        client = TestClient(app)
        response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "ok")

    def test_meta_glossary_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from profile_studio_api.main import create_app

        app = create_app()
        client = TestClient(app)
        response = client.get("/api/meta/glossary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("metrics", payload)
        self.assertIn("intent_fidelity", payload["metrics"])

    def test_probe_catalog_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from profile_studio_api.main import create_app

        app = create_app()
        client = TestClient(app)
        response = client.get("/api/meta/probe-catalog")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("probe_families", payload)
        self.assertIn("scoring_mechanics", payload)

    def test_probe_trace_endpoint_supports_legacy_records(self) -> None:
        from fastapi.testclient import TestClient

        from profile_studio_api.main import create_app

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            prior_env = {
                "LLMPSYCHO_DATA_DIR": os.environ.get("LLMPSYCHO_DATA_DIR"),
                "LLMPSYCHO_EXPLAINABILITY_V3": os.environ.get("LLMPSYCHO_EXPLAINABILITY_V3"),
            }
            os.environ["LLMPSYCHO_DATA_DIR"] = str(data_dir)
            os.environ["LLMPSYCHO_EXPLAINABILITY_V3"] = "1"
            try:
                app = create_app()
                services = app.state.services
                profile_id = "legacy-profile"
                artifact_path = services.settings.profiles_dir / f"{profile_id}.json"
                payload = {
                    "run_id": profile_id,
                    "model_id": "simulated-local",
                    "regimes": [
                        {
                            "regime_id": "core",
                            "trait_estimates": [
                                {"trait": "T4", "mean": 0.1, "sd": 0.2, "ci95": [-0.1, 0.3], "reliability": 0.8}
                            ],
                        }
                    ],
                    "diagnostics": {
                        "critical_reliability_met": True,
                        "critical_ci_met": True,
                        "critical_coverage_met": True,
                        "sentinel_items_sampled": 8,
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
                    "budget": {"calls_used": 10, "tokens_prompt": 200, "tokens_completion": 100},
                    "stop_reason": "global_uncertainty_threshold_met",
                    "records": [
                        {
                            "call_index": 0,
                            "stage": "A",
                            "regime_id": "core",
                            "item_id": "I08",
                            "family": "intent_clarification",
                            "prompt_tokens": 20,
                            "completion_tokens": 10,
                            "expected_probability": 0.45,
                            "score": 0.5,
                            "score_components": {"single_question": 1.0},
                        }
                    ],
                }
                artifact_path.write_text(json.dumps(payload), encoding="utf-8")
                services.repository.record_profile(
                    profile_id=profile_id,
                    run_id=profile_id,
                    model_id="simulated-local",
                    provider="simulated",
                    source="run",
                    artifact_path=str(artifact_path),
                    checksum="legacy-checksum",
                    payload=payload,
                    metadata={"created_at": "2026-02-15T00:00:00+00:00"},
                )

                client = TestClient(app)
                trace_response = client.get(f"/api/profiles/{profile_id}/probe-trace?limit=10")
                self.assertEqual(trace_response.status_code, 200)
                trace_payload = trace_response.json()
                self.assertEqual(trace_payload.get("total"), 1)
                first = trace_payload["items"][0]
                self.assertIn("prompt_text", first)
                self.assertFalse(first.get("has_full_transcript"))

                profile_response = client.get(f"/api/profiles/{profile_id}")
                self.assertEqual(profile_response.status_code, 200)
                profile_payload = profile_response.json()
                self.assertIn("trace_summary", profile_payload)
                self.assertEqual(profile_payload["trace_summary"]["total_records"], 1)
            finally:
                if prior_env["LLMPSYCHO_DATA_DIR"] is None:
                    os.environ.pop("LLMPSYCHO_DATA_DIR", None)
                else:
                    os.environ["LLMPSYCHO_DATA_DIR"] = prior_env["LLMPSYCHO_DATA_DIR"]
                if prior_env["LLMPSYCHO_EXPLAINABILITY_V3"] is None:
                    os.environ.pop("LLMPSYCHO_EXPLAINABILITY_V3", None)
                else:
                    os.environ["LLMPSYCHO_EXPLAINABILITY_V3"] = prior_env["LLMPSYCHO_EXPLAINABILITY_V3"]


if __name__ == "__main__":
    unittest.main()
