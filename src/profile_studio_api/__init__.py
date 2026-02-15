"""FastAPI backend for interactive profile studio."""

from __future__ import annotations

from typing import Any

create_app: Any | None
try:
    from .main import create_app
except Exception:
    # Keep package importable even when optional web dependencies are absent.
    create_app = None

__all__ = ["create_app"]
