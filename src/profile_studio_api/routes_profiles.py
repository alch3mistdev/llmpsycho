"""Profile listing, retrieval, and manual import endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

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

    artifact_path = Path(row["artifact_path"])
    if not artifact_path.exists():
        raise HTTPException(status_code=500, detail="Profile artifact file missing")

    with artifact_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and "profile" in payload:
        metadata = payload.get("metadata") or {}
        profile_payload = payload["profile"]
    else:
        metadata = {}
        profile_payload = payload

    explainability_enabled = services.settings.explainability_v2_enabled
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
    }


@router.get("/profiles/{profile_id}/explain")
def get_profile_explain(profile_id: str, regime_id: str = "core", services: AppServices = Depends(get_services)) -> dict[str, Any]:
    if not services.settings.explainability_v2_enabled:
        raise HTTPException(status_code=404, detail="Explainability v2 is disabled")

    row = services.repository.get_profile(profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    artifact_path = Path(row["artifact_path"])
    if not artifact_path.exists():
        raise HTTPException(status_code=500, detail="Profile artifact file missing")

    with artifact_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and "profile" in payload and isinstance(payload["profile"], dict):
        profile_payload = payload["profile"]
    elif isinstance(payload, dict):
        profile_payload = payload
    else:
        raise HTTPException(status_code=500, detail="Profile artifact payload is invalid")

    return {
        "profile_id": profile_id,
        "index": row,
        **explain_profile(profile_payload, regime_id=regime_id),
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
