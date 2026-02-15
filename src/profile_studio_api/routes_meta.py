"""Metadata endpoints for model/provider presets and glossary definitions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .deps import get_services
from .services import AppServices


router = APIRouter(prefix="/api", tags=["meta"])


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
        },
    }
