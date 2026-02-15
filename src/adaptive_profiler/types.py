"""Core datatypes for the adaptive profiling engine."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from .traits import TRAIT_CODES


@dataclass(frozen=True)
class RegimeConfig:
    """Runtime context for profiling under a specific prompt/tool regime."""

    regime_id: str
    system_prompt: str = ""
    temperature: float = 0.2
    tools_enabled: bool = False


@dataclass(frozen=True)
class Item:
    """Probe item metadata and scoring configuration."""

    item_id: str
    family: str
    prompt: str
    scoring_type: str
    trait_loadings: dict[str, float]
    difficulty: float = 0.0
    guessing: float = 0.0
    regime_tags: tuple[str, ...] = ("core", "safety")
    paraphrase_group: str | None = None
    is_ood: bool = False
    is_sentinel: bool = False
    expected_class: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelOutput:
    """Single model completion result used by the adaptive engine."""

    raw_text: str
    prompt_tokens: int
    completion_tokens: int
    score_override: float | None = None


@dataclass
class ResponseRecord:
    """Execution trace for one administered item."""

    run_id: str
    call_index: int
    stage: str
    regime_id: str
    item_id: str
    family: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    expected_probability: float
    score: float
    score_components: dict[str, float]
    prompt_text: str | None = None
    response_text: str | None = None
    scoring_type: str | None = None
    trait_loadings: dict[str, float] | None = None
    item_metadata: dict[str, Any] | None = None
    posterior_before: dict[str, Any] | None = None
    posterior_after: dict[str, Any] | None = None
    selection_context: dict[str, Any] | None = None


@dataclass
class PosteriorState:
    """Diagonal Gaussian approximation for trait posterior."""

    mean: dict[str, float]
    variance: dict[str, float]
    prior_variance: float = 1.0

    @classmethod
    def prior(cls, prior_variance: float = 1.0) -> "PosteriorState":
        return cls(
            mean={trait: 0.0 for trait in TRAIT_CODES},
            variance={trait: prior_variance for trait in TRAIT_CODES},
            prior_variance=prior_variance,
        )

    def copy(self) -> "PosteriorState":
        return PosteriorState(
            mean=dict(self.mean),
            variance=dict(self.variance),
            prior_variance=self.prior_variance,
        )

    def inflate_variance(self, factor: float) -> "PosteriorState":
        out = self.copy()
        for trait in TRAIT_CODES:
            out.variance[trait] *= factor
        return out

    def reliability(self, trait: str) -> float:
        ratio = self.variance[trait] / max(self.prior_variance, 1e-9)
        rel = 1.0 - ratio
        return max(0.0, min(1.0, rel))

    def ci95_width(self, trait: str) -> float:
        # Report CI width on a bounded probability scale for stable cross-trait
        # comparisons and practical stop thresholds.
        sd = math.sqrt(max(self.variance[trait], 1e-9))
        mean = self.mean[trait]
        lo = 1.0 / (1.0 + math.exp(-(mean - 1.96 * sd)))
        hi = 1.0 / (1.0 + math.exp(-(mean + 1.96 * sd)))
        return hi - lo


@dataclass
class TraitEstimate:
    """Final estimate for one trait under one regime."""

    trait: str
    mean: float
    sd: float
    ci95: tuple[float, float]
    reliability: float


@dataclass
class RegimeReport:
    """Final report section for one regime."""

    regime_id: str
    traits: list[TraitEstimate]


@dataclass
class BudgetStats:
    """Budget usage for one profile run."""

    calls_used: int
    prompt_tokens: int
    completion_tokens: int


@dataclass
class ProfileReport:
    """Top-level profile output."""

    run_id: str
    model_id: str
    regimes: list[RegimeReport]
    diagnostics: dict[str, float | int | bool]
    risk_flags: dict[str, bool]
    budget: BudgetStats
    stop_reason: str
    records: list[ResponseRecord]

    def to_dict(self) -> dict[str, Any]:
        record_rows: list[dict[str, Any]] = []
        for r in self.records:
            row: dict[str, Any] = {
                "call_index": r.call_index,
                "stage": r.stage,
                "regime_id": r.regime_id,
                "item_id": r.item_id,
                "family": r.family,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "expected_probability": r.expected_probability,
                "score": r.score,
                "score_components": r.score_components,
            }
            if r.prompt_text is not None:
                row["prompt_text"] = r.prompt_text
            if r.response_text is not None:
                row["response_text"] = r.response_text
            if r.scoring_type is not None:
                row["scoring_type"] = r.scoring_type
            if r.trait_loadings is not None:
                row["trait_loadings"] = r.trait_loadings
            if r.item_metadata is not None:
                row["item_metadata"] = r.item_metadata
            if r.posterior_before is not None:
                row["posterior_before"] = r.posterior_before
            if r.posterior_after is not None:
                row["posterior_after"] = r.posterior_after
            if r.selection_context is not None:
                row["selection_context"] = r.selection_context
            record_rows.append(row)

        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "regimes": [
                {
                    "regime_id": regime.regime_id,
                    "trait_estimates": [
                        {
                            "trait": t.trait,
                            "mean": t.mean,
                            "sd": t.sd,
                            "ci95": [t.ci95[0], t.ci95[1]],
                            "reliability": t.reliability,
                        }
                        for t in regime.traits
                    ],
                }
                for regime in self.regimes
            ],
            "diagnostics": self.diagnostics,
            "risk_flags": self.risk_flags,
            "budget": {
                "calls_used": self.budget.calls_used,
                "tokens_prompt": self.budget.prompt_tokens,
                "tokens_completion": self.budget.completion_tokens,
            },
            "stop_reason": self.stop_reason,
            "records": record_rows,
        }
