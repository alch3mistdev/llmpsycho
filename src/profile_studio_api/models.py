"""Pydantic request/response contracts for Profile Studio APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Literal


Provider = Literal["openai", "anthropic", "simulated"]


class RunCreateRequest(BaseModel):
    model_id: str = Field(min_length=1)
    provider: Provider = "simulated"
    adapter_config: dict[str, Any] = Field(default_factory=dict)
    run_config_overrides: dict[str, Any] = Field(default_factory=dict)
    regimes: list[dict[str, Any]] = Field(default_factory=list)


class RunCreateResponse(BaseModel):
    job_id: str
    run_id: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    model_id: str
    provider: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_text: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class ProfileImportResponse(BaseModel):
    profile_id: str
    status: str
    source: str


class IngestionStatusResponse(BaseModel):
    running: bool
    last_scan_at: str | None = None
    imported_count: int
    error_count: int
    recent: list[dict[str, Any]] = Field(default_factory=list)


class QueryLabRequest(BaseModel):
    profile_id: str
    provider: Provider = "simulated"
    model_id: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    regime_id: str = "core"
    adapter_config: dict[str, Any] = Field(default_factory=dict)


class QueryLabABRequest(QueryLabRequest):
    ab_mode: Literal["same_model"] = "same_model"


class MetaModelsResponse(BaseModel):
    models: list[dict[str, Any]]
