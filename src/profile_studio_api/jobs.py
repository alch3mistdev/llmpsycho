"""Asynchronous run job manager for profile creation."""

from __future__ import annotations

from dataclasses import fields
import hashlib
import json
from pathlib import Path
import threading
import traceback
from typing import Any
import uuid

from adaptive_profiler import AdaptiveProfilerEngine, RunConfig, build_item_bank
from adaptive_profiler.config import RegimeConfig
from adaptive_profiler.simulate import SimulatedModelAdapter, sample_true_thetas

from .models import RunCreateRequest
from .profile_explain import build_profile_summary, build_regime_deltas, build_trait_driver_map
from .repository import ProfileStudioRepository
from .settings import AppSettings


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).isoformat()


class RunJobManager:
    """Background execution manager for profile runs."""

    def __init__(self, settings: AppSettings, repository: ProfileStudioRepository) -> None:
        self.settings = settings
        self.repository = repository
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def create_run_job(self, request: RunCreateRequest) -> tuple[str, str]:
        job_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        requested = request.model_dump(mode="python")

        self.repository.create_run(
            run_id=run_id,
            job_id=job_id,
            model_id=request.model_id,
            provider=request.provider,
            requested=requested,
        )
        self.repository.append_run_event(run_id, "queued", {"job_id": job_id, "run_id": run_id})

        thread = threading.Thread(
            target=self._run_job,
            name=f"profile-run-{run_id}",
            kwargs={
                "job_id": job_id,
                "run_id": run_id,
                "request": request,
            },
            daemon=True,
        )

        with self._lock:
            self._threads[job_id] = thread
        thread.start()
        return job_id, run_id

    def _build_run_config(self, request: RunCreateRequest) -> RunConfig:
        allowed = {f.name for f in fields(RunConfig)}
        overrides = {k: v for k, v in request.run_config_overrides.items() if k in allowed}

        kwargs: dict[str, Any] = {"model_id": request.model_id}
        kwargs.update(overrides)

        if request.regimes:
            regimes: list[RegimeConfig] = []
            for candidate in request.regimes:
                regimes.append(
                    RegimeConfig(
                        regime_id=str(candidate.get("regime_id", "core")),
                        system_prompt=str(candidate.get("system_prompt", "")),
                        temperature=float(candidate.get("temperature", 0.2)),
                        tools_enabled=bool(candidate.get("tools_enabled", False)),
                    )
                )
            kwargs["regimes"] = tuple(regimes)

        return RunConfig(**kwargs)

    def _build_adapter(self, request: RunCreateRequest):
        if request.provider == "simulated":
            theta_seed = int(request.adapter_config.get("theta_seed", 61))
            sim_seed = int(request.adapter_config.get("sim_seed", 62))
            benchmark_trained = bool(request.adapter_config.get("benchmark_trained", False))
            return SimulatedModelAdapter(
                true_theta_by_regime=sample_true_thetas(seed=theta_seed),
                seed=sim_seed,
                benchmark_trained=benchmark_trained,
            )

        if request.provider == "openai":
            from adaptive_profiler import OpenAIAdapter

            return OpenAIAdapter(
                model=request.model_id,
                api_key=request.adapter_config.get("api_key"),
                max_tokens=int(request.adapter_config.get("max_tokens", 80)),
            )

        if request.provider == "anthropic":
            from adaptive_profiler import AnthropicAdapter

            return AnthropicAdapter(
                model=request.model_id,
                api_key=request.adapter_config.get("api_key"),
                max_tokens=int(request.adapter_config.get("max_tokens", 80)),
            )

        raise ValueError(f"Unsupported provider '{request.provider}'")

    def _persist_profile_artifact(
        self,
        *,
        run_id: str,
        model_id: str,
        provider: str,
        report_dict: dict[str, Any],
    ) -> tuple[str, Path, str]:
        profile_id = report_dict.get("run_id") or run_id
        metadata = {
            "profile_id": profile_id,
            "run_id": run_id,
            "model_id": model_id,
            "provider": provider,
            "source": "run",
            "created_at": _utc_now(),
            "version": 1,
        }
        envelope = {
            "metadata": metadata,
            "profile": report_dict,
            "profile_summary": build_profile_summary(report_dict, regime_id="core"),
            "regime_deltas": build_regime_deltas(report_dict),
            "trait_driver_map": build_trait_driver_map(report_dict, regime_id="core"),
            "explainability_version": 2,
        }
        raw = _json_bytes(envelope)
        checksum = _sha256_bytes(raw)

        artifact_path = self.settings.profiles_dir / f"{profile_id}.json"
        artifact_path.write_bytes(raw)

        self.repository.record_profile(
            profile_id=profile_id,
            run_id=run_id,
            model_id=model_id,
            provider=provider,
            source="run",
            artifact_path=str(artifact_path),
            checksum=checksum,
            payload=report_dict,
            metadata=metadata,
        )
        return profile_id, artifact_path, checksum

    def _run_job(self, *, job_id: str, run_id: str, request: RunCreateRequest) -> None:
        self.repository.update_run_status(run_id, status="running", set_started=True)
        self.repository.append_run_event(run_id, "running", {"run_id": run_id, "job_id": job_id})

        try:
            config = self._build_run_config(request)
            item_bank_seed = int(request.adapter_config.get("item_bank_seed", 17))
            engine_seed = int(request.adapter_config.get("engine_seed", 7))
            item_bank = build_item_bank(seed=item_bank_seed)

            adapter = self._build_adapter(request)
            engine = AdaptiveProfilerEngine(config=config, item_bank=item_bank, seed=engine_seed)

            def on_progress(event: dict[str, Any]) -> None:
                self.repository.append_run_event(run_id, "progress", event)

            report = engine.run(adapter, run_id=run_id, progress_callback=on_progress)
            report_dict = report.to_dict()

            profile_id, artifact_path, checksum = self._persist_profile_artifact(
                run_id=run_id,
                model_id=request.model_id,
                provider=request.provider,
                report_dict=report_dict,
            )

            summary = {
                "profile_id": profile_id,
                "artifact_path": str(artifact_path),
                "checksum": checksum,
                "calls_used": report_dict.get("budget", {}).get("calls_used"),
                "stop_reason": report_dict.get("stop_reason"),
                "critical_reliability_met": report_dict.get("diagnostics", {}).get("critical_reliability_met"),
                "critical_ci_met": report_dict.get("diagnostics", {}).get("critical_ci_met"),
            }
            self.repository.append_run_event(run_id, "completed", summary)
            self.repository.update_run_status(
                run_id,
                status="completed",
                summary=summary,
                set_finished=True,
            )
        except Exception as exc:
            trace = traceback.format_exc(limit=10)
            payload = {
                "error": str(exc),
                "trace": trace,
            }
            self.repository.append_run_event(run_id, "failed", payload)
            self.repository.update_run_status(
                run_id,
                status="failed",
                summary={"error": str(exc)},
                error_text=str(exc),
                set_finished=True,
            )
