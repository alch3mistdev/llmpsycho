"""FastAPI application entrypoint for Profile Studio."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ingestion_watcher import IngestionWatcher
from .jobs import RunJobManager
from .model_catalog import ProviderModelCatalog
from .repository import ProfileStudioRepository
from .routes_ingestion import router as ingestion_router
from .routes_meta import router as meta_router
from .routes_profiles import router as profiles_router
from .routes_query_lab import router as query_lab_router
from .routes_runs import router as runs_router
from .services import AppServices
from .settings import AppSettings


def create_app() -> FastAPI:
    settings = AppSettings.load()
    settings.ensure_paths()

    repository = ProfileStudioRepository(settings.db_path)
    jobs = RunJobManager(settings=settings, repository=repository)
    ingestion = IngestionWatcher(settings=settings, repository=repository)
    model_catalog = ProviderModelCatalog()

    app = FastAPI(
        title="LLMPsycho Profile Studio API",
        version="0.1.0",
        description="Interactive profile creation, ingestion, exploration, and query-lab backend.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.services = AppServices(
        settings=settings,
        repository=repository,
        jobs=jobs,
        ingestion=ingestion,
        model_catalog=model_catalog,
    )

    @app.on_event("startup")
    def _startup() -> None:
        model_catalog.refresh(force=True)
        ingestion.start()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        ingestion.stop()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(runs_router)
    app.include_router(profiles_router)
    app.include_router(ingestion_router)
    app.include_router(query_lab_router)
    app.include_router(meta_router)

    return app


app = create_app()
