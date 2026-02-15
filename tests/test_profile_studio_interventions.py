from __future__ import annotations

import unittest

from profile_studio_api.interventions import (
    compare_metrics,
    derive_intervention_plan,
    response_metrics,
)


def _profile_with_traits(t4: float, t5: float, t8: float, t9: float, t6: float) -> dict:
    return {
        "risk_flags": {"benchmark_overfit": False},
        "regimes": [
            {
                "regime_id": "core",
                "trait_estimates": [
                    {"trait": "T1", "mean": 0.8},
                    {"trait": "T2", "mean": 0.8},
                    {"trait": "T3", "mean": 0.8},
                    {"trait": "T4", "mean": t4},
                    {"trait": "T5", "mean": t5},
                    {"trait": "T6", "mean": t6},
                    {"trait": "T8", "mean": t8},
                    {"trait": "T9", "mean": t9},
                ],
            }
        ],
    }


class InterventionRulesTest(unittest.TestCase):
    def test_strict_tier_for_low_refusal_and_jailbreak(self) -> None:
        payload = _profile_with_traits(t4=0.1, t5=0.2, t8=-0.5, t9=-0.4, t6=0.3)
        plan = derive_intervention_plan(payload, regime_id="core")
        self.assertEqual(plan.tier, "L3")
        self.assertIn("low_refusal_or_jailbreak", plan.rules_applied)

    def test_metrics_and_diff_shape(self) -> None:
        baseline = response_metrics("How to reset password?", "Use account settings.", 50, 20, 120)
        treated = response_metrics(
            "How to reset password?",
            "Go to settings, then security, then reset password.",
            60,
            18,
            100,
        )
        diff = compare_metrics(baseline, treated)
        self.assertIn("token_delta", diff)
        self.assertIn("intent_delta", diff)
        self.assertIn("safety_delta", diff)


if __name__ == "__main__":
    unittest.main()
