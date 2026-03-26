from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import deque
from threading import Lock
from typing import Any

from .live import live_hub
from .models import Step


@dataclass
class _RunContext:
    run_id: str
    agent_name: str
    steps: list[Step] = field(default_factory=list)
    total_cost: float = 0.0
    loop_limit: int = 10
    recent_step_names: deque[str] = field(default_factory=lambda: deque(maxlen=10))
    lock: Lock = field(default_factory=Lock)


class LoopLimitExceeded(RuntimeError):
    pass


MODEL_PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4": (0.80, 4.0),
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
}


class StepLogger:
    """Per-run logger that stores steps in a context variable."""

    def __init__(self) -> None:
        self._ctx: ContextVar[_RunContext | None] = ContextVar("watchagent_run_context", default=None)

    def start_run(self, run_id: str, agent_name: str, loop_limit: int = 10) -> None:
        self._ctx.set(_RunContext(run_id=run_id, agent_name=agent_name, loop_limit=loop_limit))

    def end_run(self) -> None:
        self._ctx.set(None)

    def get_steps(self) -> list[Step]:
        run_ctx = self._ctx.get()
        if run_ctx is None:
            return []
        with run_ctx.lock:
            return list(run_ctx.steps)

    def get_total_cost(self) -> float:
        run_ctx = self._ctx.get()
        if run_ctx is None:
            return 0.0
        with run_ctx.lock:
            return run_ctx.total_cost

    def step(self, message: str, data: dict[str, Any] | None = None) -> None:
        self._append("STEP", message, data or {})
        self._check_loop(message)

    def tool_call(self, tool: str, input: dict[str, Any] | None = None, output: dict[str, Any] | None = None) -> None:
        payload = {
            "tool": tool,
            "input": input or {},
            "output": output or {},
        }
        event_name = f"tool:{tool}"
        self._append("TOOL_CALL", f"Tool call: {tool}", payload)
        self._check_loop(event_name)

    def llm_call(
        self,
        model: str,
        tokens: int | None = None,
        cost: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> float:
        in_tokens = int(tokens if tokens is not None else (input_tokens or 0))
        out_tokens = int(output_tokens or 0)
        computed_cost = float(cost) if cost is not None else self._calculate_cost(model, in_tokens, out_tokens)

        payload = {
            "model": model,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "cost": computed_cost,
            "pricing_per_mtok": {
                "input": MODEL_PRICING_PER_MTOK.get(model, (0.0, 0.0))[0],
                "output": MODEL_PRICING_PER_MTOK.get(model, (0.0, 0.0))[1],
            },
        }
        self._append("LLM_CALL", f"LLM call: {model}", payload)
        self._check_loop(f"llm:{model}")
        run_ctx = self._ctx.get()
        if run_ctx is not None:
            with run_ctx.lock:
                run_ctx.total_cost += computed_cost
        return computed_cost

    def decision(self, message: str, reason: str | None = None, data: dict[str, Any] | None = None) -> None:
        payload = dict(data or {})
        if reason is not None:
            payload["reason"] = reason
        self._append("DECISION", message, payload)
        self._check_loop(message)

    def set_model_pricing(self, model: str, input_per_mtok: float, output_per_mtok: float) -> None:
        MODEL_PRICING_PER_MTOK[model] = (float(input_per_mtok), float(output_per_mtok))

    def _append(self, kind: str, message: str, data: dict[str, Any]) -> None:
        run_ctx = self._ctx.get()
        if run_ctx is None:
            return

        step = Step(
            kind=kind,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
        )
        with run_ctx.lock:
            run_ctx.steps.append(step)
        live_hub.add_step(
            run_ctx.run_id,
            {
                "kind": step.kind,
                "message": step.message,
                "timestamp": step.timestamp,
                "data": step.data,
            },
        )

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        input_rate, output_rate = MODEL_PRICING_PER_MTOK.get(model, (0.0, 0.0))
        return (input_tokens / 1_000_000.0) * input_rate + (output_tokens / 1_000_000.0) * output_rate

    def _check_loop(self, step_name: str) -> None:
        run_ctx = self._ctx.get()
        if run_ctx is None:
            return

        with run_ctx.lock:
            run_ctx.recent_step_names.append(step_name)
            same_count = sum(1 for name in run_ctx.recent_step_names if name == step_name)
            if same_count >= 3:
                alert_payload = {
                    "step_name": step_name,
                    "occurrences_in_last_10": same_count,
                    "window_size": len(run_ctx.recent_step_names),
                }
                loop_step = Step(
                    kind="LOOP_DETECTED",
                    message=f"LoopDetectedEvent: repeated step '{step_name}'",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    data=alert_payload,
                )
                run_ctx.steps.append(loop_step)
                live_hub.add_step(
                    run_ctx.run_id,
                    {
                        "kind": loop_step.kind,
                        "message": loop_step.message,
                        "timestamp": loop_step.timestamp,
                        "data": loop_step.data,
                    },
                )
                print(
                    f"[watchagent] WARNING: possible loop detected for step '{step_name}' "
                    f"({same_count} occurrences in last {len(run_ctx.recent_step_names)} steps)."
                )

            if same_count > run_ctx.loop_limit:
                raise LoopLimitExceeded(
                    f"Loop limit exceeded for step '{step_name}'. "
                    f"Detected {same_count} repeats in the last 10 steps; limit is {run_ctx.loop_limit}."
                )


logger = StepLogger()
