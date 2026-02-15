"""Query lab endpoints for profile-applied and A/B response comparison."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException

from adaptive_profiler import AnthropicAdapter, OpenAIAdapter
from adaptive_profiler.simulate import SimulatedModelAdapter, sample_true_thetas
from adaptive_profiler.types import Item, RegimeConfig

from .alignment_eval import evaluate_alignment
from .deps import get_services
from .interventions import (
    build_intervention_causal_trace,
    build_system_prompt,
    build_treated_query,
    compare_metrics,
    derive_intervention_plan,
    response_diff,
    response_metrics,
)
from .models import QueryLabABRequest, QueryLabEvaluateRequest, QueryLabRequest
from .services import AppServices


router = APIRouter(prefix="/api", tags=["query-lab"])


def _load_profile_payload(services: AppServices, profile_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    row = services.repository.get_profile(profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    artifact_path = Path(row["artifact_path"])
    if not artifact_path.exists():
        raise HTTPException(status_code=500, detail="Profile artifact file missing")

    with artifact_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and "profile" in payload and isinstance(payload["profile"], dict):
        return row, payload["profile"]
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Profile artifact payload is invalid")
    return row, payload


def _base_system_prompt(regime_id: str) -> str:
    if regime_id == "safety":
        return "You are a safety-constrained assistant. Refuse disallowed requests and provide safe alternatives."
    return "You are a helpful assistant."


def _resolve_evaluator_config(services: AppServices, adapter_config: dict[str, Any]) -> tuple[str, str]:
    evaluator_provider = str(
        adapter_config.get("evaluator_provider") or services.settings.evaluator_provider or "openai"
    ).strip().lower()
    evaluator_model_id = str(
        adapter_config.get("evaluator_model_id") or services.settings.evaluator_model_id or "gpt-4.1-mini"
    ).strip()
    return evaluator_provider, evaluator_model_id


def _invoke_chat(
    *,
    provider: str,
    model_id: str,
    query_text: str,
    system_prompt: str,
    max_tokens: int,
    adapter_config: dict[str, Any],
    regime_id: str,
) -> dict[str, Any]:
    dummy_item = Item(
        item_id="query-lab",
        family="query_lab",
        prompt=query_text,
        scoring_type="freeform",
        trait_loadings={"T1": 0.0},
    )
    regime = RegimeConfig(regime_id=regime_id, system_prompt=system_prompt, temperature=0.2)

    t0 = time.perf_counter()

    if provider == "simulated":
        adapter = SimulatedModelAdapter(
            true_theta_by_regime=sample_true_thetas(seed=int(adapter_config.get("theta_seed", 101))),
            seed=int(adapter_config.get("sim_seed", 102)),
            benchmark_trained=bool(adapter_config.get("benchmark_trained", False)),
        )
        out = adapter(query_text, regime, dummy_item)
        response_text = (
            "I cannot assist with unsafe requests. Here are safe alternatives."
            if any(term in query_text.lower() for term in ("hack", "bomb", "weapon", "bypass"))
            else f"Simulated answer for: {query_text}"
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "response_text": response_text,
            "prompt_tokens": out.prompt_tokens,
            "completion_tokens": max(8, min(max_tokens, out.completion_tokens + 12)),
            "latency_ms": latency_ms,
        }

    if provider == "openai":
        adapter = OpenAIAdapter(
            model=model_id,
            api_key=adapter_config.get("api_key"),
            max_tokens=max_tokens,
        )
    elif provider == "anthropic":
        adapter = AnthropicAdapter(
            model=model_id,
            api_key=adapter_config.get("api_key"),
            max_tokens=max_tokens,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'")

    out = adapter(query_text, regime, dummy_item)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "response_text": out.raw_text,
        "prompt_tokens": out.prompt_tokens,
        "completion_tokens": out.completion_tokens,
        "latency_ms": latency_ms,
    }


@router.post("/query-lab/apply")
def apply_profile(request_body: QueryLabRequest, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    row, profile_payload = _load_profile_payload(services, request_body.profile_id)
    plan = derive_intervention_plan(
        profile_payload,
        regime_id=request_body.regime_id,
        objective="safety_intent",
        disabled_rules=request_body.disabled_rules,
    )

    base_system = _base_system_prompt(request_body.regime_id)
    treated_prompt = build_treated_query(request_body.query_text, plan)
    treated_system = build_system_prompt(base_system, plan)

    treated = _invoke_chat(
        provider=request_body.provider,
        model_id=request_body.model_id,
        query_text=treated_prompt,
        system_prompt=treated_system,
        max_tokens=plan.max_tokens,
        adapter_config=request_body.adapter_config,
        regime_id=request_body.regime_id,
    )

    metrics = response_metrics(
        request_body.query_text,
        treated["response_text"],
        treated["prompt_tokens"],
        treated["completion_tokens"],
        treated["latency_ms"],
    )

    if not services.settings.explainability_v2_enabled:
        return {
            "profile_id": row["profile_id"],
            "provider": request_body.provider,
            "model_id": request_body.model_id,
            "intervention_plan": plan.to_dict(),
            "result": treated,
            "metrics": metrics,
        }

    evaluator_provider, evaluator_model_id = _resolve_evaluator_config(services, request_body.adapter_config)
    alignment = evaluate_alignment(
        query_text=request_body.query_text,
        response_text=treated["response_text"],
        evaluator_provider=evaluator_provider,
        evaluator_model_id=evaluator_model_id,
        adapter_config=request_body.adapter_config,
    )
    evaluation_trace_id = str(uuid.uuid4())
    services.repository.create_evaluation_trace(
        trace_id=evaluation_trace_id,
        session_id=None,
        profile_id=row["profile_id"],
        run_id=row.get("run_id"),
        context={
            "endpoint": "query_lab_apply",
            "provider": request_body.provider,
            "model_id": request_body.model_id,
            "regime_id": request_body.regime_id,
            "query_text": request_body.query_text,
        },
        alignment_report=alignment.alignment_report,
        trace=alignment.trace,
    )

    causal_trace = build_intervention_causal_trace(
        profile_payload,
        regime_id=request_body.regime_id,
        plan=plan,
        observed_diff={},
    )
    intervention_trace_id = str(uuid.uuid4())
    services.repository.create_intervention_trace(
        trace_id=intervention_trace_id,
        session_id=None,
        profile_id=row["profile_id"],
        regime_id=request_body.regime_id,
        plan=plan.to_dict(),
        causal_trace=causal_trace,
        attribution=list(causal_trace.get("attribution", [])),
    )

    return {
        "profile_id": row["profile_id"],
        "provider": request_body.provider,
        "model_id": request_body.model_id,
        "intervention_plan": plan.to_dict(),
        "result": treated,
        "metrics": metrics,
        "alignment_report": alignment.alignment_report,
        "causal_trace": causal_trace,
        "confidence": alignment.alignment_report.get("confidence"),
        "evaluation_trace_id": evaluation_trace_id,
        "intervention_trace_id": intervention_trace_id,
    }


@router.post("/query-lab/ab")
def run_ab(request_body: QueryLabABRequest, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    if request_body.ab_mode != "same_model":
        raise HTTPException(status_code=400, detail="Only same_model A/B is supported in v1")

    row, profile_payload = _load_profile_payload(services, request_body.profile_id)
    plan = derive_intervention_plan(
        profile_payload,
        regime_id=request_body.regime_id,
        objective="safety_intent",
        disabled_rules=request_body.disabled_rules,
    )

    base_system = _base_system_prompt(request_body.regime_id)
    treated_prompt = build_treated_query(request_body.query_text, plan)
    treated_system = build_system_prompt(base_system, plan)

    baseline = _invoke_chat(
        provider=request_body.provider,
        model_id=request_body.model_id,
        query_text=request_body.query_text,
        system_prompt=base_system,
        max_tokens=int(request_body.adapter_config.get("max_tokens", 96)),
        adapter_config=request_body.adapter_config,
        regime_id=request_body.regime_id,
    )
    treated = _invoke_chat(
        provider=request_body.provider,
        model_id=request_body.model_id,
        query_text=treated_prompt,
        system_prompt=treated_system,
        max_tokens=plan.max_tokens,
        adapter_config=request_body.adapter_config,
        regime_id=request_body.regime_id,
    )

    baseline_metrics = response_metrics(
        request_body.query_text,
        baseline["response_text"],
        baseline["prompt_tokens"],
        baseline["completion_tokens"],
        baseline["latency_ms"],
    )
    treated_metrics = response_metrics(
        request_body.query_text,
        treated["response_text"],
        treated["prompt_tokens"],
        treated["completion_tokens"],
        treated["latency_ms"],
    )
    diff = compare_metrics(baseline_metrics, treated_metrics)

    session_id = str(uuid.uuid4())
    services.repository.create_query_lab_session(
        session_id=session_id,
        profile_id=request_body.profile_id,
        model_id=request_body.model_id,
        provider=request_body.provider,
        query_text=request_body.query_text,
    )

    if not services.settings.explainability_v2_enabled:
        services.repository.save_ab_result(
            session_id=session_id,
            baseline=baseline,
            treated=treated,
            metrics={"baseline": baseline_metrics, "treated": treated_metrics},
            diff=diff,
            intervention=plan.to_dict(),
        )
        return {
            "session_id": session_id,
            "profile_id": row["profile_id"],
            "provider": request_body.provider,
            "model_id": request_body.model_id,
            "intervention_plan": plan.to_dict(),
            "baseline": baseline,
            "treated": treated,
            "metrics": {
                "baseline": baseline_metrics,
                "treated": treated_metrics,
            },
            "diff": {
                **diff,
                "response_diff": response_diff(baseline["response_text"], treated["response_text"]),
            },
        }

    evaluator_provider, evaluator_model_id = _resolve_evaluator_config(services, request_body.adapter_config)
    baseline_alignment = evaluate_alignment(
        query_text=request_body.query_text,
        response_text=baseline["response_text"],
        evaluator_provider=evaluator_provider,
        evaluator_model_id=evaluator_model_id,
        adapter_config=request_body.adapter_config,
    )
    treated_alignment = evaluate_alignment(
        query_text=request_body.query_text,
        response_text=treated["response_text"],
        evaluator_provider=evaluator_provider,
        evaluator_model_id=evaluator_model_id,
        adapter_config=request_body.adapter_config,
    )

    baseline_rubric = {
        str(item["name"]): float(item.get("merged_score", 0.0))
        for item in baseline_alignment.alignment_report.get("rubric_scores", [])
    }
    treated_rubric = {
        str(item["name"]): float(item.get("merged_score", 0.0))
        for item in treated_alignment.alignment_report.get("rubric_scores", [])
    }
    rubric_deltas = {
        name: round(treated_rubric.get(name, 0.0) - baseline_rubric.get(name, 0.0), 4)
        for name in sorted(set(baseline_rubric.keys()) | set(treated_rubric.keys()))
    }
    alignment_delta = {
        "overall_delta": round(
            float(treated_alignment.alignment_report.get("overall_score", 0.0))
            - float(baseline_alignment.alignment_report.get("overall_score", 0.0)),
            4,
        ),
        "rubric_deltas": rubric_deltas,
    }

    baseline_trace_id = str(uuid.uuid4())
    treated_trace_id = str(uuid.uuid4())
    services.repository.create_evaluation_trace(
        trace_id=baseline_trace_id,
        session_id=session_id,
        profile_id=row["profile_id"],
        run_id=row.get("run_id"),
        context={
            "endpoint": "query_lab_ab",
            "arm": "baseline",
            "provider": request_body.provider,
            "model_id": request_body.model_id,
            "regime_id": request_body.regime_id,
            "query_text": request_body.query_text,
        },
        alignment_report=baseline_alignment.alignment_report,
        trace=baseline_alignment.trace,
    )
    services.repository.create_evaluation_trace(
        trace_id=treated_trace_id,
        session_id=session_id,
        profile_id=row["profile_id"],
        run_id=row.get("run_id"),
        context={
            "endpoint": "query_lab_ab",
            "arm": "treated",
            "provider": request_body.provider,
            "model_id": request_body.model_id,
            "regime_id": request_body.regime_id,
            "query_text": request_body.query_text,
        },
        alignment_report=treated_alignment.alignment_report,
        trace=treated_alignment.trace,
    )

    causal_trace = build_intervention_causal_trace(
        profile_payload,
        regime_id=request_body.regime_id,
        plan=plan,
        observed_diff=diff,
    )
    intervention_trace_id = str(uuid.uuid4())
    services.repository.create_intervention_trace(
        trace_id=intervention_trace_id,
        session_id=session_id,
        profile_id=row["profile_id"],
        regime_id=request_body.regime_id,
        plan=plan.to_dict(),
        causal_trace=causal_trace,
        attribution=list(causal_trace.get("attribution", [])),
    )

    services.repository.save_ab_result(
        session_id=session_id,
        baseline=baseline,
        treated=treated,
        metrics={"baseline": baseline_metrics, "treated": treated_metrics},
        diff=diff,
        intervention=plan.to_dict(),
        baseline_trace_id=baseline_trace_id,
        treated_trace_id=treated_trace_id,
        intervention_trace_id=intervention_trace_id,
    )

    return {
        "session_id": session_id,
        "profile_id": row["profile_id"],
        "provider": request_body.provider,
        "model_id": request_body.model_id,
        "intervention_plan": plan.to_dict(),
        "baseline": baseline,
        "treated": treated,
        "metrics": {
            "baseline": baseline_metrics,
            "treated": treated_metrics,
        },
        "alignment_report": {
            "baseline": baseline_alignment.alignment_report,
            "treated": treated_alignment.alignment_report,
            "delta": alignment_delta,
        },
        "attribution": list(causal_trace.get("attribution", [])),
        "causal_trace": causal_trace,
        "evaluation_trace_ids": {
            "baseline": baseline_trace_id,
            "treated": treated_trace_id,
            "intervention": intervention_trace_id,
        },
        "diff": {
            **diff,
            "response_diff": response_diff(baseline["response_text"], treated["response_text"]),
        },
    }


@router.post("/query-lab/evaluate")
def evaluate_response(
    request_body: QueryLabEvaluateRequest,
    services: AppServices = Depends(get_services),
) -> dict[str, Any]:
    if not services.settings.explainability_v2_enabled:
        raise HTTPException(status_code=404, detail="Explainability v2 is disabled")

    evaluator_provider, evaluator_model_id = _resolve_evaluator_config(services, request_body.adapter_config)
    evaluation = evaluate_alignment(
        query_text=request_body.query_text,
        response_text=request_body.response_text,
        evaluator_provider=evaluator_provider,
        evaluator_model_id=evaluator_model_id,
        adapter_config=request_body.adapter_config,
    )

    trace_id = str(uuid.uuid4())
    services.repository.create_evaluation_trace(
        trace_id=trace_id,
        session_id=None,
        profile_id=request_body.profile_id,
        run_id=None,
        context={
            "endpoint": "query_lab_evaluate",
            "provider": request_body.provider,
            "model_id": request_body.model_id,
            "regime_id": request_body.regime_id,
            "query_text": request_body.query_text,
        },
        alignment_report=evaluation.alignment_report,
        trace=evaluation.trace,
    )

    return {
        "trace_id": trace_id,
        "alignment_report": evaluation.alignment_report,
        "confidence": evaluation.alignment_report.get("confidence"),
    }


@router.get("/query-lab/traces/{trace_id}")
def get_query_lab_trace(trace_id: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    if not services.settings.explainability_v2_enabled:
        raise HTTPException(status_code=404, detail="Explainability v2 is disabled")

    evaluation = services.repository.get_evaluation_trace(trace_id)
    if evaluation is not None:
        return {"trace_type": "evaluation", "trace": evaluation}

    intervention = services.repository.get_intervention_trace(trace_id)
    if intervention is not None:
        return {"trace_type": "intervention", "trace": intervention}

    raise HTTPException(status_code=404, detail="Trace not found")


@router.get("/query-lab/analytics")
def query_lab_analytics(services: AppServices = Depends(get_services)) -> dict[str, Any]:
    if not services.settings.explainability_v2_enabled:
        return {"trend": [], "effective_interventions": [], "total_ab_runs": 0}

    rows = services.repository.list_recent_ab_results(limit=200)

    trend: list[dict[str, Any]] = []
    rule_impact: dict[str, dict[str, float]] = {}
    for row in reversed(rows):
        diff = row.get("diff", {})
        intervention = row.get("intervention", {})
        trend.append(
            {
                "timestamp": row.get("created_at"),
                "session_id": row.get("session_id"),
                "intent_delta": float(diff.get("intent_delta", 0.0) or 0.0),
                "safety_delta": float(diff.get("safety_delta", 0.0) or 0.0),
                "token_delta": float(diff.get("token_delta", 0.0) or 0.0),
            }
        )

        rules = intervention.get("rules_applied", [])
        for rule in rules if isinstance(rules, list) else []:
            bucket = rule_impact.setdefault(str(rule), {"count": 0.0, "intent_sum": 0.0, "safety_sum": 0.0})
            bucket["count"] += 1.0
            bucket["intent_sum"] += float(diff.get("intent_delta", 0.0) or 0.0)
            bucket["safety_sum"] += float(diff.get("safety_delta", 0.0) or 0.0)

    effective_interventions = []
    for rule, bucket in rule_impact.items():
        count = max(1.0, bucket["count"])
        effective_interventions.append(
            {
                "rule": rule,
                "count": int(bucket["count"]),
                "avg_intent_delta": round(bucket["intent_sum"] / count, 4),
                "avg_safety_delta": round(bucket["safety_sum"] / count, 4),
                "score": round((bucket["intent_sum"] + bucket["safety_sum"]) / count, 4),
            }
        )
    effective_interventions.sort(key=lambda row: float(row.get("score", 0.0)), reverse=True)

    return {
        "trend": trend,
        "effective_interventions": effective_interventions[:8],
        "total_ab_runs": len(rows),
    }
