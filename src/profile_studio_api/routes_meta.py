"""Metadata endpoints for model/provider presets."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .deps import get_services
from .services import AppServices


router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta/models")
def list_models(services: AppServices = Depends(get_services)) -> dict[str, object]:
    snapshot = services.model_catalog.refresh(force=False)
    return {
        "models": snapshot.models,
        "refreshed_at": snapshot.refreshed_at,
        "errors": snapshot.errors,
    }
