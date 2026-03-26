from __future__ import annotations

import json
import os
from urllib import request

from .config import get_alerts_config
from .models import RunRecord


def _dashboard_link(run_id: str) -> str:
    base = os.getenv("WATCHAGENT_DASHBOARD_URL", "http://127.0.0.1:3001")
    return f"{base}/runs/{run_id}"


def send_slack_crash_alert(run: RunRecord) -> None:
    cfg = get_alerts_config()
    webhook = cfg.get("slack_webhook", "")
    if not webhook:
        return

    payload = {
        "text": f"watchagent crash detected for {run.agent_name}",
        "attachments": [
            {
                "color": "#ef4444",
                "fields": [
                    {"title": "Agent", "value": run.agent_name, "short": True},
                    {"title": "Status", "value": run.status.value, "short": True},
                    {"title": "Error", "value": run.error_message or "unknown", "short": False},
                    {"title": "AI explanation", "value": run.crash_analysis or "No explanation", "short": False},
                    {"title": "Dashboard", "value": _dashboard_link(run.agent_id), "short": False},
                ],
            }
        ],
    }

    req = request.Request(
        url=webhook,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        request.urlopen(req, timeout=8).read()
    except Exception:  # noqa: BLE001
        return


def _build_html_email(run: RunRecord) -> str:
    return f"""
    <html>
      <body style=\"font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;\">
        <div style=\"max-width:680px;margin:0 auto;background:#111827;border-radius:12px;padding:24px;border:1px solid #334155;\">
          <h2 style=\"margin-top:0;color:#fda4af;\">watchagent crash alert</h2>
          <p><strong>Agent:</strong> {run.agent_name}</p>
          <p><strong>Status:</strong> {run.status.value}</p>
          <p><strong>Error:</strong> {run.error_message or 'Unknown error'}</p>
          <h3 style=\"color:#7dd3fc;\">AI analysis</h3>
          <pre style=\"white-space:pre-wrap;background:#0b1220;padding:12px;border-radius:8px;border:1px solid #1e293b;\">{run.crash_analysis or 'No explanation available.'}</pre>
          <p>
            <a href=\"{_dashboard_link(run.agent_id)}\" style=\"display:inline-block;padding:10px 14px;background:#0ea5e9;color:white;border-radius:8px;text-decoration:none;\">
              Open Dashboard
            </a>
          </p>
        </div>
      </body>
    </html>
    """.strip()


def send_email_crash_alert(run: RunRecord) -> None:
    cfg = get_alerts_config()
    to_email = cfg.get("email_to", "")
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
    if not to_email or not sendgrid_api_key:
        return

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except Exception:  # noqa: BLE001
        return

    from_email = os.getenv("WATCHAGENT_ALERT_FROM_EMAIL", "alerts@watchagent.dev")
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=f"watchagent crash: {run.agent_name}",
        html_content=_build_html_email(run),
    )
    try:
        SendGridAPIClient(sendgrid_api_key).send(message)
    except Exception:  # noqa: BLE001
        return


def send_crash_alerts(run: RunRecord) -> None:
    send_slack_crash_alert(run)
    send_email_crash_alert(run)
