from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import error, request

from .config import get_license_info, get_license_key, machine_id, set_last_validated, set_license_info, set_plan

LICENSE_API_BASE = os.getenv("WATCHAGENT_LICENSE_API", "https://api.watchagent.dev")


@dataclass
class LicenseStatus:
    plan: str
    active: bool
    offline_mode: bool
    message: str


class LicenseError(RuntimeError):
    pass


def _post_json(url: str, payload: dict[str, Any], timeout: int = 8) -> dict[str, Any]:
    req = request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def activate_license(license_key: str) -> LicenseStatus:
    key = license_key.strip()
    if not key:
        raise LicenseError("License key is required")

    payload = {
        "license_key": key,
        "machine_id": machine_id(),
    }
    try:
        data = _post_json(f"{LICENSE_API_BASE}/api/license/activate", payload)
    except error.URLError as exc:
        raise LicenseError(f"Activation failed: {exc}") from exc

    if not data.get("valid"):
        raise LicenseError(str(data.get("message", "License activation failed")))

    plan = str(data.get("plan", "FREE")).upper()
    set_license_info(
        plan=plan,
        license_key=key,
        license_id=str(data.get("license_id", "")),
        expires_at=str(data.get("expires_at", "")),
    )
    return LicenseStatus(plan=plan, active=True, offline_mode=False, message="License activated")


def _within_offline_grace(last_validated_at: str, days: int = 7) -> bool:
    if not last_validated_at:
        return False
    try:
        ts = datetime.fromisoformat(last_validated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    now = datetime.now(timezone.utc)
    return now - ts <= timedelta(days=days)


def get_local_license_status() -> LicenseStatus:
    info = get_license_info()
    has_key = bool(get_license_key())
    if info.plan == "PRO" and has_key:
        return LicenseStatus(plan="PRO", active=True, offline_mode=False, message="Local PRO license")
    return LicenseStatus(plan="FREE", active=False, offline_mode=False, message="Free tier")


def refresh_license_status(force_online: bool = False) -> LicenseStatus:
    info = get_license_info()
    key = get_license_key()
    if not key:
        set_plan("FREE")
        return LicenseStatus(plan="FREE", active=False, offline_mode=False, message="No license key configured")

    payload = {
        "license_key": key,
        "machine_id": machine_id(),
    }

    try:
        data = _post_json(f"{LICENSE_API_BASE}/api/license/validate", payload)
        if data.get("valid"):
            plan = str(data.get("plan", "PRO")).upper()
            set_license_info(
                plan=plan,
                license_key=key,
                license_id=str(data.get("license_id", info.license_id)),
                expires_at=str(data.get("expires_at", info.expires_at)),
            )
            set_last_validated()
            return LicenseStatus(plan=plan, active=True, offline_mode=False, message="License verified")

        set_plan("FREE")
        return LicenseStatus(plan="FREE", active=False, offline_mode=False, message=str(data.get("message", "Invalid license")))
    except Exception as exc:  # noqa: BLE001
        if _within_offline_grace(info.last_validated_at, days=7):
            return LicenseStatus(plan=info.plan or "PRO", active=True, offline_mode=True, message="Offline grace period")
        if force_online:
            raise LicenseError(f"License validation failed: {exc}") from exc
        set_plan("FREE")
        return LicenseStatus(plan="FREE", active=False, offline_mode=False, message="License check failed and grace expired")


def require_pro(feature: str) -> None:
    status = refresh_license_status(force_online=False)
    if status.plan != "PRO" or not status.active:
        raise PermissionError(f"{feature} is available on watchagent Pro. Run: watchagent activate <license-key>")
