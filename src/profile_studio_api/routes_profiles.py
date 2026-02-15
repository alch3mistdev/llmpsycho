"""Profile listing, retrieval, and manual import endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from adaptive_profiler.item_bank import build_item_bank
from adaptive_profiler.types import Item

from .deps import get_services
from .models import ProfileImportResponse
from .profile_explain import (
    build_profile_summary,
    build_regime_deltas,
    build_trait_driver_map,
    explain_profile,
)
from .services import AppServices


router = APIRouter(prefix="/api", tags=["profiles"])

_ITEM_LOOKUP: dict[str, Item] = {item.item_id: item for item in build_item_bank(seed=17)}


def _load_profile_envelope(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact_path = Path(row["artifact_path"])
    if not artifact_path.exists():
        raise HTTPException(status_code=500, detail="Profile artifact file missing")

    with artifact_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and "profile" in payload and isinstance(payload["profile"], dict):
        metadata = payload.get("metadata") or {}
        return metadata, payload["profile"]
    if isinstance(payload, dict):
        return {}, payload
    raise HTTPException(status_code=500, detail="Profile artifact payload is invalid")


def _enrich_record(record: dict[str, Any]) -> dict[str, Any]:
    row = dict(record)
    item_id = str(row.get("item_id", ""))
    item = _ITEM_LOOKUP.get(item_id)
    if item is None:
        row["has_full_transcript"] = bool(row.get("prompt_text")) and bool(row.get("response_text"))
        return row

    if not row.get("prompt_text"):
        row["prompt_text"] = item.prompt
    if not row.get("scoring_type"):
        row["scoring_type"] = item.scoring_type
    if not row.get("trait_loadings"):
        row["trait_loadings"] = dict(item.trait_loadings)
    if not row.get("item_metadata"):
        row["item_metadata"] = dict(item.metadata)
    if not row.get("family"):
        row["family"] = item.family

    if "selection_context" not in row:
        row["selection_context"] = {}
    if isinstance(row["selection_context"], dict):
        row["selection_context"].setdefault("legacy_record", "posterior_after" not in row)

    row["has_full_transcript"] = bool(row.get("prompt_text")) and bool(row.get("response_text"))
    return row


def _trace_summary(profile_payload: dict[str, Any]) -> dict[str, Any]:
    records = profile_payload.get("records", [])
    if not isinstance(records, list):
        records = []

    stage_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    family_counts: dict[str, int] = {}
    full_transcript_count = 0
    enriched_count = 0

    for record in records:
        if not isinstance(record, dict):
            continue
        enriched = _enrich_record(record)
        stage = str(enriched.get("stage", ""))
        if stage in stage_counts:
            stage_counts[stage] += 1
        family = str(enriched.get("family", "unknown"))
        family_counts[family] = family_counts.get(family, 0) + 1
        if enriched.get("has_full_transcript"):
            full_transcript_count += 1
        if any(key in enriched for key in ("prompt_text", "scoring_type", "trait_loadings", "item_metadata")):
            enriched_count += 1

    return {
        "total_records": len(records),
        "records_with_full_transcript": full_transcript_count,
        "records_with_enriched_fields": enriched_count,
        "partial_trace": full_transcript_count < len(records),
        "stage_counts": stage_counts,
        "top_families": sorted(
            [{"family": family, "count": count} for family, count in family_counts.items()],
            key=lambda row: row["count"],
            reverse=True,
        )[:8],
    }


@router.get("/profiles")
def list_profiles(
    model_id: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    converged: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    services: AppServices = Depends(get_services),
) -> dict[str, Any]:
    rows = services.repository.list_profiles(
        model_id=model_id,
        provider=provider,
        converged=converged,
        limit=limit,
    )
    return {"profiles": rows, "count": len(rows)}


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    row = services.repository.get_profile(profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    metadata, profile_payload = _load_profile_envelope(row)

    explainability_enabled = services.settings.explainability_v2_enabled
    explainability_v3_enabled = services.settings.explainability_v3_enabled
    regime_id = "core"
    profile_summary = build_profile_summary(profile_payload, regime_id=regime_id) if explainability_enabled else None
    regime_deltas = build_regime_deltas(profile_payload) if explainability_enabled else None
    trait_driver_map = build_trait_driver_map(profile_payload, regime_id=regime_id) if explainability_enabled else None

    return {
        "profile_id": profile_id,
        "index": row,
        "metadata": metadata,
        "profile": profile_payload,
        "profile_summary": profile_summary,
        "regime_deltas": regime_deltas,
        "trait_driver_map": trait_driver_map,
        "explainability_version": 2 if explainability_enabled else 1,
        "trace_summary": _trace_summary(profile_payload) if explainability_v3_enabled else None,
    }


@router.get("/profiles/{profile_id}/explain")
def get_profile_explain(profile_id: str, regime_id: str = "core", services: AppServices = Depends(get_services)) -> dict[str, Any]:
    if not services.settings.explainability_v2_enabled:
        raise HTTPException(status_code=404, detail="Explainability v2 is disabled")

    row = services.repository.get_profile(profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    _, profile_payload = _load_profile_envelope(row)

    return {
        "profile_id": profile_id,
        "index": row,
        **explain_profile(profile_payload, regime_id=regime_id),
    }


@router.get("/profiles/{profile_id}/probe-trace")
def get_profile_probe_trace(
    profile_id: str,
    regime_id: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    family: str | None = Query(default=None),
    q: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=60, ge=1, le=500),
    services: AppServices = Depends(get_services),
) -> dict[str, Any]:
    if not services.settings.explainability_v3_enabled:
        raise HTTPException(status_code=404, detail="Explainability v3 is disabled")

    row = services.repository.get_profile(profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    _, profile_payload = _load_profile_envelope(row)

    records = profile_payload.get("records", [])
    if not isinstance(records, list):
        records = []

    filtered: list[dict[str, Any]] = []
    q_lower = (q or "").strip().lower()
    for record in records:
        if not isinstance(record, dict):
            continue
        enriched = _enrich_record(record)
        if regime_id and str(enriched.get("regime_id", "")) != regime_id:
            continue
        if stage and str(enriched.get("stage", "")).upper() != stage.upper():
            continue
        if family and str(enriched.get("family", "")) != family:
            continue
        if q_lower:
            haystack = " ".join(
                str(enriched.get(key, ""))
                for key in ("item_id", "family", "prompt_text", "response_text", "scoring_type", "stage")
            ).lower()
            if q_lower not in haystack:
                continue
        filtered.append(enriched)

    page = filtered[offset : offset + limit]
    return {
        "profile_id": profile_id,
        "count": len(page),
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "partial_trace": any(not bool(item.get("has_full_transcript")) for item in filtered),
        "items": page,
    }


@router.post("/profiles/import", response_model=ProfileImportResponse)
async def import_profile(
    file: UploadFile = File(...),
    services: AppServices = Depends(get_services),
) -> ProfileImportResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    result = services.ingestion.import_upload_bytes(file.filename, raw)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Import failed"))

    profile_id = result.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=500, detail="Import did not return profile_id")

    return ProfileImportResponse(
        profile_id=profile_id,
        status=str(result.get("status", "imported")),
        source="upload",
    )
