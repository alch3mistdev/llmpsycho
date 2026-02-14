from __future__ import annotations

import statistics
import unittest

from adaptive_profiler.simulate import run_panel


class AcceptanceTargetsTest(unittest.TestCase):
    def test_convergence_efficiency_and_robustness_targets(self) -> None:
        reports = run_panel(runs=24, seed=1200, benchmark_trained=False)

        convergence = [
            bool(r.diagnostics.get("critical_reliability_met", False))
            and bool(r.diagnostics.get("critical_ci_met", False))
            and r.budget.calls_used <= 60
            for r in reports
        ]
        convergence_rate = sum(1 for ok in convergence if ok) / len(convergence)
        self.assertGreaterEqual(convergence_rate, 0.90)

        median_calls = statistics.median(r.budget.calls_used for r in reports)
        self.assertLessEqual(median_calls, 52)

        sentinel_ok = [int(r.diagnostics.get("sentinel_items_sampled", 0)) >= 8 for r in reports]
        self.assertTrue(all(sentinel_ok))

    def test_benchmark_overfit_detector_has_low_false_positive_rate(self) -> None:
        reports = run_panel(runs=24, seed=2200, benchmark_trained=False)
        false_positive_rate = (
            sum(1 for r in reports if r.risk_flags.get("benchmark_overfit", False)) / len(reports)
        )
        self.assertLessEqual(false_positive_rate, 0.15)


if __name__ == "__main__":
    unittest.main()
