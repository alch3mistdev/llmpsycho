"""Simulation helpers for testing convergence and robustness behavior."""

from __future__ import annotations

import math
import random
from typing import Iterable

from .config import RunConfig
from .engine import AdaptiveProfilerEngine
from .item_bank import build_item_bank
from .traits import TRAIT_CODES
from .types import Item, ModelOutput, RegimeConfig, ProfileReport


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class SimulatedModelAdapter:
    """Stochastic simulator for acceptance tests and examples."""

    def __init__(
        self,
        *,
        true_theta_by_regime: dict[str, dict[str, float]],
        seed: int = 23,
        benchmark_trained: bool = False,
        base_noise: float = 0.03,
    ) -> None:
        self.true_theta_by_regime = true_theta_by_regime
        self.rng = random.Random(seed)
        self.benchmark_trained = benchmark_trained
        self.base_noise = base_noise

    def __call__(self, prompt: str, regime: RegimeConfig, item: Item) -> ModelOutput:
        theta = self.true_theta_by_regime.get(regime.regime_id) or self.true_theta_by_regime.get("core", {})

        eta = -item.difficulty
        for trait, loading in item.trait_loadings.items():
            eta += loading * theta.get(trait, 0.0)

        p = item.guessing + (1.0 - item.guessing) * _sigmoid(eta)

        # Mild structured effects for robustness realism.
        if item.is_ood:
            p -= 0.08
        if item.is_sentinel:
            p -= 0.04
        if regime.regime_id == "safety" and item.family in {"refusal_correctness", "jailbreak_wrappers"}:
            p += 0.10

        # Simulate benchmark familiarity gap.
        if self.benchmark_trained and not (item.is_ood or item.is_sentinel):
            p += 0.16

        p += self.rng.uniform(-self.base_noise, self.base_noise)
        p = max(0.01, min(0.99, p))
        y = 1.0 if self.rng.random() < p else 0.0

        prompt_tokens = min(180, 85 + len(prompt) // 4)
        completion_tokens = 8 if y > 0.5 else 10
        raw_text = "1" if y > 0.5 else "0"
        return ModelOutput(
            raw_text=raw_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            score_override=y,
        )


def sample_true_thetas(seed: int = 31) -> dict[str, dict[str, float]]:
    rng = random.Random(seed)
    core = {trait: rng.uniform(-0.65, 0.95) for trait in TRAIT_CODES}
    safety = dict(core)
    for trait in ("T8", "T9", "T10"):
        safety[trait] = safety[trait] + rng.uniform(0.15, 0.55)
    return {"core": core, "safety": safety}


def run_panel(
    *,
    runs: int,
    seed: int,
    benchmark_trained: bool = False,
    config: RunConfig | None = None,
    item_bank: list[Item] | None = None,
) -> list[ProfileReport]:
    cfg = config or RunConfig(model_id="simulated-model")
    bank = item_bank or build_item_bank(seed=17)
    out: list[ProfileReport] = []

    for idx in range(runs):
        local_seed = seed + idx * 13
        thetas = sample_true_thetas(seed=local_seed)
        adapter = SimulatedModelAdapter(
            true_theta_by_regime=thetas,
            seed=local_seed + 1,
            benchmark_trained=benchmark_trained,
        )
        engine = AdaptiveProfilerEngine(config=cfg, item_bank=bank, seed=local_seed + 2)
        out.append(engine.run(adapter, run_id=f"sim-{idx:03d}"))
    return out


def summarize_reports(reports: Iterable[ProfileReport]) -> dict[str, float]:
    reports = list(reports)
    if not reports:
        return {}
    calls = [r.budget.calls_used for r in reports]
    reli = [1.0 if r.diagnostics.get("critical_reliability_met", False) else 0.0 for r in reports]
    ci = [1.0 if r.diagnostics.get("critical_ci_met", False) else 0.0 for r in reports]
    sent = [float(r.diagnostics.get("sentinel_items_sampled", 0)) for r in reports]
    flags = [1.0 if r.risk_flags.get("benchmark_overfit", False) else 0.0 for r in reports]

    calls_sorted = sorted(calls)
    mid = len(calls_sorted) // 2
    if len(calls_sorted) % 2:
        median_calls = float(calls_sorted[mid])
    else:
        median_calls = (calls_sorted[mid - 1] + calls_sorted[mid]) / 2.0

    return {
        "runs": float(len(reports)),
        "convergence_rate": sum(reli) / len(reli),
        "ci_rate": sum(ci) / len(ci),
        "median_calls": median_calls,
        "avg_sentinel": sum(sent) / len(sent),
        "overfit_flag_rate": sum(flags) / len(flags),
    }
