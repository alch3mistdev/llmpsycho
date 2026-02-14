"""Example adaptive profiling run with simulated model outputs."""

from __future__ import annotations

import json

from adaptive_profiler.config import RunConfig
from adaptive_profiler.engine import AdaptiveProfilerEngine
from adaptive_profiler.item_bank import build_item_bank
from adaptive_profiler.simulate import SimulatedModelAdapter, sample_true_thetas


def main() -> None:
    config = RunConfig(model_id="hypothetical-llm")
    item_bank = build_item_bank(seed=17)
    thetas = sample_true_thetas(seed=91)

    adapter = SimulatedModelAdapter(
        true_theta_by_regime=thetas,
        seed=92,
        benchmark_trained=False,
    )

    engine = AdaptiveProfilerEngine(config=config, item_bank=item_bank, seed=93)
    report = engine.run(adapter, run_id="hypothetical-run")

    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
