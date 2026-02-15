"""Provider model catalog loaded from live provider endpoints with local fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import threading
import time
from typing import Any


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _looks_like_openai_model(model_id: str) -> bool:
    lowered = model_id.lower()
    return lowered.startswith("gpt-") or lowered.startswith("o") or lowered.startswith("chatgpt")


def _looks_like_anthropic_model(model_id: str) -> bool:
    lowered = model_id.lower()
    return lowered.startswith("claude")


@dataclass
class CatalogSnapshot:
    models: list[dict[str, Any]]
    refreshed_at: str | None
    errors: dict[str, str]


class ProviderModelCatalog:
    """Caches provider model IDs fetched from live APIs on backend startup."""

    def __init__(self, refresh_ttl_seconds: int = 300) -> None:
        self.refresh_ttl_seconds = max(10, refresh_ttl_seconds)
        self._lock = threading.Lock()
        self._models: list[dict[str, Any]] = []
        self._refreshed_at: str | None = None
        self._refreshed_epoch: float = 0.0
        self._errors: dict[str, str] = {}

    def refresh(self, *, force: bool = False) -> CatalogSnapshot:
        now = time.time()
        with self._lock:
            stale = (now - self._refreshed_epoch) > self.refresh_ttl_seconds
            if not force and self._models and not stale:
                return CatalogSnapshot(
                    models=list(self._models),
                    refreshed_at=self._refreshed_at,
                    errors=dict(self._errors),
                )

            models, errors = self._load_models()
            self._models = models
            self._errors = errors
            self._refreshed_epoch = now
            self._refreshed_at = _utc_now()
            return CatalogSnapshot(
                models=list(self._models),
                refreshed_at=self._refreshed_at,
                errors=dict(self._errors),
            )

    def snapshot(self) -> CatalogSnapshot:
        with self._lock:
            return CatalogSnapshot(
                models=list(self._models),
                refreshed_at=self._refreshed_at,
                errors=dict(self._errors),
            )

    def _load_models(self) -> tuple[list[dict[str, Any]], dict[str, str]]:
        models: list[dict[str, Any]] = []
        errors: dict[str, str] = {}

        models.append(
            {
                "provider": "simulated",
                "model_id": "simulated-local",
                "label": "Simulated Local Model",
                "available_hint": "No API key required",
                "source": "builtin",
            }
        )

        openai_models, openai_error = self._fetch_openai_models()
        if openai_models:
            for model_id in openai_models:
                models.append(
                    {
                        "provider": "openai",
                        "model_id": model_id,
                        "label": f"OpenAI {model_id}",
                        "available_hint": "Loaded from OpenAI models endpoint",
                        "source": "openai_api",
                    }
                )
        else:
            models.extend(
                [
                    {
                        "provider": "openai",
                        "model_id": "gpt-4o",
                        "label": "OpenAI GPT-4o",
                        "available_hint": "Fallback preset (set OPENAI_API_KEY for live list)",
                        "source": "fallback",
                    },
                    {
                        "provider": "openai",
                        "model_id": "gpt-4.1-mini",
                        "label": "OpenAI GPT-4.1 Mini",
                        "available_hint": "Fallback preset (set OPENAI_API_KEY for live list)",
                        "source": "fallback",
                    },
                ]
            )
            if openai_error:
                errors["openai"] = openai_error

        anthropic_models, anthropic_error = self._fetch_anthropic_models()
        if anthropic_models:
            for model_id in anthropic_models:
                models.append(
                    {
                        "provider": "anthropic",
                        "model_id": model_id,
                        "label": f"Anthropic {model_id}",
                        "available_hint": "Loaded from Anthropic models endpoint",
                        "source": "anthropic_api",
                    }
                )
        else:
            models.append(
                {
                    "provider": "anthropic",
                    "model_id": "claude-3-5-sonnet-20241022",
                    "label": "Anthropic Claude 3.5 Sonnet",
                    "available_hint": "Fallback preset (set ANTHROPIC_API_KEY for live list)",
                    "source": "fallback",
                }
            )
            if anthropic_error:
                errors["anthropic"] = anthropic_error

        # Deduplicate by provider/model pair while preserving first-seen order.
        out: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for row in models:
            key = (str(row.get("provider", "")), str(row.get("model_id", "")))
            if key in seen:
                continue
            seen.add(key)
            out.append(row)

        return out, errors

    def _fetch_openai_models(self) -> tuple[list[str], str | None]:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return [], "OPENAI_API_KEY not set"

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.models.list()
            data = getattr(response, "data", [])
            model_ids = sorted(
                {
                    str(getattr(model, "id", "")).strip()
                    for model in data
                    if str(getattr(model, "id", "")).strip()
                    and _looks_like_openai_model(str(getattr(model, "id", "")))
                }
            )
            return model_ids, None
        except Exception as exc:
            return [], f"OpenAI models endpoint fetch failed: {exc}"

    def _fetch_anthropic_models(self) -> tuple[list[str], str | None]:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            return [], "ANTHROPIC_API_KEY not set"

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            models_api = getattr(client, "models", None)
            if models_api is None or not hasattr(models_api, "list"):
                return [], "Anthropic SDK does not expose models.list()"

            response = models_api.list()
            data = getattr(response, "data", [])
            model_ids = sorted(
                {
                    str(getattr(model, "id", "")).strip()
                    for model in data
                    if str(getattr(model, "id", "")).strip()
                    and _looks_like_anthropic_model(str(getattr(model, "id", "")))
                }
            )
            return model_ids, None
        except Exception as exc:
            return [], f"Anthropic models endpoint fetch failed: {exc}"
