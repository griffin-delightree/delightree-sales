"""Weekly "next week" planning.

Run on Friday: for each rep, pick the coming week's accounts from their eligible
pool (K = 5 days x slate_size), in the normal priority order, and bucket them
evenly across Mon-Fri. This is ELIGIBILITY ONLY — no Opus drafting — so it's cheap
across the whole team. The full research/drafting still happens each morning for
just that day's accounts (see assemble.build_slate, which reads this plan).

The plan is a snapshot; the morning run re-validates each account is still
eligible and backfills if a day came up short, so a stale pick never surfaces.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from ..registry import Rep
from ..hubspot.eligibility import candidate_pool
from .. import storage

WEEKDAYS = 5  # Mon-Fri


def upcoming_week_dates(now: datetime) -> list[str]:
    """The 5 weekday ISO dates of the NEXT week (Mon-Fri). Running Friday plans
    the immediately-following week; running on a Monday plans the week after."""
    d = now.date()
    days_ahead = (7 - d.weekday()) % 7      # weekday(): Mon=0 .. Sun=6
    if days_ahead == 0:
        days_ahead = 7
    monday = d + timedelta(days=days_ahead)
    return [(monday + timedelta(days=i)).isoformat() for i in range(WEEKDAYS)]


def _acct(c) -> dict:
    return {
        "id": c.id, "name": c.name, "vertical": c.vertical, "status": c.status,
        "domain": c.domain, "last_touch": c.notes_last_contacted or "",
        "priority": c.priority,
    }


async def plan_week(rep: Rep, *, now: datetime | None = None) -> dict:
    """Build and persist the coming week's plan for one rep. Returns the plan."""
    now = now or datetime.now(timezone.utc)
    dates = upcoming_week_dates(now)
    size = rep.slate_size or 3
    tracker = storage.load_tracker(rep.hubspot_owner_id)
    completed = set(tracker.get("completed_company_ids", []))

    run = await candidate_pool(rep, completed_company_ids=completed, now=now)
    picks = run.eligible[: size * WEEKDAYS]

    days = []
    for i, dt in enumerate(dates):
        chunk = picks[i * size:(i + 1) * size]
        days.append({"date": dt, "accounts": [_acct(c) for c in chunk]})

    plan = {
        "week_of": dates[0],
        "generated": now.date().isoformat(),
        "slate_size": size,
        "eligible_total": len(run.eligible),
        "days": days,
    }
    storage.save_week_plan(rep.hubspot_owner_id, plan)
    return plan


def planned_ids_for(owner_id: str, date: str) -> list[str]:
    """Account ids planned for a specific ISO date, or [] if none/no plan."""
    plan = storage.load_week_plan(owner_id)
    if not plan:
        return []
    for day in plan.get("days", []):
        if day.get("date") == date:
            return [a["id"] for a in day.get("accounts", [])]
    return []
