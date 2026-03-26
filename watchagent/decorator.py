from __future__ import annotations

import asyncio
import copy
import contextvars
import functools
import json
import os
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from urllib import request
from typing import Any, Callable, TypeVar, cast

from .live import live_hub
from .license import refresh_license_status
from .logger import LoopLimitExceeded, logger
from .models import RunRecord, RunStatus
from .storage import insert_run, prune_old_runs
from .alerts import send_crash_alerts

F = TypeVar("F", bound=Callable[..., Any])


DEFAULT_TIMEOUT_SECONDS = 300.0


def watch(name: str | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS, loop_limit: int = 10) -> Callable[[F], F]:
    """Capture function run telemetry for an AI agent."""

    def decorator(func: F) -> F:
        agent_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await _run_async(func, agent_name, timeout, loop_limit, args, kwargs)

            return cast(F, async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_sync(func, agent_name, timeout, loop_limit, args, kwargs)

        return cast(F, sync_wrapper)

    return decorator


def _run_sync(
    func: Callable[..., Any],
    agent_name: str,
    timeout: float,
    loop_limit: int,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    license_status = refresh_license_status(force_online=False)
    if license_status.plan != "PRO" and live_hub.get_active_runs():
        raise RuntimeError("Free tier allows monitoring only 1 active agent at a time. Upgrade to Pro for unlimited agents.")

    run_id = str(uuid.uuid4())
    start_dt = datetime.now(timezone.utc)
    start_perf = time.perf_counter()

    logger.start_run(run_id=run_id, agent_name=agent_name, loop_limit=loop_limit)
    live_hub.start_run(run_id=run_id, agent_name=agent_name)

    status = RunStatus.SUCCESS
    error_message: str | None = None
    error_traceback: str | None = None
    crash_analysis: str | None = None
    output_data: Any = None
    raised_exc: BaseException | None = None

    try:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            ctx = contextvars.copy_context()
            future = executor.submit(ctx.run, func, *args, **kwargs)
            try:
                output_data = future.result(timeout=timeout)
            except FutureTimeout:
                status = RunStatus.TIMEOUT
                error_message = f"Function timed out after {timeout} seconds"
                future.cancel()
                raised_exc = TimeoutError(error_message)
            except Exception as exc:  # noqa: BLE001
                status = RunStatus.FAILED
                error_message = str(exc)
                error_traceback = traceback.format_exc()
                crash_analysis = _analyze_crash(logger.get_steps(), error_traceback)
                raised_exc = exc
        finally:
            # Do not block on worker completion after timeout; persist partial state immediately.
            executor.shutdown(wait=False, cancel_futures=True)
    except LoopLimitExceeded as exc:
        status = RunStatus.FAILED
        error_message = str(exc)
        error_traceback = traceback.format_exc()
        crash_analysis = _analyze_crash(logger.get_steps(), error_traceback)
        raised_exc = exc
    except Exception as exc:  # noqa: BLE001
        status = RunStatus.FAILED
        error_message = str(exc)
        error_traceback = traceback.format_exc()
        crash_analysis = _analyze_crash(logger.get_steps(), error_traceback)
        raised_exc = exc
    finally:
        _persist_run(
            run_id=run_id,
            agent_name=agent_name,
            start_dt=start_dt,
            start_perf=start_perf,
            args=args,
            kwargs=kwargs,
            output_data=output_data,
            status=status,
            error_message=error_message,
            error_traceback=error_traceback,
            crash_analysis=crash_analysis,
        )
        live_hub.finish_run(run_id, status.value, error_message)
        logger.end_run()

    if raised_exc is not None:
        raise raised_exc
    return output_data


async def _run_async(
    func: Callable[..., Any],
    agent_name: str,
    timeout: float,
    loop_limit: int,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    license_status = refresh_license_status(force_online=False)
    if license_status.plan != "PRO" and live_hub.get_active_runs():
        raise RuntimeError("Free tier allows monitoring only 1 active agent at a time. Upgrade to Pro for unlimited agents.")

    run_id = str(uuid.uuid4())
    start_dt = datetime.now(timezone.utc)
    start_perf = time.perf_counter()

    logger.start_run(run_id=run_id, agent_name=agent_name, loop_limit=loop_limit)
    live_hub.start_run(run_id=run_id, agent_name=agent_name)

    status = RunStatus.SUCCESS
    error_message: str | None = None
    error_traceback: str | None = None
    crash_analysis: str | None = None
    output_data: Any = None
    raised_exc: BaseException | None = None

    try:
        try:
            output_data = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            status = RunStatus.TIMEOUT
            error_message = f"Function timed out after {timeout} seconds"
            raised_exc = TimeoutError(error_message)
        except Exception as exc:  # noqa: BLE001
            status = RunStatus.FAILED
            error_message = str(exc)
            error_traceback = traceback.format_exc()
            crash_analysis = _analyze_crash(logger.get_steps(), error_traceback)
            raised_exc = exc
    except LoopLimitExceeded as exc:
        status = RunStatus.FAILED
        error_message = str(exc)
        error_traceback = traceback.format_exc()
        crash_analysis = _analyze_crash(logger.get_steps(), error_traceback)
        raised_exc = exc
    except Exception as exc:  # noqa: BLE001
        status = RunStatus.FAILED
        error_message = str(exc)
        error_traceback = traceback.format_exc()
        crash_analysis = _analyze_crash(logger.get_steps(), error_traceback)
        raised_exc = exc
    finally:
        _persist_run(
            run_id=run_id,
            agent_name=agent_name,
            start_dt=start_dt,
            start_perf=start_perf,
            args=args,
            kwargs=kwargs,
            output_data=output_data,
            status=status,
            error_message=error_message,
            error_traceback=error_traceback,
            crash_analysis=crash_analysis,
        )
        live_hub.finish_run(run_id, status.value, error_message)
        logger.end_run()

    if raised_exc is not None:
        raise raised_exc
    return output_data


def _persist_run(
    run_id: str,
    agent_name: str,
    start_dt: datetime,
    start_perf: float,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    output_data: Any,
    status: RunStatus,
    error_message: str | None,
    error_traceback: str | None,
    crash_analysis: str | None,
) -> None:
    license_status = refresh_license_status(force_online=False)
    retention_days = 90 if license_status.plan == "PRO" else 7
    prune_old_runs(retention_days)

    end_dt = datetime.now(timezone.utc)
    duration_ms = int((time.perf_counter() - start_perf) * 1000)
    steps = logger.get_steps()

    replay_frames = _build_replay_frames(
        steps=steps,
        base_input={
            "args": _serialize(args),
            "kwargs": _serialize(kwargs),
        },
        final_output=_serialize(output_data),
    )

    run = RunRecord(
        agent_id=run_id,
        agent_name=agent_name,
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
        duration_ms=duration_ms,
        input_data={"args": _serialize(args), "kwargs": _serialize(kwargs)},
        output_data=_serialize(output_data),
        status=status,
        error_message=error_message,
        error_traceback=error_traceback,
        crash_analysis=crash_analysis,
        steps=steps,
        replay_frames=replay_frames,
        total_cost=logger.get_total_cost(),
    )
    insert_run(run)
    if status in {RunStatus.FAILED, RunStatus.TIMEOUT}:
        send_crash_alerts(run)


def _build_replay_frames(steps: list[Any], base_input: dict[str, Any], final_output: Any) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    current_state: dict[str, Any] = {"input": base_input, "timeline": []}
    for index, step in enumerate(steps, start=1):
        data = getattr(step, "data", {}) or {}
        step_message = getattr(step, "message", "")
        step_kind = getattr(step, "kind", "STEP")
        if isinstance(data, dict) and "state" in data:
            state_value = data.get("state")
            if isinstance(state_value, dict):
                current_state = copy.deepcopy(state_value)
            else:
                current_state = {"value": _serialize(state_value)}

        timeline = current_state.get("timeline", [])
        if not isinstance(timeline, list):
            timeline = []
        timeline = [*timeline, {"kind": step_kind, "message": step_message, "timestamp": getattr(step, "timestamp", "")}]
        current_state["timeline"] = timeline
        current_state["latest_step_data"] = _serialize(data)

        options = []
        if isinstance(data, dict):
            raw_options = data.get("options", [])
            if isinstance(raw_options, list):
                options = [str(item) for item in raw_options]

        frames.append(
            {
                "step_index": index,
                "kind": getattr(step, "kind", "STEP"),
                "message": step_message,
                "timestamp": getattr(step, "timestamp", ""),
                "state": copy.deepcopy(current_state),
                "options": options,
            }
        )

    if frames:
        frames[-1]["final_output"] = final_output
    return frames


def _analyze_crash(steps: list[Any], error: str | None) -> str:
    if not error:
        return ""

    last_steps = [
        {
            "kind": step.kind,
            "message": step.message,
            "timestamp": step.timestamp,
            "data": step.data,
        }
        for step in steps[-5:]
    ]

    prompt = (
        "Agent crashed. Last steps: "
        f"{json.dumps(last_steps, ensure_ascii=True)}\n"
        f"Error: {error}\n"
        "Explain in simple terms what went wrong and suggest fix in 3 bullet points."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_analysis(last_steps, error)

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = request.Request(
        url="https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body.get("content", [])
            if content and isinstance(content, list):
                first = content[0]
                if isinstance(first, dict) and first.get("type") == "text":
                    return str(first.get("text", "")).strip()
    except Exception:  # noqa: BLE001
        return _fallback_analysis(last_steps, error)
    return _fallback_analysis(last_steps, error)


def _fallback_analysis(last_steps: list[dict[str, Any]], error: str) -> str:
    last_messages = ", ".join(step.get("message", "") for step in last_steps if step.get("message"))
    return (
        "- The agent terminated due to an unhandled exception.\n"
        f"- The final sequence before failure was: {last_messages or 'no logged steps available'}.\n"
        "- Fix suggestion: add input guards, wrap risky operations in try/except, and log intermediate values "
        "to isolate the exact failing branch."
    )


def _serialize(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, tuple):
            return [_serialize(item) for item in value]
        if isinstance(value, list):
            return [_serialize(item) for item in value]
        if isinstance(value, dict):
            return {str(k): _serialize(v) for k, v in value.items()}
        return repr(value)
