"""Background slate generation.

Slate generation takes minutes (Opus drafts every contact) and makes blocking API
calls. Running it inside a web request blows past the proxy timeout AND blocks the
web worker -> 502. So generation runs in a background thread; the web request just
kicks it off and returns immediately. The dashboard polls until the slate is ready.
"""
from __future__ import annotations

import asyncio
import threading
import time

from ..registry import Rep

_jobs: dict[str, dict] = {}          # owner_id -> {status, started, ended, error}
_lock = threading.Lock()


def status(owner_id: str) -> dict:
    with _lock:
        return dict(_jobs.get(owner_id) or {})


def is_running(owner_id: str) -> bool:
    return status(owner_id).get("status") == "running"


def _run(rep: Rep) -> None:
    from .assemble import build_slate  # local import to avoid a cycle at import time
    try:
        asyncio.run(build_slate(rep))
        result = {"status": "done", "ended": time.time()}
    except Exception as e:  # surface the failure to the dashboard instead of hanging
        result = {"status": "error", "error": str(e)[:300], "ended": time.time()}
    with _lock:
        _jobs[rep.hubspot_owner_id] = {**_jobs.get(rep.hubspot_owner_id, {}), **result}


def start(rep: Rep) -> str:
    """Kick off generation in a background thread. One job per owner at a time."""
    oid = rep.hubspot_owner_id
    with _lock:
        if (_jobs.get(oid) or {}).get("status") == "running":
            return "already_running"
        _jobs[oid] = {"status": "running", "started": time.time()}
    threading.Thread(target=_run, args=(rep,), daemon=True).start()
    return "started"
