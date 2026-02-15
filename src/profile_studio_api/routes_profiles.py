"""Profile listing, retrieval, and manual import endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from .deps import get_services
from .models import ProfileImportResponse
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

    return {
        "profile_id": profile_id,
        "index": row,
        "metadata": metadata,
        "profile": profile_payload,
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
