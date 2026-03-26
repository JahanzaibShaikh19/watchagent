from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from .config import add_team_member, get_alerts_config, get_team_members, remove_team_member, set_alert_email, set_slack_webhook
from .license import LicenseError, activate_license, refresh_license_status, require_pro
from .serve import serve
from .storage import daily_cost, get_run, list_runs, list_runs_for_export, monthly_cost, weekly_cost


def main() -> None:
    parser = argparse.ArgumentParser(prog="watchagent", description="Monitor and inspect AI agent runs")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="Show recent runs")
    list_parser.add_argument("--limit", type=int, default=20, help="Number of recent runs to show")

    show_parser = subparsers.add_parser("show", help="Show details for a run")
    show_parser.add_argument("id", help="Agent run ID (UUID)")

    subparsers.add_parser("cost", help="Show total LLM cost for current month")
    subparsers.add_parser("serve", help="Start dashboard API and UI")

    activate_parser = subparsers.add_parser("activate", help="Activate Pro license")
    activate_parser.add_argument("license_key", help="License key")

    subparsers.add_parser("license-status", help="Show current license status")

    config_parser = subparsers.add_parser("config", help="Configure watchagent")
    config_parser.add_argument("--slack-webhook", help="Set Slack webhook URL")
    config_parser.add_argument("--alert-email", help="Set crash alert email")
    config_parser.add_argument("--team-add", help="Add team member email (Pro)")
    config_parser.add_argument("--team-remove", help="Remove team member email")
    config_parser.add_argument("--show", action="store_true", help="Show current configuration")

    export_parser = subparsers.add_parser("export", help="Export runs as CSV/JSON (Pro)")
    export_parser.add_argument("--format", choices=["csv", "json"], default="json")
    export_parser.add_argument("--output", required=True, help="Output file path")

    args = parser.parse_args()
    try:
        if args.command == "list":
            _ensure_license_checked()
            _cmd_list(args.limit)
            return

        if args.command == "show":
            _ensure_license_checked()
            _cmd_show(args.id)
            return

        if args.command == "cost":
            _ensure_license_checked()
            _cmd_cost()
            return

        if args.command == "serve":
            _ensure_license_checked()
            serve()
            return

        if args.command == "activate":
            _cmd_activate(args.license_key)
            return

        if args.command == "license-status":
            _cmd_license_status()
            return

        if args.command == "config":
            _ensure_license_checked()
            _cmd_config(args)
            return

        if args.command == "export":
            _ensure_license_checked()
            _cmd_export(args.format, args.output)
            return

        parser.print_help()
    except PermissionError as exc:
        print(str(exc))


def _cmd_list(limit: int) -> None:
    runs = list_runs(limit=limit)
    if not runs:
        print("No runs found.")
        return

    print("ID                                   NAME            STATUS   DURATION_MS  START_TIME")
    for run in runs:
        print(
            f"{run.agent_id:<36} {run.agent_name[:14]:<14} {run.status.value:<8} {run.duration_ms:<11} {run.start_time}"
        )


def _cmd_show(run_id: str) -> None:
    run = get_run(run_id)
    if run is None:
        print(f"Run not found: {run_id}")
        return

    print(f"agent_id: {run.agent_id}")
    print(f"agent_name: {run.agent_name}")
    print(f"status: {run.status.value}")
    print(f"start_time: {run.start_time}")
    print(f"end_time: {run.end_time}")
    print(f"duration_ms: {run.duration_ms}")
    print(f"error_message: {run.error_message}")
    print(f"error_traceback: {run.error_traceback}")
    print("crash_analysis:")
    print(run.crash_analysis or "")
    print(f"total_cost: {run.total_cost:.6f}")
    print("input:")
    print(json.dumps(run.input_data, indent=2, ensure_ascii=True))
    print("output:")
    print(json.dumps(run.output_data, indent=2, ensure_ascii=True))
    print("steps:")
    print(json.dumps([_step_to_dict(step) for step in run.steps], indent=2, ensure_ascii=True))


def _cmd_cost() -> None:
    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    week_start_dt = now - timedelta(days=now.weekday())
    week_end_dt = week_start_dt + timedelta(days=6)
    week_start = week_start_dt.strftime("%Y-%m-%d")
    week_end = week_end_dt.strftime("%Y-%m-%d")

    print(f"Daily total ({day}): ${daily_cost(day):.6f}")
    print(f"Weekly total ({week_start} to {week_end}): ${weekly_cost(week_start, week_end):.6f}")
    print(f"Monthly total ({month}): ${monthly_cost(month):.6f}")


def _cmd_activate(license_key: str) -> None:
    try:
        status = activate_license(license_key)
    except LicenseError as exc:
        print(f"Activation failed: {exc}")
        return
    print(f"Activation successful. Plan: {status.plan}")


def _cmd_license_status() -> None:
    status = refresh_license_status(force_online=False)
    print(f"Plan: {status.plan}")
    print(f"Active: {status.active}")
    print(f"Offline grace mode: {status.offline_mode}")
    print(f"Message: {status.message}")


def _cmd_config(args: argparse.Namespace) -> None:
    changed = False

    if args.slack_webhook is not None:
        set_slack_webhook(args.slack_webhook)
        print("Slack webhook updated.")
        changed = True

    if args.alert_email is not None:
        set_alert_email(args.alert_email)
        print("Alert email updated.")
        changed = True

    if args.team_add:
        require_pro("Team sharing")
        members = add_team_member(args.team_add, max_members=5)
        print(f"Team member added. Members ({len(members)}/5): {', '.join(members)}")
        changed = True

    if args.team_remove:
        members = remove_team_member(args.team_remove)
        print(f"Team member removed. Members ({len(members)}/5): {', '.join(members) if members else 'none'}")
        changed = True

    if args.show or not changed:
        alerts = get_alerts_config()
        members = get_team_members()
        print("Current config:")
        print(f"  slack_webhook: {'set' if alerts.get('slack_webhook') else 'not set'}")
        print(f"  alert_email: {alerts.get('email_to') or 'not set'}")
        print(f"  team_members ({len(members)}/5): {', '.join(members) if members else 'none'}")


def _cmd_export(output_format: str, output_path: str) -> None:
    require_pro("CSV/JSON export")
    runs = list_runs_for_export(limit=5000)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    items = [
        {
            "agent_id": run.agent_id,
            "agent_name": run.agent_name,
            "status": run.status.value,
            "duration_ms": run.duration_ms,
            "total_cost": run.total_cost,
            "start_time": run.start_time,
            "end_time": run.end_time,
            "error_message": run.error_message,
            "error_traceback": run.error_traceback,
            "crash_analysis": run.crash_analysis,
            "steps": [
                {
                    "kind": step.kind,
                    "message": step.message,
                    "timestamp": step.timestamp,
                    "data": step.data,
                }
                for step in run.steps
            ],
        }
        for run in runs
    ]

    if output_format == "json":
        out.write_text(json.dumps(items, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"Exported {len(items)} runs to {out}")
        return

    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
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
    print(f"Exported {len(items)} runs to {out}")


def _ensure_license_checked() -> None:
    refresh_license_status(force_online=False)


def _step_to_dict(step: object) -> dict[str, object]:
    return {
        "kind": getattr(step, "kind", ""),
        "message": getattr(step, "message", ""),
        "timestamp": getattr(step, "timestamp", ""),
        "data": getattr(step, "data", {}),
    }


if __name__ == "__main__":
    main()
