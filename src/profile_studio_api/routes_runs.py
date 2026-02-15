"""Run creation, status, and live event streaming endpoints."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .deps import get_services
from .models import RunCreateRequest, RunCreateResponse, RunStatusResponse
from .services import AppServices


router = APIRouter(prefix="/api", tags=["runs"])


@router.post("/runs", response_model=RunCreateResponse)
def create_run(request_body: RunCreateRequest, services: AppServices = Depends(get_services)) -> RunCreateResponse:
    job_id, run_id = services.jobs.create_run_job(request_body)
    return RunCreateResponse(job_id=job_id, run_id=run_id)


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: str, services: AppServices = Depends(get_services)) -> RunStatusResponse:
    row = services.repository.get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatusResponse(
        run_id=row["run_id"],
        status=row["status"],
        model_id=row["model_id"],
        provider=row["provider"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        error_text=row["error_text"],
        summary=row["summary"],
    )


def _format_sse(*, event_id: int, event_type: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload)
    return f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    services: AppServices = Depends(get_services),
) -> StreamingResponse:
    if services.repository.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    last_id = 0
    header_last_event = request.headers.get("last-event-id")
    if header_last_event and header_last_event.isdigit():
        last_id = int(header_last_event)

    async def event_generator():
        nonlocal last_id
        idle_ticks = 0
        while True:
            if await request.is_disconnected():
                break

            events = services.repository.list_run_events(run_id, after_id=last_id)
            if events:
                idle_ticks = 0
                for event in events:
                    last_id = event["id"]
                    yield _format_sse(
                        event_id=event["id"],
                        event_type=event["event_type"],
                        payload=event["payload"],
                    )
            else:
                idle_ticks += 1
                yield ": keep-alive\n\n"

            run = services.repository.get_run(run_id)
            terminal = run is not None and run["status"] in {"completed", "failed"}
            if terminal and idle_ticks >= 2:
                summary = run.get("summary", {}) if run else {}
                yield _format_sse(
                    event_id=last_id + 1,
                    event_type="terminal",
                    payload={"status": run["status"], "summary": summary},
                )
                break

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
