from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class Step:
    kind: str
    message: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunRecord:
    agent_id: str
    agent_name: str
    start_time: str
    end_time: str
    duration_ms: int
    input_data: Any
    output_data: Any
    status: RunStatus
    error_message: str | None = None
    error_traceback: str | None = None
    crash_analysis: str | None = None
    steps: list[Step] = field(default_factory=list)
    replay_frames: list[dict[str, Any]] = field(default_factory=list)
    total_cost: float = 0.0
