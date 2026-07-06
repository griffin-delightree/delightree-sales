"""STEP 5 - assemble the daily slate and render the page.

Pipeline for one rep:
  eligibility pool -> rolling slate of 3 (carryover + fill) -> enrich each ->
  draft each -> PageData -> write data.json + tracker.json + daily_reengagement.html.

Slate/carryover (v1, faithful to the spec's intent):
  - A prior-slate company that is STILL in the eligible pool carries over, keeping
    its original surfaced_date.
  - A prior-slate company that has LEFT the eligible pool (now has an open deal, was
    contacted, became a customer, etc.) is treated as WORKED -> retired to
    completed_company_ids. (This uses eligibility as the "worked" proxy for v1; the
    HubSpot-footprint check - enrollment/contact/deal since surfaced_date - is a
    later refinement.)
  - Fill to 3 from the pool (P1 before P2, oldest-dormant first), excluding the
    current slate and completed ids.
  - Pool floor: if fewer than 3 remain, surface what is available (never loosen the guard).
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..config import get_settings
from ..models import PageData, Company
from ..registry import Rep
from ..hubspot.client import HubSpotClient
from ..hubspot.eligibility import candidate_pool, EligibilityRun
from ..render import render_html
from .. import storage
from .enrich import enrich_company
from .draft import draft_company

SLATE_SIZE = 3


async def build_slate(rep: Rep, *, now: datetime | None = None, draft: bool = True) -> PageData:
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    owner_id = rep.hubspot_owner_id
    tracker = storage.load_tracker(owner_id)
    completed = set(tracker.get("completed_company_ids", []))

    async with HubSpotClient() as client:
        portal_id = get_settings().hubspot_portal_id or await client.get_portal_id()
        run: EligibilityRun = await candidate_pool(
            rep, completed_company_ids=completed, now=now, client=client
        )
        by_id = {c.id: c for c in run.eligible}

        # --- carryover: keep prior-slate ids still eligible; retire the rest ---
        prior = tracker.get("active_slate", [])
        new_slate: list[dict] = []
        newly_completed: list[str] = []
        carried: list[str] = []
        for item in prior:
            cid = item.get("id")
            if cid in by_id:
                new_slate.append({"id": cid, "name": by_id[cid].name,
                                  "surfaced_date": item.get("surfaced_date", today)})
                carried.append(cid)
            elif cid:
                newly_completed.append(cid)

        # --- fill to SLATE_SIZE from the pool (already ordered P1/oldest-first) ---
        in_slate = {i["id"] for i in new_slate}
        for cand in run.eligible:
            if len(new_slate) >= SLATE_SIZE:
                break
            if cand.id in in_slate or cand.id in completed or cand.id in newly_completed:
                continue
            new_slate.append({"id": cand.id, "name": cand.name, "surfaced_date": today})
            in_slate.add(cand.id)

        # --- research the slate (enrich + draft) ---
        companies: list[Company] = []
        for item in new_slate:
            cand = by_id.get(item["id"])
            if not cand:
                continue
            company = await enrich_company(client, rep, cand, portal_id=portal_id)
            if draft:
                company = draft_company(company)
            companies.append(company)

    # --- persist tracker + page ---
    completed |= set(newly_completed)
    tracker["active_slate"] = new_slate
    tracker["completed_company_ids"] = sorted(completed)
    tracker["last_run_date"] = today
    tracker["runs"] = (tracker.get("runs", []) + [{"date": today, "ids": [i["id"] for i in new_slate]}])[-60:]
    if carried:
        tracker["carryover_log"] = tracker.get("carryover_log", []) + [{"date": today, "carried": carried}]

    page = PageData(generated=today, signature=rep.signature, companies=companies)
    streak = int(tracker.get("streak_days", 0)) or 1
    html = render_html(page, streak=streak, rep_name=rep.rep_name)

    storage.save_tracker(owner_id, tracker)
    storage.save_data_json(owner_id, page.to_data_json())
    storage.save_page(owner_id, html)
    return page
