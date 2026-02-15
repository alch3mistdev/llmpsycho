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

from .deps import get_services
from .interventions import (
    build_system_prompt,
    build_treated_query,
    compare_metrics,
    derive_intervention_plan,
    response_diff,
    response_metrics,
)
from .models import QueryLabABRequest, QueryLabRequest
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
    plan = derive_intervention_plan(profile_payload, regime_id=request_body.regime_id, objective="safety_intent")

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

    return {
        "profile_id": row["profile_id"],
        "provider": request_body.provider,
        "model_id": request_body.model_id,
        "intervention_plan": plan.to_dict(),
        "result": treated,
        "metrics": metrics,
    }


@router.post("/query-lab/ab")
def run_ab(request_body: QueryLabABRequest, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    if request_body.ab_mode != "same_model":
        raise HTTPException(status_code=400, detail="Only same_model A/B is supported in v1")

    row, profile_payload = _load_profile_payload(services, request_body.profile_id)
    plan = derive_intervention_plan(profile_payload, regime_id=request_body.regime_id, objective="safety_intent")

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
