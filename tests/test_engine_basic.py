from __future__ import annotations

import unittest

from adaptive_profiler.config import RunConfig
from adaptive_profiler.engine import AdaptiveProfilerEngine
from adaptive_profiler.item_bank import build_item_bank
from adaptive_profiler.simulate import SimulatedModelAdapter, sample_true_thetas


class EngineBasicBehaviorTest(unittest.TestCase):
    def test_run_respects_caps_and_stopping_guards(self) -> None:
        cfg = RunConfig(model_id="basic-test")
        bank = build_item_bank(seed=17)
        engine = AdaptiveProfilerEngine(config=cfg, item_bank=bank, seed=77)
        adapter = SimulatedModelAdapter(true_theta_by_regime=sample_true_thetas(seed=88), seed=89)

        report = engine.run(adapter, run_id="basic-run")

        self.assertLessEqual(report.budget.calls_used, cfg.call_cap)
        self.assertLessEqual(report.budget.prompt_tokens + report.budget.completion_tokens, cfg.token_cap)
        self.assertGreaterEqual(report.budget.calls_used, cfg.min_calls_before_global_stop)
        self.assertGreaterEqual(int(report.diagnostics["sentinel_items_sampled"]), cfg.sentinel_minimum)
        self.assertGreaterEqual(int(report.diagnostics["calls_in_stage_a"]), cfg.stage_a_min)
        self.assertGreaterEqual(int(report.diagnostics["calls_in_stage_b"]), cfg.stage_b_min)
        self.assertGreaterEqual(int(report.diagnostics["calls_in_stage_c"]), cfg.stage_c_min)


if __name__ == "__main__":
    unittest.main()
