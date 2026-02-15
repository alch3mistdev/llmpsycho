from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
