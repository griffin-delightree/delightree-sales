"""STEP 7 - weekday 7AM scheduler.

Pre-generates slates so reps just log in and today's 3 are already there (no waiting
on the ~3-min live draft). Runs IN the web process via APScheduler; gated by env so it
never starts unless you opt in, and only runs reps flagged `auto_slate` in reps.json
(cost control - drafting every one of 43 imported users daily would be wasteful).

Enable in prod: set SCHEDULE_ENABLED=true, and `"auto_slate": true` on the ADRs who
should get a daily slate.
"""
from __future__ import annotations

import asyncio
import logging

from .config import get_settings
from .registry import active_reps

log = logging.getLogger("scheduler")
_scheduler = None


def _run_enabled() -> None:
    """Generate slates for opted-in reps, one at a time (gentle on the box + API).
    Skips entirely unless the admin has the morning run switched ON."""
    from . import schedule_state
    if not schedule_state.is_enabled():
        log.info("scheduler: fired but morning run is OFF; skipping")
        return
    reps = [r for r in active_reps() if getattr(r, "auto_slate", False)]
    log.info("scheduler: generating slates for %d rep(s)", len(reps))
    from .pipeline.assemble import build_slate
    for rep in reps:
        try:
            asyncio.run(build_slate(rep))
            log.info("scheduler: slate done for %s", rep.email)
        except Exception as e:
            log.error("scheduler: slate FAILED for %s: %s", rep.email, e)


def start_scheduler():
    """Register the weekday-morning job ALWAYS. Whether it does anything when it
    fires is decided at fire time by schedule_state.is_enabled(), so the admin can
    flip it on/off from the portal with no redeploy."""
    global _scheduler
    s = get_settings()
    if _scheduler is not None:
        return _scheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    _scheduler = BackgroundScheduler(timezone=s.schedule_tz)
    _scheduler.add_job(
        _run_enabled,
        CronTrigger(day_of_week="mon-fri", hour=s.schedule_hour, minute=0),
        id="daily_slates",
        misfire_grace_time=3600,
    )
    _scheduler.start()
    log.info("scheduler registered: weekday %02d:00 %s (gated by admin toggle)",
             s.schedule_hour, s.schedule_tz)
    return _scheduler
