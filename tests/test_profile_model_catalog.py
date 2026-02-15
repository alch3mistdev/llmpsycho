from __future__ import annotations

import os
import unittest

from profile_studio_api.model_catalog import ProviderModelCatalog


class ProviderModelCatalogTest(unittest.TestCase):
    def test_fallback_models_when_api_keys_missing(self) -> None:
        openai_prev = os.environ.pop("OPENAI_API_KEY", None)
        anthropic_prev = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            catalog = ProviderModelCatalog(refresh_ttl_seconds=60)
            snapshot = catalog.refresh(force=True)

            providers = {(m.get("provider"), m.get("model_id")) for m in snapshot.models}
            self.assertIn(("simulated", "simulated-local"), providers)
            self.assertIn(("openai", "gpt-4o"), providers)
            self.assertIn(("anthropic", "claude-3-5-sonnet-20241022"), providers)
            self.assertIn("openai", snapshot.errors)
            self.assertIn("anthropic", snapshot.errors)
        finally:
            if openai_prev is not None:
                os.environ["OPENAI_API_KEY"] = openai_prev
            if anthropic_prev is not None:
                os.environ["ANTHROPIC_API_KEY"] = anthropic_prev


if __name__ == "__main__":
    unittest.main()
