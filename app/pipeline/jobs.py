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


def _run_add(rep: Rep, company_id: str) -> None:
    from .assemble import add_company
    try:
        asyncio.run(add_company(rep, company_id))
        result = {"status": "done", "ended": time.time()}
    except Exception as e:
        result = {"status": "error", "error": str(e)[:300], "ended": time.time()}
    with _lock:
        _jobs[rep.hubspot_owner_id] = {**_jobs.get(rep.hubspot_owner_id, {}), **result}


def start_add(rep: Rep, company_id: str) -> str:
    """Research one company and append it to the rep's slate, in the background."""
    oid = rep.hubspot_owner_id
    with _lock:
        if (_jobs.get(oid) or {}).get("status") == "running":
            return "already_running"
        _jobs[oid] = {"status": "running", "started": time.time()}
    threading.Thread(target=_run_add, args=(rep, company_id), daemon=True).start()
    return "started"


def start_batch(reps: list[Rep]) -> int:
    """Generate slates for a set of reps sequentially in one background thread
    (same path the 7AM scheduler uses). Returns how many were queued."""
    with _lock:
        for rep in reps:
            _jobs[rep.hubspot_owner_id] = {"status": "running", "started": time.time()}

    def _worker(batch: list[Rep]) -> None:
        for rep in batch:
            _run(rep)                     # sequential; gentle on the box + API

    threading.Thread(target=_worker, args=(list(reps),), daemon=True).start()
    return len(reps)
