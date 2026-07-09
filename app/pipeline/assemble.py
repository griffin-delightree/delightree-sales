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

from datetime import datetime, timezone, timedelta

from ..config import get_settings
from ..models import PageData, Company
from ..registry import Rep
from ..hubspot.client import HubSpotClient, HubSpotError
from ..hubspot.eligibility import (
    candidate_pool, EligibilityRun, to_candidate, company_owner_matches,
    build_filter_groups, _to_int, parse_hs_datetime,
)
from ..hubspot.properties import p, all_internal_names
from ..render import render_html, render_data
from .. import storage
from .enrich import enrich_company
from .draft import draft_company

SLATE_SIZE = 3


class NotOwned(Exception):
    """Raised when a rep tries to add a company outside their own book."""


async def build_slate(rep: Rep, *, now: datetime | None = None, draft: bool = True) -> PageData:
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    size = rep.slate_size or SLATE_SIZE       # per-rep, admin-tunable (default 3)
    owner_id = rep.hubspot_owner_id
    tracker = storage.load_tracker(owner_id)
    completed = set(tracker.get("completed_company_ids", []))

    async with HubSpotClient() as client:
        portal_id = get_settings().hubspot_portal_id or await client.get_portal_id()
        run: EligibilityRun = await candidate_pool(
            rep, completed_company_ids=completed, now=now, client=client
        )
        by_id = {c.id: c for c in run.eligible}

        # --- assemble the slate: pinned (manual) first, then carryover, then fill ---
        prior = tracker.get("active_slate", [])
        pinned = tracker.get("pinned", [])
        new_slate: list[dict] = []
        newly_completed: list[str] = []
        carried: list[str] = []
        seen: set[str] = set()

        # (1) manual adds are ALWAYS kept and never auto-retired by the eligibility proxy
        for pn in pinned:
            cid = pn.get("id")
            if not cid or cid in seen:
                continue
            new_slate.append({"id": cid, "name": pn.get("name", ""),
                              "surfaced_date": pn.get("surfaced_date", today), "manual": True})
            seen.add(cid); carried.append(cid)

        # (2) carry prior-slate ids still eligible; retire the rest as worked
        for item in prior:
            cid = item.get("id")
            if not cid or cid in seen:
                continue
            if cid in by_id:
                new_slate.append({"id": cid, "name": by_id[cid].name,
                                  "surfaced_date": item.get("surfaced_date", today)})
                seen.add(cid); carried.append(cid)
            else:
                newly_completed.append(cid)

        # (3) fill to the rep's slate size from the pool (ordered P1/oldest-first)
        for cand in run.eligible:
            if len(new_slate) >= size:
                break
            if cand.id in seen or cand.id in completed or cand.id in newly_completed:
                continue
            new_slate.append({"id": cand.id, "name": cand.name, "surfaced_date": today})
            seen.add(cand.id)

        # --- research the slate (enrich + draft) ---
        companies: list[Company] = []
        for item in new_slate:
            cand = by_id.get(item["id"])
            if cand is None:
                # pinned/manual company not in the eligible pool -> fetch it directly
                # (bypasses the gates; the rep explicitly asked for it). Still owner-scoped.
                try:
                    obj = await client.get_company(item["id"], all_internal_names())
                except HubSpotError:
                    continue
                if not company_owner_matches(obj.get("properties", {}), rep):
                    continue
                cand = to_candidate(obj, rep)
            company = await enrich_company(client, rep, cand, portal_id=portal_id)
            if draft:
                company = draft_company(company)
            company.manual = bool(item.get("manual"))
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


# --------------------------- manual "add company" ---------------------------

