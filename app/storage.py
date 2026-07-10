"""Per-rep persistence, namespaced by HubSpot owner_id under DATA_DIR.

    data/<owner_id>/data.json                 last rendered payload
    data/<owner_id>/tracker.json              slate / carryover / streak state
    data/<owner_id>/daily_reengagement.html   the rendered page served to the rep

Filesystem for v1 (swap for Postgres behind this module later). All access is by
owner_id, which is the scoping key - a request can only ever read its own rep's dir.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import get_settings

_TRACKER_TEMPLATE = {
    "streak_days": 0,
    "last_run_date": None,
    "completed_company_ids": [],
    "runs": [],
    "active_slate": [],
    "carryover_log": [],
}


def owner_dir(owner_id: str) -> Path:
    d = get_settings().data_dir / str(owner_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _p(owner_id: str, name: str) -> Path:
    return owner_dir(owner_id) / name


def load_tracker(owner_id: str) -> dict:
    path = _p(owner_id, "tracker.json")
    if path.exists():
        t = json.loads(path.read_text())
        for k, v in _TRACKER_TEMPLATE.items():
            t.setdefault(k, v if not isinstance(v, list) else list(v))
        return t
    return {k: (list(v) if isinstance(v, list) else v) for k, v in _TRACKER_TEMPLATE.items()}


def save_tracker(owner_id: str, tracker: dict) -> None:
    _p(owner_id, "tracker.json").write_text(json.dumps(tracker, indent=2))


def save_data_json(owner_id: str, data: dict) -> None:
    _p(owner_id, "data.json").write_text(json.dumps(data, indent=2))


def load_data_json(owner_id: str) -> dict | None:
    path = _p(owner_id, "data.json")
    return json.loads(path.read_text()) if path.exists() else None


def save_week_plan(owner_id: str, plan: dict) -> None:
    _p(owner_id, "week_plan.json").write_text(json.dumps(plan, indent=2))


def load_week_plan(owner_id: str) -> dict | None:
    path = _p(owner_id, "week_plan.json")
    return json.loads(path.read_text()) if path.exists() else None


def save_page(owner_id: str, html: str) -> None:
    _p(owner_id, "daily_reengagement.html").write_text(html)


def load_page(owner_id: str) -> str | None:
    path = _p(owner_id, "daily_reengagement.html")
    return path.read_text() if path.exists() else None
