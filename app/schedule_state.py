"""Admin-controlled on/off for the weekday 7AM auto-run, persisted on the disk.

The scheduler job is ALWAYS registered at boot; whether it actually generates
slates when it fires is decided here at fire time. That lets the admin flip the
morning run on/off from the portal with no redeploy and no Render env edit.

First read (no file yet) falls back to SCHEDULE_ENABLED from the env, so existing
deploys keep whatever they were configured with until the admin toggles it.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from .config import get_settings

_lock = threading.Lock()


def _path() -> Path:
    d = get_settings().data_dir
    d.mkdir(parents=True, exist_ok=True)
    return d / "schedule.json"


def is_enabled() -> bool:
    p = _path()
    if not p.exists():
        return get_settings().schedule_enabled     # env is the initial default
    try:
        return bool(json.loads(p.read_text()).get("enabled", False))
    except (ValueError, OSError):
        return get_settings().schedule_enabled


def set_enabled(value: bool) -> bool:
    with _lock:
        _path().write_text(json.dumps({"enabled": bool(value)}, indent=2))
    return bool(value)
