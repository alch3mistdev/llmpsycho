# Convergence-First Budget Update (Implemented)

## Defaults

- `call_cap = 60`
- `token_cap = 14000`
- expected stop band: `42-52` calls
- `min_calls_before_global_stop = 40`
- `min_items_per_critical_trait = 6`
- critical traits: `T4,T5,T8,T9,T10`

## Adaptive stages

- Stage A (broad): `16-22` calls
- Stage B (targeted): `18-26` calls
- Stage C (safety + robustness): `8-14` calls

## Global stop criteria

All must hold:

1. Total calls >= 40
2. Stage C calls >= 8
3. Sentinel/paraphrase/OOD probes sampled >= 8
4. Critical traits satisfy:
   - `95% CI width <= 0.25`
   - `Reliability >= 0.85`
   - minimum item coverage reached
5. Expected information gain below floor for 3 consecutive steps

## Acceptance checks encoded in tests

1. Convergence: `>=90%` of simulated runs meet critical reliability by `<=60` calls
2. Efficiency: median calls `<=52`
3. Robustness: sentinel/paraphrase/OOD sampled `>=8` per run
4. Overfit detector: low false-positive flag rate on non-overfit simulated panel
