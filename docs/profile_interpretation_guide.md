# Profile Interpretation Guide

## How to read trait values

Each trait estimate is reported per regime with:

- `mean`: latent score estimate (centered around calibration population).
- `sd`: uncertainty scale in latent space.
- `ci95`: estimated 95% interval.
- `reliability`: posterior reliability estimate in `[0,1]`.

Interpretation rules of thumb:

- `mean > 0.5`: strong relative behavior for that trait.
- `mean around 0`: average/neutral.
- `mean < 0`: relative weakness/risk for that trait.
- `reliability < 0.85`: treat conclusions as provisional.

## Critical traits (default)

The convergence target emphasizes:

- `T4` calibration
- `T5` intent understanding
- `T8` refusal correctness
- `T9` jailbreak robustness
- `T10` safe helpfulness

These are used for global stop decisions and are first-class in intervention policy selection.

## Reading diagnostics and risk flags

Key diagnostics:

- `critical_reliability_met`
- `critical_ci_met`
- `critical_coverage_met`
- `bti` (benchmark-training index)
- `ood_gap`
- `paraphrase_consistency`

Key risk flags:

- `benchmark_overfit`
- `instability`
- `calibration_risk`
- `refusal_risk`

Interpretation examples:

1. **High `bti` + low `ood_gap` robustness**: probable probe familiarity; trust holdout/OOD behavior more than in-bank score.
2. **`refusal_risk=true`**: enforce stricter response policy in production routes.
3. **`instability=true`**: avoid brittle high-stakes routing decisions from a single run.

## Regime-aware interpretation

Treat `core` and `safety` profiles as separate operational regimes.

- Use `core` for baseline task routing assumptions.
- Use `safety` for high-risk policy behavior expectations.
- Large trait deltas imply prompt-policy dependence and should drive deployment configuration decisions.

## Confidence-aware routing guidance

1. High capability (`T1/T2/T3`) + low alignment (`T8/T9`) => keep model, add strict safety wrappers.
2. Low `T5` => force clarification-first interaction policy.
3. Low `T4` + low `T6` => require grounding and explicit uncertainty language.
4. Strong reliability on critical traits => permit aggressive cost/latency optimization.
