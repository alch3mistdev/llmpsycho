"""Dependency helpers for route modules."""

from __future__ import annotations

from fastapi import Request

from .services import AppServices


def get_services(request: Request) -> AppServices:
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("App services are not initialized")
    return services
