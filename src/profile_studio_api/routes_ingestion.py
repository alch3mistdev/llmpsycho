"""Ingestion watcher control and status endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from .deps import get_services
from .models import IngestionStatusResponse
from .services import AppServices


router = APIRouter(prefix="/api", tags=["ingestion"])


@router.post("/ingestion/scan")
def scan_ingestion(services: AppServices = Depends(get_services)) -> dict[str, Any]:
    results = services.ingestion.scan_once()
    return {
        "scanned": len(results),
        "results": results,
    }


@router.get("/ingestion/status", response_model=IngestionStatusResponse)
def ingestion_status(services: AppServices = Depends(get_services)) -> IngestionStatusResponse:
    status = services.ingestion.status()
    return IngestionStatusResponse(**status)
