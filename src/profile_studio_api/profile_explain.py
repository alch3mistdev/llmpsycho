"""Profile explainability helpers for plain-language summaries and relationship views."""

from __future__ import annotations

from typing import Any

from adaptive_profiler.traits import TRAIT_NAMES

from .interventions import derive_intervention_plan


def _trait_map(profile_payload: dict[str, Any], regime_id: str) -> dict[str, float]:
    for regime in profile_payload.get("regimes", []):
        if regime.get("regime_id") != regime_id:
            continue
        out: dict[str, float] = {}
        for row in regime.get("trait_estimates", []):
            trait = str(row.get("trait", ""))
            try:
                out[trait] = float(row.get("mean", 0.0))
            except (TypeError, ValueError):
                out[trait] = 0.0
        return out
    return {}


def _score_label(score: float) -> str:
    if score >= 0.7:
        return "strong"
    if score >= 0.2:
        return "moderate"
    if score >= -0.2:
        return "mixed"
    return "weak"


def _human_trait(trait: str) -> str:
    return TRAIT_NAMES.get(trait, trait)


def build_profile_summary(profile_payload: dict[str, Any], regime_id: str = "core") -> dict[str, Any]:
    core = _trait_map(profile_payload, regime_id)
    if not core:
        return {
            "strengths": [],
            "risks": [],
            "recommended_usage": [],
            "cautionary_usage": [],
            "quick_take": "No trait estimates available for this regime.",
        }

    top = sorted(core.items(), key=lambda item: item[1], reverse=True)[:3]
    low = sorted(core.items(), key=lambda item: item[1])[:3]

    strengths = [
        {
            "trait": trait,
            "name": _human_trait(trait),
            "score": score,
            "label": _score_label(score),
            "summary": f"{_human_trait(trait)} appears { _score_label(score) } in {regime_id}.",
        }
        for trait, score in top
    ]
    risks = [
        {
            "trait": trait,
            "name": _human_trait(trait),
            "score": score,
            "label": _score_label(score),
            "summary": f"{_human_trait(trait)} may be a risk area ({_score_label(score)}).",
        }
        for trait, score in low
    ]

    recommended_usage: list[str] = []
    cautionary_usage: list[str] = []

    if core.get("T5", 0.0) > 0.2 and core.get("T10", 0.0) > 0.2:
        recommended_usage.append("Good fit for interactive assistance where user intent clarification matters.")
    if core.get("T1", 0.0) > 0.4 and core.get("T2", 0.0) > 0.3:
        recommended_usage.append("Suitable for structured reasoning and deterministic transform tasks.")
    if core.get("T8", 0.0) < 0.0 or core.get("T9", 0.0) < 0.0:
        cautionary_usage.append("Use stricter safety intervention tier for risky prompts.")
    if core.get("T4", 0.0) < 0.0:
        cautionary_usage.append("Require calibration/uncertainty language for high-stakes outputs.")
    if core.get("T6", 0.0) < 0.0:
        cautionary_usage.append("Use grounding checks to reduce unsupported claims.")

    if not recommended_usage:
        recommended_usage.append("General-purpose use is reasonable with default guardrails.")
    if not cautionary_usage:
        cautionary_usage.append("No severe risk concentration detected; monitor over time.")

    quick_take = (
        f"This profile is strongest in {', '.join(_human_trait(t) for t, _ in top[:2])} "
        f"and weakest in {', '.join(_human_trait(t) for t, _ in low[:2])}."
    )

    return {
        "strengths": strengths,
        "risks": risks,
        "recommended_usage": recommended_usage,
        "cautionary_usage": cautionary_usage,
        "quick_take": quick_take,
    }


def build_regime_deltas(profile_payload: dict[str, Any]) -> list[dict[str, Any]]:
    core = _trait_map(profile_payload, "core")
    safety = _trait_map(profile_payload, "safety")
    out: list[dict[str, Any]] = []

    keys = sorted(set(core.keys()) | set(safety.keys()))
    for trait in keys:
        c = core.get(trait, 0.0)
        s = safety.get(trait, c)
        delta = s - c
        out.append(
            {
                "trait": trait,
                "name": _human_trait(trait),
                "core": c,
                "safety": s,
                "delta": delta,
                "direction": "up" if delta > 0.05 else "down" if delta < -0.05 else "flat",
            }
        )

    return sorted(out, key=lambda row: abs(float(row["delta"])), reverse=True)


def build_trait_driver_map(profile_payload: dict[str, Any], regime_id: str = "core") -> list[dict[str, Any]]:
    plan = derive_intervention_plan(profile_payload, regime_id=regime_id)
    tmap = _trait_map(profile_payload, regime_id)

    rule_trait_map: dict[str, list[str]] = {
        "low_refusal_or_jailbreak": ["T8", "T9"],
        "low_intent_understanding": ["T5"],
        "low_calibration": ["T4"],
        "low_truthfulness_or_overfit": ["T6"],
        "high_capability_compact_mode": ["T1", "T2", "T3"],
        "default_profile_policy": ["T5", "T8"],
    }

    out: list[dict[str, Any]] = []
    for rule in plan.rules_applied:
        for trait in rule_trait_map.get(rule, []):
            value = tmap.get(trait, 0.0)
            out.append(
                {
                    "trait": trait,
                    "trait_name": _human_trait(trait),
                    "rule": rule,
                    "score": value,
                    "influence": abs(value),
                    "direction": "risk" if value < 0 else "support",
                }
            )

    if not out:
        for trait, value in tmap.items():
            out.append(
                {
                    "trait": trait,
                    "trait_name": _human_trait(trait),
                    "rule": "default_profile_policy",
                    "score": value,
                    "influence": abs(value),
                    "direction": "risk" if value < 0 else "support",
                }
            )

    return out


def explain_profile(profile_payload: dict[str, Any], regime_id: str = "core") -> dict[str, Any]:
    summary = build_profile_summary(profile_payload, regime_id=regime_id)
    deltas = build_regime_deltas(profile_payload)
    drivers = build_trait_driver_map(profile_payload, regime_id=regime_id)

    key_delta = deltas[0] if deltas else None
    delta_text = (
        f"Largest regime shift is {key_delta['name']} ({key_delta['direction']}, delta {key_delta['delta']:.3f})."
        if key_delta
        else "No regime shift available."
    )

    return {
        "regime_id": regime_id,
        "quick_take": summary.get("quick_take"),
        "summary": summary,
        "regime_delta_note": delta_text,
        "top_drivers": sorted(drivers, key=lambda row: float(row.get("influence", 0.0)), reverse=True)[:8],
        "explainability_version": 2,
    }
