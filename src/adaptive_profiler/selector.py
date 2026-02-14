"""Adaptive item selection policy."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import random

from .config import RunConfig
from .mirt import DiagonalMIRT
from .types import Item, PosteriorState


@dataclass(frozen=True)
class SelectionDecision:
    item: Item
    expected_gain: float
    stage: str


class AdaptiveSelector:
    """Stage-aware utility maximization with epsilon exploration."""

    def __init__(self, config: RunConfig, mirt: DiagonalMIRT, seed: int = 7) -> None:
        self.config = config
        self.mirt = mirt
        self.rng = random.Random(seed)

    def current_stage(self, stage_counts: dict[str, int], critical_counts: Counter[str]) -> str:
        # Stage A: broad coverage
        if stage_counts["A"] < self.config.stage_a_min:
            return "A"
        if (
            stage_counts["A"] < self.config.stage_a_max
            and min(critical_counts[t] for t in self.config.critical_traits) < 2
        ):
            return "A"

        # Stage B: uncertainty-driven refinement
        if stage_counts["B"] < self.config.stage_b_min:
            return "B"
        if (
            stage_counts["B"] < self.config.stage_b_max
            and min(critical_counts[t] for t in self.config.critical_traits)
            < self.config.min_items_per_critical_trait
        ):
            return "B"

        # Stage C: safety + robustness validation
        return "C"

    def _epsilon(self, call_index: int) -> float:
        frac = min(1.0, max(0.0, call_index / max(1, self.config.call_cap - 1)))
        return self.config.exploration_start + frac * (self.config.exploration_end - self.config.exploration_start)

    def _coverage_bonus(self, item: Item, trait_counts: Counter[str]) -> float:
        bonus = 0.0
        for trait, loading in item.trait_loadings.items():
            if trait in self.config.critical_traits:
                deficit = max(0, self.config.min_items_per_critical_trait - trait_counts[trait])
                bonus += loading * 0.035 * deficit
        return bonus

    @staticmethod
    def _novelty_bonus(item: Item) -> float:
        if item.is_sentinel:
            return 0.09
        if item.is_ood or item.paraphrase_group:
            return 0.05
        return 0.0

    def _utility(
        self,
        item: Item,
        posterior: PosteriorState,
        trait_counts: Counter[str],
        stage: str,
        exposure_count: int,
    ) -> tuple[float, float]:
        expected_gain = self.mirt.expected_information_gain(item, posterior)
        coverage = self._coverage_bonus(item, trait_counts)
        novelty = self._novelty_bonus(item)

        if stage == "A":
            weight_info = 0.7
            weight_coverage = 1.5
            weight_novelty = 0.7
        elif stage == "B":
            weight_info = 1.4
            weight_coverage = 1.0
            weight_novelty = 0.8
        else:
            weight_info = 1.0
            weight_coverage = 0.8
            weight_novelty = 1.6

        exposure_penalty = 0.04 * math.sqrt(max(0, exposure_count))
        utility = (
            weight_info * expected_gain
            + weight_coverage * coverage
            + weight_novelty * novelty
            - exposure_penalty
        )
        return utility, expected_gain

    def select_next_item(
        self,
        *,
        items: list[Item],
        posterior: PosteriorState,
        regime_id: str,
        trait_counts: Counter[str],
        used_ids: set[str],
        exposure_counts: Counter[str],
        call_index: int,
        stage: str,
        sentinel_count: int,
    ) -> SelectionDecision | None:
        must_inject_sentinel = ((call_index + 1) % 4 == 0) and (
            sentinel_count < self.config.sentinel_minimum
        )

        pool = [
            item
            for item in items
            if item.item_id not in used_ids and regime_id in item.regime_tags
        ]

        if must_inject_sentinel:
            sentinel_pool = [item for item in pool if item.is_sentinel or item.is_ood or item.paraphrase_group]
            if sentinel_pool:
                pool = sentinel_pool

        if stage == "C" and sentinel_count < self.config.sentinel_minimum:
            stage_c_pool = [item for item in pool if item.is_sentinel or item.is_ood or item.paraphrase_group]
            if stage_c_pool:
                pool = stage_c_pool

        if not pool:
            return None

        scored: list[tuple[float, float, Item]] = []
        for item in pool:
            utility, expected_gain = self._utility(
                item=item,
                posterior=posterior,
                trait_counts=trait_counts,
                stage=stage,
                exposure_count=exposure_counts[item.item_id],
            )
            scored.append((utility, expected_gain, item))

        scored.sort(key=lambda row: row[0], reverse=True)
        epsilon = self._epsilon(call_index)
        top = scored[: max(3, min(8, len(scored)))]

        if self.rng.random() < epsilon:
            selected = self.rng.choice(top)
        else:
            selected = top[0]

        return SelectionDecision(item=selected[2], expected_gain=selected[1], stage=stage)
