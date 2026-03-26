from __future__ import annotations

import json
import queue
from io import StringIO
from datetime import datetime
from typing import Any
import csv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

from .license import refresh_license_status
from .live import live_hub
from .models import RunRecord
from .storage import (
    count_runs,
    count_success_runs,
    delete_run,
    get_run,
    list_runs_for_export,
    list_runs_paginated,
    monthly_cost,
)

app = FastAPI(title="watchagent dashboard api", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _step_to_dict(step: Any) -> dict[str, Any]:
    if isinstance(step, dict):
        return step
    return {
        "kind": getattr(step, "kind", ""),
        "message": getattr(step, "message", ""),
        "timestamp": getattr(step, "timestamp", ""),
        "data": getattr(step, "data", {}),
    }


def _run_to_dict(run: RunRecord) -> dict[str, Any]:
    return {
        "agent_id": run.agent_id,
        "agent_name": run.agent_name,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "duration_ms": run.duration_ms,
        "input": run.input_data,
        "output": run.output_data,
        "status": run.status.value,
        "error_message": run.error_message,
        "error_traceback": run.error_traceback,
        "crash_analysis": run.crash_analysis,
        "steps": [_step_to_dict(step) for step in run.steps],
        "total_cost": run.total_cost,
        "replay_frames_count": len(run.replay_frames),
    }


def _require_dashboard_pro() -> None:
    status = refresh_license_status(force_online=False)
    if status.plan != "PRO" or not status.active:
        raise HTTPException(status_code=402, detail="Dashboard access requires Pro tier")


@app.get("/api/runs")
def api_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    _require_dashboard_pro()
    runs, total = list_runs_paginated(page=page, page_size=page_size)
    active_runs = live_hub.get_active_runs()

    data = [
        {
            "agent_id": run.agent_id,
            "agent_name": run.agent_name,
            "status": run.status.value,
            "duration_ms": run.duration_ms,
            "total_cost": run.total_cost,
            "start_time": run.start_time,
            "end_time": run.end_time,
        }
        for run in runs
    ]
    data = active_runs + data

    return {
        "items": data,
        "page": page,
        "page_size": page_size,
        "total": total + len(active_runs),
    }


@app.get("/api/runs/live")
def api_runs_live() -> StreamingResponse:
    _require_dashboard_pro()
    subscriber = live_hub.subscribe()

    def event_generator() -> Any:
        try:
            snapshot = {
                "type": "snapshot",
                "active_runs": live_hub.get_active_runs(),
            }
            yield f"data: {json.dumps(snapshot, ensure_ascii=True)}\\n\\n"

            while True:
                try:
                    event = subscriber.get(timeout=2.0)
                    yield f"data: {json.dumps(event, ensure_ascii=True)}\\n\\n"
                except queue.Empty:
                    yield "event: ping\\ndata: {}\\n\\n"
        finally:
            live_hub.unsubscribe(subscriber)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/runs/{run_id}")
def api_run_detail(run_id: str) -> dict[str, Any]:
    _require_dashboard_pro()
    active = live_hub.get_active_run(run_id)
    if active is not None:
        return {
            "agent_id": active["agent_id"],
            "agent_name": active["agent_name"],
            "status": active["status"],
            "duration_ms": None,
            "start_time": active["start_time"],
            "end_time": None,
            "input": None,
            "output": None,
            "error_message": active.get("error_message"),
            "error_traceback": None,
            "crash_analysis": None,
            "steps": active.get("steps", []),
            "total_cost": 0.0,
        }

    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_dict(run)


@app.get("/api/runs/{run_id}/steps")
def api_run_steps(run_id: str) -> dict[str, Any]:
    _require_dashboard_pro()
    active = live_hub.get_active_run(run_id)
    if active is not None:
        return {
            "run_id": run_id,
            "status": "RUNNING",
            "items": active.get("steps", []),
        }

    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run_id,
        "status": run.status.value,
        "items": [_step_to_dict(step) for step in run.steps],
    }


@app.get("/api/stats")
def api_stats() -> dict[str, Any]:
    _require_dashboard_pro()
    total = count_runs()
    success = count_success_runs()
    success_rate = (success / total * 100.0) if total else 0.0
    month = datetime.now().strftime("%Y-%m")

    return {
        "total_runs": total,
        "success_rate": round(success_rate, 2),
        "total_cost_month": monthly_cost(month),
        "month": month,
    }


@app.delete("/api/runs/{run_id}")
def api_delete_run(run_id: str) -> dict[str, Any]:
    _require_dashboard_pro()
    removed = delete_run(run_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"deleted": True, "id": run_id}


@app.get("/api/runs/{run_id}/replay")
def api_run_replay(run_id: str) -> dict[str, Any]:
    _require_dashboard_pro()
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run_id,
        "items": run.replay_frames,
    }


@app.get("/api/runs/export")
def api_export_runs(format: str = Query("json", pattern="^(json|csv)$")) -> Response:
    _require_dashboard_pro()
    rows = list_runs_for_export(limit=5000)
    items = [_run_to_dict(item) for item in rows]

    if format == "json":
        return Response(content=json.dumps(items, ensure_ascii=True, indent=2), media_type="application/json")

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["agent_id", "agent_name", "status", "duration_ms", "total_cost", "start_time", "end_time", "error_message"],
    )
    writer.writeheader()
    for item in items:
        writer.writerow(
            {
                "agent_id": item["agent_id"],
                "agent_name": item["agent_name"],
                "status": item["status"],
                "duration_ms": item["duration_ms"],
                "total_cost": item["total_cost"],
                "start_time": item["start_time"],
                "end_time": item["end_time"],
                "error_message": item["error_message"],
            }
        )
    return Response(content=output.getvalue(), media_type="text/csv")


@app.get("/api/license/status")
def api_license_status() -> dict[str, Any]:
    status = refresh_license_status(force_online=False)
    return {
        "plan": status.plan,
        "active": status.active,
        "offline_mode": status.offline_mode,
        "message": status.message,
    }


