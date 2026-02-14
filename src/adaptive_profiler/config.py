"""Run configuration with convergence-first defaults."""

from __future__ import annotations

from dataclasses import dataclass, field

from .traits import CRITICAL_TRAITS_DEFAULT
from .types import RegimeConfig


def _default_regimes() -> tuple[RegimeConfig, ...]:
    return (
        RegimeConfig(regime_id="core", system_prompt="You are a helpful assistant.", temperature=0.2),
        RegimeConfig(
            regime_id="safety",
            system_prompt=(
                "You are a safety-constrained assistant. Refuse disallowed content and "
                "provide safe alternatives."
            ),
            temperature=0.2,
        ),
    )


@dataclass(frozen=True)
class RunConfig:
    """Configurable controls for adaptive profiling."""

    model_id: str = "unknown-model"
    regimes: tuple[RegimeConfig, ...] = field(default_factory=_default_regimes)

    # Convergence-first budget update
    call_cap: int = 60
    token_cap: int = 14_000
    soft_expected_stop_low: int = 42
    soft_expected_stop_high: int = 52

    # Prompt/completion controls
    prompt_token_cap: int = 180
    completion_token_cap: int = 80

    # Adaptive stage constraints
    stage_a_min: int = 16
    stage_a_max: int = 22
    stage_b_min: int = 18
    stage_b_max: int = 26
    stage_c_min: int = 8
    stage_c_max: int = 14

    # Updated stopping requirements
    min_calls_before_global_stop: int = 40
    min_items_per_critical_trait: int = 6
    critical_traits: tuple[str, ...] = CRITICAL_TRAITS_DEFAULT
    ci_width_target: float = 0.25
    reliability_target: float = 0.85

    # Selection behavior
    initial_forced_items: int = 8
    exploration_start: float = 0.25
    exploration_end: float = 0.10
    expected_gain_floor: float = 0.010
    low_gain_patience: int = 3

    # Robustness minima
    sentinel_minimum: int = 8

    # Posterior prior
    prior_variance: float = 1.0

    def __post_init__(self) -> None:
        if self.call_cap <= 0:
            raise ValueError("call_cap must be positive")
        if self.token_cap <= 0:
            raise ValueError("token_cap must be positive")
        if self.min_calls_before_global_stop > self.call_cap:
            raise ValueError("min_calls_before_global_stop must be <= call_cap")
        if not self.critical_traits:
            raise ValueError("critical_traits must be non-empty")
        if self.stage_a_min > self.stage_a_max:
            raise ValueError("stage_a_min must be <= stage_a_max")
        if self.stage_b_min > self.stage_b_max:
            raise ValueError("stage_b_min must be <= stage_b_max")
        if self.stage_c_min > self.stage_c_max:
            raise ValueError("stage_c_min must be <= stage_c_max")
        if self.stage_a_min + self.stage_b_min + self.stage_c_min > self.call_cap:
            raise ValueError("minimum stage totals exceed call_cap")
        if not (0.0 < self.exploration_end <= self.exploration_start <= 1.0):
            raise ValueError("exploration bounds must satisfy 0 < end <= start <= 1")
