from __future__ import annotations

import queue
import threading
from datetime import datetime, timezone
from typing import Any


class LiveHub:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []
        self._active_runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        q: queue.Queue[dict[str, Any]] = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers = [item for item in self._subscribers if item is not q]

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(event)
            except queue.Full:
                continue

    def start_run(self, run_id: str, agent_name: str) -> None:
        with self._lock:
            self._active_runs[run_id] = {
                "agent_id": run_id,
                "agent_name": agent_name,
                "status": "RUNNING",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "steps": [],
            }
        self.publish({"type": "run_started", "run_id": run_id, "agent_name": agent_name})

    def add_step(self, run_id: str, step: dict[str, Any]) -> None:
        with self._lock:
            run = self._active_runs.get(run_id)
            if run is None:
                return
            run_steps = run["steps"]
            run_steps.append(step)
        self.publish({"type": "step", "run_id": run_id, "step": step})

    def finish_run(self, run_id: str, status: str, error: str | None = None) -> None:
        with self._lock:
            run = self._active_runs.get(run_id)
            if run is not None:
                run["status"] = status
                run["error_message"] = error
            self._active_runs.pop(run_id, None)
        self.publish({"type": "run_finished", "run_id": run_id, "status": status, "error_message": error})

    def get_active_runs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._active_runs.values()]

    def get_active_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            run = self._active_runs.get(run_id)
            return dict(run) if run is not None else None


live_hub = LiveHub()
