"""Per-rep admin overrides, persisted on the mounted disk.

The base roster comes from HubSpot (reps.json, baked into the image). Anything the
admin tunes in the portal - active, slate_size, auto_slate, team - is saved here as
an overlay, so it survives redeploys AND survives re-running `import-owners` (which
only rewrites the base). registry.load_reps() merges base + these overrides.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from .config import get_settings

_lock = threading.Lock()

# fields the admin may override (whitelist — ignore anything else)
ALLOWED = {"active", "slate_size", "auto_slate", "team", "location_floor", "max_locations"}


def _path() -> Path:
    d = get_settings().data_dir
    d.mkdir(parents=True, exist_ok=True)
    return d / "rep_overrides.json"


def load() -> dict[str, dict]:
    p = _path()
    return json.loads(p.read_text()) if p.exists() else {}


def get(email: str) -> dict:
    return load().get(email.strip().lower(), {})


def set_fields(email: str, **fields) -> None:
    _apply([email], fields)


def set_bulk(emails: list[str], **fields) -> None:
    _apply(emails, fields)


def _apply(emails: list[str], fields: dict) -> None:
    # None means "reset to base/global default" -> drop the key from the overlay.
    clean = {k: v for k, v in fields.items() if k in ALLOWED}
    if not clean:
        return
    with _lock:
        d = load()
        for email in emails:
            e = email.strip().lower()
            cur = dict(d.get(e, {}))
            for k, v in clean.items():
                if v is None:
                    cur.pop(k, None)
                else:
                    cur[k] = v
            if cur:
                d[e] = cur
            else:
                d.pop(e, None)
        _path().write_text(json.dumps(d, indent=2))
