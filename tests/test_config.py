from __future__ import annotations

import unittest

from adaptive_profiler.config import RunConfig


class RunConfigDefaultsTest(unittest.TestCase):
    def test_convergence_first_defaults(self) -> None:
        cfg = RunConfig()
        self.assertEqual(cfg.call_cap, 60)
        self.assertEqual(cfg.token_cap, 14000)
        self.assertEqual(cfg.min_calls_before_global_stop, 40)
        self.assertEqual(cfg.min_items_per_critical_trait, 6)
        self.assertEqual(cfg.critical_traits, ("T4", "T5", "T8", "T9", "T10"))
        self.assertEqual((cfg.stage_a_min, cfg.stage_a_max), (16, 22))
        self.assertEqual((cfg.stage_b_min, cfg.stage_b_max), (18, 26))
        self.assertEqual((cfg.stage_c_min, cfg.stage_c_max), (8, 14))
        self.assertEqual(cfg.ci_width_target, 0.25)
        self.assertEqual(cfg.reliability_target, 0.85)


if __name__ == "__main__":
    unittest.main()
