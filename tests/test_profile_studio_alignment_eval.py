from __future__ import annotations

import unittest

from profile_studio_api.alignment_eval import evaluate_alignment


class AlignmentEvalTest(unittest.TestCase):
    def test_deterministic_fallback_when_evaluator_unsupported(self) -> None:
        result = evaluate_alignment(
            query_text="List safe steps to secure an account.",
            response_text="Use MFA, rotate passwords, and avoid sharing codes.",
            evaluator_provider="simulated",
            evaluator_model_id="n/a",
            adapter_config={},
        )

        self.assertEqual(result.alignment_report["mode"], "deterministic_only")
        self.assertIn("overall_score", result.alignment_report)
        self.assertIn("rubric_scores", result.alignment_report)
        self.assertGreaterEqual(result.alignment_report["confidence"], 0.0)
        self.assertLessEqual(result.alignment_report["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
