from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import RunRecord, RunStatus, Step


def _db_path() -> Path:
    return Path.home() / ".watchagent" / "logs.db"


def _connect() -> sqlite3.Connection:
    db_file = _db_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def initialize() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                agent_id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                input_json TEXT,
                output_json TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                error_traceback TEXT,
                crash_analysis TEXT,
                steps_json TEXT,
                replay_json TEXT,
                total_cost REAL NOT NULL DEFAULT 0.0
            )
            """
        )
        _ensure_column(conn, "runs", "error_traceback", "TEXT")
        _ensure_column(conn, "runs", "crash_analysis", "TEXT")
        _ensure_column(conn, "runs", "replay_json", "TEXT")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runs_start_time
            ON runs(start_time DESC)
            """
        )


def insert_run(run: RunRecord) -> None:
    initialize()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                agent_id,
                agent_name,
                start_time,
                end_time,
                duration_ms,
                input_json,
                output_json,
                status,
                error_message,
                error_traceback,
                crash_analysis,
                steps_json,
                replay_json,
                total_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.agent_id,
                run.agent_name,
                run.start_time,
                run.end_time,
                run.duration_ms,
                json.dumps(run.input_data, ensure_ascii=True),
                json.dumps(run.output_data, ensure_ascii=True),
                run.status.value,
                run.error_message,
                run.error_traceback,
                run.crash_analysis,
                json.dumps([_step_to_dict(step) for step in run.steps], ensure_ascii=True),
                json.dumps(run.replay_frames, ensure_ascii=True),
                float(run.total_cost),
            ),
        )


def list_runs(limit: int = 20) -> list[RunRecord]:
    initialize()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM runs
            ORDER BY start_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_runs_paginated(page: int = 1, page_size: int = 50) -> tuple[list[RunRecord], int]:
    initialize()
    page = max(page, 1)
    page_size = max(min(page_size, 200), 1)
    offset = (page - 1) * page_size

    with _connect() as conn:
        total_row = conn.execute("SELECT COUNT(*) AS total FROM runs").fetchone()
        rows = conn.execute(
            """
            SELECT * FROM runs
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()

    total = int(total_row["total"]) if total_row is not None else 0
    return [_row_to_record(row) for row in rows], total


def get_run(agent_id: str) -> RunRecord | None:
    initialize()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM runs
            WHERE agent_id = ?
            """,
            (agent_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def delete_run(agent_id: str) -> bool:
    initialize()
    with _connect() as conn:
        result = conn.execute(
            """
            DELETE FROM runs
            WHERE agent_id = ?
            """,
            (agent_id,),
        )
        return result.rowcount > 0


def monthly_cost(year_month: str) -> float:
    initialize()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(total_cost), 0.0) AS total
            FROM runs
            WHERE substr(start_time, 1, 7) = ?
            """,
            (year_month,),
        ).fetchone()
    if row is None:
        return 0.0
    return float(row["total"])


def total_cost() -> float:
    initialize()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(total_cost), 0.0) AS total
            FROM runs
            """
        ).fetchone()
    if row is None:
        return 0.0
    return float(row["total"])


def count_runs() -> int:
    initialize()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM runs").fetchone()
    if row is None:
        return 0
    return int(row["total"])


def count_success_runs() -> int:
    initialize()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM runs
            WHERE status = ?
            """,
            (RunStatus.SUCCESS.value,),
        ).fetchone()
    if row is None:
        return 0
    return int(row["total"])


def daily_cost(day: str) -> float:
    initialize()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(total_cost), 0.0) AS total
            FROM runs
            WHERE substr(start_time, 1, 10) = ?
            """,
            (day,),
        ).fetchone()
    if row is None:
        return 0.0
    return float(row["total"])


def weekly_cost(week_start: str, week_end: str) -> float:
    initialize()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(total_cost), 0.0) AS total
            FROM runs
            WHERE substr(start_time, 1, 10) >= ? AND substr(start_time, 1, 10) <= ?
            """,
            (week_start, week_end),
        ).fetchone()
    if row is None:
        return 0.0
    return float(row["total"])


def prune_old_runs(retention_days: int) -> int:
    initialize()
    with _connect() as conn:
        result = conn.execute(
            """
            DELETE FROM runs
            WHERE julianday('now') - julianday(start_time) > ?
            """,
            (retention_days,),
        )
    return int(result.rowcount)


def list_recent_agent_names(days: int) -> list[str]:
    initialize()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT agent_name
            FROM runs
            WHERE julianday('now') - julianday(start_time) <= ?
            ORDER BY agent_name ASC
            """,
            (days,),
        ).fetchall()
    return [str(row["agent_name"]) for row in rows]


def list_runs_for_export(limit: int = 5000) -> list[RunRecord]:
    return list_runs(limit=limit)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def _step_to_dict(step: Step) -> dict[str, Any]:
    return {
        "kind": step.kind,
        "message": step.message,
        "timestamp": step.timestamp,
        "data": step.data,
    }


def _row_to_record(row: sqlite3.Row) -> RunRecord:
    steps_json = row["steps_json"] or "[]"
    replay_json = row["replay_json"] or "[]"
    input_json = row["input_json"] or "null"
    output_json = row["output_json"] or "null"

    parsed_steps = json.loads(steps_json)
    steps = [
        Step(
            kind=item.get("kind", "STEP"),
            message=item.get("message", ""),
            timestamp=item.get("timestamp", ""),
            data=item.get("data", {}),
        )
        for item in parsed_steps
    ]

    return RunRecord(
        agent_id=row["agent_id"],
        agent_name=row["agent_name"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        duration_ms=int(row["duration_ms"]),
        input_data=json.loads(input_json),
        output_data=json.loads(output_json),
        status=RunStatus(row["status"]),
        error_message=row["error_message"],
        error_traceback=row["error_traceback"],
        crash_analysis=row["crash_analysis"],
        steps=steps,
        replay_frames=json.loads(replay_json),
        total_cost=float(row["total_cost"]),
    )
