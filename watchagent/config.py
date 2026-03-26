from __future__ import annotations

import base64
import getpass
import hashlib
import json
import itertools
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".watchagent"
CONFIG_FILE = CONFIG_DIR / "config.json"
OFFLINE_GRACE_DAYS = 7


@dataclass
class LicenseInfo:
    plan: str = "FREE"
    encrypted_key: str = ""
    license_id: str = ""
    last_validated_at: str = ""
    expires_at: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_config() -> dict[str, Any]:
    return {
        "license": {
            "plan": "FREE",
            "encrypted_key": "",
            "license_id": "",
            "last_validated_at": "",
            "expires_at": "",
            "offline_grace_days": OFFLINE_GRACE_DAYS,
        },
        "alerts": {
            "slack_webhook": "",
            "email_to": "",
        },
        "team": {
            "members": [],
        },
        "meta": {
            "updated_at": _now_iso(),
        },
    }


def load_config() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        cfg = _default_config()
        save_config(cfg)
        return cfg

    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raw = _default_config()

    merged = _default_config()
    merged.update(raw)
    merged["license"] = {**_default_config()["license"], **raw.get("license", {})}
    merged["alerts"] = {**_default_config()["alerts"], **raw.get("alerts", {})}
    merged["team"] = {**_default_config()["team"], **raw.get("team", {})}
    return merged


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg.setdefault("meta", {})
    cfg["meta"]["updated_at"] = _now_iso()
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=True), encoding="utf-8")


def machine_id() -> str:
    value = f"{socket.gethostname()}::{getpass.getuser()}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _encryption_key() -> bytes:
    seed = f"watchagent::{machine_id()}::v1".encode("utf-8")
    return hashlib.sha256(seed).digest()


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    raw = value.encode("utf-8")
    key = _encryption_key()
    cipher = bytes((byte ^ key_byte) for byte, key_byte in zip(raw, itertools.cycle(key)))
    return base64.urlsafe_b64encode(cipher).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        cipher = base64.urlsafe_b64decode(value.encode("utf-8"))
        key = _encryption_key()
        raw = bytes((byte ^ key_byte) for byte, key_byte in zip(cipher, itertools.cycle(key)))
        return raw.decode("utf-8")
    except Exception:  # noqa: BLE001
        return ""


def set_license_info(plan: str, license_key: str, license_id: str = "", expires_at: str = "") -> None:
    cfg = load_config()
    cfg["license"]["plan"] = plan.upper()
    cfg["license"]["encrypted_key"] = encrypt_secret(license_key)
    cfg["license"]["license_id"] = license_id
    cfg["license"]["last_validated_at"] = _now_iso()
    cfg["license"]["expires_at"] = expires_at
    save_config(cfg)


def set_plan(plan: str) -> None:
    cfg = load_config()
    cfg["license"]["plan"] = plan.upper()
    save_config(cfg)


def set_last_validated() -> None:
    cfg = load_config()
    cfg["license"]["last_validated_at"] = _now_iso()
    save_config(cfg)


def get_license_key() -> str:
    cfg = load_config()
    return decrypt_secret(str(cfg.get("license", {}).get("encrypted_key", "")))


def get_license_info() -> LicenseInfo:
    cfg = load_config().get("license", {})
    return LicenseInfo(
        plan=str(cfg.get("plan", "FREE") or "FREE").upper(),
        encrypted_key=str(cfg.get("encrypted_key", "")),
        license_id=str(cfg.get("license_id", "")),
        last_validated_at=str(cfg.get("last_validated_at", "")),
        expires_at=str(cfg.get("expires_at", "")),
    )


def set_slack_webhook(url: str) -> None:
    cfg = load_config()
    cfg["alerts"]["slack_webhook"] = url.strip()
    save_config(cfg)


def set_alert_email(address: str) -> None:
    cfg = load_config()
    cfg["alerts"]["email_to"] = address.strip()
    save_config(cfg)


def get_alerts_config() -> dict[str, str]:
    alerts = load_config().get("alerts", {})
    return {
        "slack_webhook": str(alerts.get("slack_webhook", "")),
        "email_to": str(alerts.get("email_to", "")),
    }


def get_team_members() -> list[str]:
    team = load_config().get("team", {})
    members = team.get("members", [])
    if not isinstance(members, list):
        return []
    return [str(member) for member in members]


def add_team_member(email: str, max_members: int = 5) -> list[str]:
    clean = email.strip().lower()
    members = get_team_members()
    if clean in members:
        return members
    if len(members) >= max_members:
        raise ValueError(f"Team limit reached ({max_members} members)")
    members.append(clean)
    cfg = load_config()
    cfg["team"]["members"] = members
    save_config(cfg)
    return members


def remove_team_member(email: str) -> list[str]:
    clean = email.strip().lower()
    members = [member for member in get_team_members() if member != clean]
    cfg = load_config()
    cfg["team"]["members"] = members
    save_config(cfg)
    return members
