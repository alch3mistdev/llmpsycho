"""Service container helpers for FastAPI app state."""

from __future__ import annotations

from dataclasses import dataclass

from .ingestion_watcher import IngestionWatcher
from .jobs import RunJobManager
from .model_catalog import ProviderModelCatalog
from .repository import ProfileStudioRepository
from .settings import AppSettings


@dataclass
class AppServices:
    settings: AppSettings
    repository: ProfileStudioRepository
    jobs: RunJobManager
    ingestion: IngestionWatcher
    model_catalog: ProviderModelCatalog