async def search_owned(rep: Rep, q: str, *, limit: int = 25) -> list[dict]:
    """Free-text search over the rep's OWN companies (ownership-scoped, no
    eligibility gates), for the manual add picker. Annotates each hit with why it
    would not have auto-surfaced, so the rep knows what they're overriding."""
    q = (q or "").strip()
    if not q:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=get_settings().dormancy_days)
    async with HubSpotClient() as client:
        raw = await client.search(
            "companies",
            filter_groups=build_filter_groups(rep),
            properties=all_internal_names(),
            query=q,
            max_results=limit,
        )
    out: list[dict] = []
    for obj in raw:
        pr = obj.get("properties", {})
        loc_raw = pr.get(p("location_count"))
        if loc_raw in (None, ""):
            loc_raw = pr.get(p("location_count_fallback"))
        loc = _to_int(loc_raw) if loc_raw not in (None, "") else None
        last_dt = parse_hs_datetime(pr.get(p("notes_last_contacted")))
        open_deals = _to_int(pr.get(p("open_deals")))
        notes: list[str] = []
        if open_deals > 0:
            notes.append("open deal")
        if last_dt and last_dt > cutoff:
            notes.append("contacted recently")
        if loc is not None and loc < rep.effective_location_floor:
            notes.append(f"under {rep.effective_location_floor} locations")
        out.append({
            "id": obj.get("id", ""),
            "name": pr.get(p("name")) or "(unnamed)",
            "domain": pr.get(p("domain")) or "",
            "locations": loc,
            "status": pr.get(p("company_status")) or "",
            "last_touch": last_dt.date().isoformat() if last_dt else "",
            "notes": notes,
        })
    return out


def _pin(tracker: dict, cid: str, name: str, today: str) -> None:
    pinned = tracker.get("pinned", [])
    if cid not in {x.get("id") for x in pinned}:
        pinned.append({"id": cid, "name": name, "surfaced_date": today, "manual": True})
    tracker["pinned"] = pinned
    slate = tracker.get("active_slate", [])
    if cid not in {x.get("id") for x in slate}:
        slate.append({"id": cid, "name": name, "surfaced_date": today, "manual": True})
    tracker["active_slate"] = slate


async def add_company(rep: Rep, company_id: str, *, draft: bool = True,
                      now: datetime | None = None, enforce_owner: bool = True) -> Company:
    """Research one company and append it to `rep`'s slate, pinned. Incremental:
    enriches+drafts ONLY this company, appends to data.json, re-renders.

    enforce_owner=True (rep self-serve add): raises NotOwned unless the company is
    in the rep's book — the scoping guard. enforce_owner=False is used ONLY by the
    admin assign path (an unowned ICP account has no owner to match), where the
    caller is already gated to admins."""
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    owner_id = rep.hubspot_owner_id

    async with HubSpotClient() as client:
        portal_id = get_settings().hubspot_portal_id or await client.get_portal_id()
        obj = await client.get_company(company_id, all_internal_names())
        if enforce_owner and not company_owner_matches(obj.get("properties", {}), rep):
            raise NotOwned(f"company {company_id} is not in {rep.email}'s book")
        cand = to_candidate(obj, rep)
        company = await enrich_company(client, rep, cand, portal_id=portal_id)
        if draft:
            company = draft_company(company)
        company.manual = True

    # merge into the existing page payload (replace if already present, else append)
    data = storage.load_data_json(owner_id) or {
        "generated": today, "signature": rep.signature, "companies": []
    }
    entry = PageData(generated=today, signature=rep.signature,
                     companies=[company]).to_data_json()["companies"][0]
    data["companies"] = [c for c in data.get("companies", []) if c.get("id") != company.id]
    data["companies"].append(entry)

    tracker = storage.load_tracker(owner_id)
    _pin(tracker, company.id, company.name, today)
    streak = int(tracker.get("streak_days", 0)) or 1

    storage.save_data_json(owner_id, data)
    storage.save_page(owner_id, render_data(data, streak=streak, rep_name=rep.rep_name))
    storage.save_tracker(owner_id, tracker)
    return company


def remove_company(rep: Rep, company_id: str) -> None:
    """Un-pin a manually added company and drop it from today's page. Does not
    touch HubSpot. If it also qualifies on its own, tomorrow's run may re-add it."""
    owner_id = rep.hubspot_owner_id
    tracker = storage.load_tracker(owner_id)
    tracker["pinned"] = [x for x in tracker.get("pinned", []) if x.get("id") != company_id]
    tracker["active_slate"] = [x for x in tracker.get("active_slate", []) if x.get("id") != company_id]
    data = storage.load_data_json(owner_id)
    if data:
        data["companies"] = [c for c in data.get("companies", []) if c.get("id") != company_id]
        streak = int(tracker.get("streak_days", 0)) or 1
        storage.save_data_json(owner_id, data)
        storage.save_page(owner_id, render_data(data, streak=streak, rep_name=rep.rep_name))
    storage.save_tracker(owner_id, tracker)
