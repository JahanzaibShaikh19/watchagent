from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    import stripe  # type: ignore
except Exception:  # noqa: BLE001
    stripe = None

app = FastAPI(title="watchagent-license-server", version="0.1.0")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("WATCHAGENT_FROM_EMAIL", "billing@watchagent.dev")
SUCCESS_URL = os.getenv("WATCHAGENT_SUCCESS_URL", "https://watchagent.dev/success")
CANCEL_URL = os.getenv("WATCHAGENT_CANCEL_URL", "https://watchagent.dev/cancel")
LICENSE_SECRET = os.getenv("WATCHAGENT_LICENSE_SECRET", "dev-secret")

if stripe is not None:
    stripe.api_key = STRIPE_SECRET_KEY

DB_DIR = Path.home() / ".watchagent-license-server"
DB_FILE = DB_DIR / "licenses.db"


def _connect() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS licenses (
                license_key TEXT PRIMARY KEY,
                plan TEXT NOT NULL,
                email TEXT,
                machine_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                activated_at TEXT,
                expires_at TEXT
            )
            """
        )


class LicensePayload(BaseModel):
    license_key: str
    machine_id: str


class CheckoutPayload(BaseModel):
    email: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_license_key(email: str) -> str:
    token = secrets.token_hex(10).upper()
    signature = hmac.new(
        key=LICENSE_SECRET.encode("utf-8"),
        msg=f"{email}:{token}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()[:8].upper()
    return f"WA-PRO-{token}-{signature}"


def _save_license(license_key: str, email: str, plan: str = "PRO") -> None:
    expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO licenses (
                license_key, plan, email, machine_id, status, created_at, activated_at, expires_at
            ) VALUES (?, ?, ?, COALESCE((SELECT machine_id FROM licenses WHERE license_key = ?), ''),
                      COALESCE((SELECT status FROM licenses WHERE license_key = ?), 'issued'),
                      ?, COALESCE((SELECT activated_at FROM licenses WHERE license_key = ?), ''), ?)
            """,
            (license_key, plan, email, license_key, license_key, _now_iso(), license_key, expires_at),
        )


def _send_license_email(to_email: str, license_key: str) -> None:
    if not SENDGRID_API_KEY:
        return
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except Exception:  # noqa: BLE001
        return


def _require_stripe() -> Any:
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe SDK is not installed on this server")
    return stripe

    html = f"""
    <html>
      <body style=\"font-family:Arial,sans-serif;background:#f8fafc;padding:24px;\">
        <div style=\"max-width:640px;margin:0 auto;background:white;border-radius:12px;padding:24px;border:1px solid #cbd5e1;\">
          <h2 style=\"margin-top:0;\">Your watchagent Pro license</h2>
          <p>Thanks for subscribing. Your license key is:</p>
          <pre style=\"font-size:18px;background:#0f172a;color:#e2e8f0;padding:12px;border-radius:8px;\">{license_key}</pre>
          <p>Activate it in terminal:</p>
          <pre style=\"background:#f1f5f9;padding:10px;border-radius:8px;\">watchagent activate {license_key}</pre>
        </div>
      </body>
    </html>
    """.strip()

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject="Your watchagent Pro license key",
        html_content=html,
    )
    try:
        SendGridAPIClient(SENDGRID_API_KEY).send(message)
    except Exception:  # noqa: BLE001
        return


@app.on_event("startup")
def on_startup() -> None:
    initialize()


@app.post("/api/license/validate")
def validate_license(payload: LicensePayload) -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (payload.license_key.strip(),)).fetchone()

    if row is None:
        return {"valid": False, "message": "License not found"}
    if row["status"] not in {"active", "issued"}:
        return {"valid": False, "message": "License is inactive"}

    expires_at = row["expires_at"]
    if expires_at:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_dt:
            return {"valid": False, "message": "License expired"}

    machine_id = str(row["machine_id"] or "")
    if machine_id and machine_id != payload.machine_id:
        return {"valid": False, "message": "License already assigned to another machine"}

    return {
        "valid": True,
        "plan": row["plan"],
        "license_id": row["license_key"],
        "expires_at": row["expires_at"],
    }


@app.post("/api/license/activate")
def activate(payload: LicensePayload) -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (payload.license_key.strip(),)).fetchone()
        if row is None:
            return {"valid": False, "message": "Invalid license key"}

        existing_machine = str(row["machine_id"] or "")
        if existing_machine and existing_machine != payload.machine_id:
            return {"valid": False, "message": "License already used on another machine"}

        conn.execute(
            """
            UPDATE licenses
            SET machine_id = ?, status = 'active', activated_at = ?
            WHERE license_key = ?
            """,
            (payload.machine_id, _now_iso(), payload.license_key.strip()),
        )

    return {
        "valid": True,
        "plan": row["plan"],
        "license_id": row["license_key"],
        "expires_at": row["expires_at"],
        "message": "License activated",
    }


@app.get("/api/license/status")
def license_status(license_key: str) -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (license_key.strip(),)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="License not found")
    return {
        "license_key": row["license_key"],
        "plan": row["plan"],
        "status": row["status"],
        "email": row["email"],
        "machine_id": row["machine_id"],
        "created_at": row["created_at"],
        "activated_at": row["activated_at"],
        "expires_at": row["expires_at"],
    }


@app.post("/api/stripe/checkout")
def stripe_checkout(payload: CheckoutPayload) -> dict[str, str]:
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    stripe_sdk = _require_stripe()

    session = stripe_sdk.checkout.Session.create(
        mode="subscription",
        customer_email=payload.email,
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        metadata={"email": str(payload.email)},
    )
    return {"checkout_url": str(session.url)}


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request) -> JSONResponse:
    stripe_sdk = _require_stripe()
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe_sdk.Webhook.construct_event(payload=payload, sig_header=signature, secret=STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    if event.get("type") == "checkout.session.completed":
        obj = event.get("data", {}).get("object", {})
        email = obj.get("customer_details", {}).get("email") or obj.get("metadata", {}).get("email")
        if email:
            license_key = _generate_license_key(str(email))
            _save_license(license_key=license_key, email=str(email), plan="PRO")
            _send_license_email(to_email=str(email), license_key=license_key)

    return JSONResponse({"received": True})
