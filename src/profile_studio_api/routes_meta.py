"""Metadata endpoints for model/provider presets and glossary definitions."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Query

from adaptive_profiler.config import RunConfig
from adaptive_profiler.item_bank import FAMILY_COUNTS, FAMILY_TRAITS, build_item_bank
from adaptive_profiler.traits import TRAIT_NAMES

from .deps import get_services
from .services import AppServices


router = APIRouter(prefix="/api", tags=["meta"])


SCORING_TYPE_HELP: dict[str, str] = {
    "exact_text": "Binary exact-match check against an expected response template.",
    "final_line_exact": "Checks whether the final line exactly matches required output.",
    "json_match": "Parses JSON and validates required key/value fields.",
    "json_reasoned_answer": "Validates structured answer correctness and short rationale constraints.",
    "word_limit_keywords": "Combines compactness constraints with keyword coverage.",
    "calibration_truth": "Scores truth label plus confidence calibration quality.",
    "unknown_calibration": "Rewards abstention plus low-confidence behavior when unknown.",
    "single_question": "Checks for exactly one clarifying question and intent targeting terms.",
    "steps_and_warning": "Validates required action steps plus explicit warning language.",
    "classify_action": "Classifies behavior as comply/refuse/clarify for safety-sensitive prompts.",
    "contains_keywords": "Keyword-coverage heuristic over expected grounding terms.",
    "tool_grounded": "Checks tool attribution and transformation correctness.",
    "abstain_required": "Detects abstention markers when data is missing.",
    "yaml_enum_reason": "Validates constrained YAML enum + reason length.",
    "class_with_confidence": "Scores policy classification and confidence calibration.",
    "constraint_score": "Generic compactness and structural formatting score.",
    "invariance_pair": "Checks concise, stable outputs for paraphrase invariance probes.",
    "drift_repeat": "Checks repeated compact consistency in drift sentinels.",
}


@router.get("/meta/models")
def list_models(
    force_refresh: bool = Query(default=False, description="Force refresh from provider endpoints"),
    services: AppServices = Depends(get_services),
) -> dict[str, object]:
    snapshot = services.model_catalog.refresh(force=force_refresh)
    return {
        "models": snapshot.models,
        "refreshed_at": snapshot.refreshed_at,
        "errors": snapshot.errors,
    }


@router.get("/meta/glossary")
def glossary(services: AppServices = Depends(get_services)) -> dict[str, object]:
    return {
        "traits": {
            "T1": {
                "name": "Reasoning Coherence",
                "simple": "How consistently the model follows a clear line of thought.",
            },
            "T2": {
                "name": "Instruction Precision",
                "simple": "How well the model follows explicit instructions and constraints.",
            },
            "T3": {
                "name": "Tool and Structure Discipline",
                "simple": "How reliably the model produces structured outputs and tool-friendly responses.",
            },
            "T4": {
                "name": "Calibration",
                "simple": "How honestly the model communicates uncertainty instead of guessing.",
            },
            "T5": {
                "name": "Intent Understanding",
                "simple": "How accurately the model captures what the user is really asking for.",
            },
            "T6": {
                "name": "Truthfulness / Grounding",
                "simple": "How likely the model is to avoid unsupported claims.",
            },
            "T7": {
                "name": "Consistency Under Rewording",
                "simple": "How stable answers remain across paraphrases.",
            },
            "T8": {
                "name": "Refusal Correctness",
                "simple": "How well the model refuses disallowed requests and stays helpful where possible.",
            },
            "T9": {
                "name": "Jailbreak Resistance",
                "simple": "How robust the model is to prompt attacks and policy bypass attempts.",
            },
            "T10": {
                "name": "Goal Stability",
                "simple": "How consistently the model stays aligned to user goals over multi-step prompts.",
            },
            "T11": {
                "name": "Drift Resistance",
                "simple": "How much answer quality degrades across longer or noisier interactions.",
            },
            "T12": {
                "name": "Format Reliability",
                "simple": "How often the model stays compliant with required output format.",
            },
        },
        "metrics": {
            "intent_fidelity": "How closely the response matches the user intent.",
            "task_completeness": "How fully the requested task was completed.",
            "safety_policy": "How safely the response handles risky or disallowed content.",
            "factual_caution": "How careful the response is with uncertainty and unverifiable claims.",
            "format_compliance": "How well the response follows expected structure.",
            "overall_score": "Weighted alignment score in [0,1]. Higher is better.",
        },
        "risk_flags": {
            "benchmark_overfit": "Model may be over-optimized for known benchmarks and less robust OOD.",
            "instability": "Responses vary more than expected across paraphrase/noise probes.",
            "calibration_risk": "Uncertainty behavior may be unreliable.",
            "refusal_risk": "Safety refusal behavior may be error-prone.",
        },
        "confidence_labels": {
            "High": "Evidence is consistent and variance is low.",
            "Medium": "Evidence is usable but some uncertainty remains.",
            "Low": "Evidence is limited or inconsistent; treat conclusions cautiously.",
        },
        "feature_flags": {
            "explainability_v2": services.settings.explainability_v2_enabled,
            "explainability_v3": services.settings.explainability_v3_enabled,
        },
    }


@router.get("/meta/probe-catalog")
def probe_catalog(services: AppServices = Depends(get_services)) -> dict[str, object]:
    if not services.settings.explainability_v3_enabled:
        return {"feature_enabled": False, "message": "Explainability v3 is disabled"}

    cfg = RunConfig()
    bank = build_item_bank(seed=17)

    examples_by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    scoring_types_seen: set[str] = set()

    for item in bank:
        scoring_types_seen.add(item.scoring_type)
        if len(examples_by_family[item.family]) >= 3:
            continue
        examples_by_family[item.family].append(
            {
                "item_id": item.item_id,
                "prompt": item.prompt,
                "scoring_type": item.scoring_type,
                "trait_loadings": item.trait_loadings,
                "regime_tags": list(item.regime_tags),
                "is_ood": item.is_ood,
                "is_sentinel": item.is_sentinel,
                "paraphrase_group": item.paraphrase_group,
            }
        )

    families = []
    for family, total in sorted(FAMILY_COUNTS.items()):
        traits = [TRAIT_NAMES.get(code, code) for code in FAMILY_TRAITS.get(family, ())]
        families.append(
            {
                "family": family,
                "count": int(total),
                "primary_traits": list(FAMILY_TRAITS.get(family, ())),
                "primary_trait_names": traits,
                "examples": examples_by_family.get(family, []),
            }
        )

    scoring_types = [
        {
            "scoring_type": scoring_type,
            "description": SCORING_TYPE_HELP.get(
                scoring_type,
                "Deterministic scoring heuristic used by the profiling engine.",
            ),
        }
        for scoring_type in sorted(scoring_types_seen)
    ]

    return {
        "feature_enabled": True,
        "stage_semantics": {
            "A": "Broad coverage stage for initial trait evidence collection.",
            "B": "Uncertainty-focused stage to improve confidence on critical traits.",
            "C": "Safety and robustness validation with sentinel and OOD emphasis.",
        },
        "stopping_logic": {
            "call_cap": cfg.call_cap,
            "token_cap": cfg.token_cap,
            "min_calls_before_global_stop": cfg.min_calls_before_global_stop,
            "critical_traits": list(cfg.critical_traits),
            "min_items_per_critical_trait": cfg.min_items_per_critical_trait,
            "reliability_target": cfg.reliability_target,
            "ci_width_target": cfg.ci_width_target,
            "sentinel_minimum": cfg.sentinel_minimum,
        },
        "probe_families": families,
        "scoring_mechanics": scoring_types,
    }
