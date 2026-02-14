"""Multidimensional 2PL-style posterior updates with diagonal covariance."""

from __future__ import annotations

import math

from .types import Item, PosteriorState


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class DiagonalMIRT:
    """
    Lightweight diagonal approximation for MIRT updates.

    The implementation keeps the model cheap and stable for online adaptive testing.
    """

    def __init__(self, information_scale: float = 25.0) -> None:
        self.information_scale = max(1.0, information_scale)

    def expected_probability(self, item: Item, posterior: PosteriorState) -> float:
        eta = -item.difficulty
        for trait, loading in item.trait_loadings.items():
            eta += loading * posterior.mean.get(trait, 0.0)
        base = _sigmoid(eta)
        guess = max(0.0, min(0.35, item.guessing))
        return guess + (1.0 - guess) * base

    def expected_information_gain(self, item: Item, posterior: PosteriorState) -> float:
        p = self.expected_probability(item, posterior)
        fisher_scale = max(1e-6, p * (1.0 - p))
        variance_term = 0.0
        for trait, loading in item.trait_loadings.items():
            variance_term += (loading * loading) * posterior.variance.get(trait, 1.0)
        return 0.35 * math.log1p(fisher_scale * variance_term)

    def update(self, posterior: PosteriorState, item: Item, score: float) -> PosteriorState:
        """
        One-step online update for score in [0, 1].

        score may be binary or partial-credit. Update is an approximation around current
        posterior mean and diagonal Hessian.
        """
        score = max(0.0, min(1.0, score))
        out = posterior.copy()
        p = self.expected_probability(item, posterior)
        error = score - p

        for trait, loading in item.trait_loadings.items():
            prev_var = max(out.variance[trait], 1e-9)
            prev_prec = 1.0 / prev_var

            # Approximate diagonal curvature for logistic observation.
            h_diag = max(
                1e-6,
                self.information_scale
                * (1.0 - item.guessing) ** 2
                * p
                * (1.0 - p)
                * (loading**2),
            )
            new_prec = prev_prec + h_diag
            new_var = 1.0 / new_prec

            # Scaled correction term; small stabilization keeps updates conservative.
            delta = new_var * loading * error
            out.mean[trait] += delta
            out.variance[trait] = new_var

        return out
