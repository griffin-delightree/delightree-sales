"""Offline test of the step-2 eligibility gates with synthetic HubSpot data.

No live token needed: a fake client returns canned company objects, and we assert
each spec rule (open deal, dormancy, status, customer, location floor, tracker,
ownership-branch tagging + selection ordering) does the right thing.

Run:  python -m pytest tests/ -q     (or)     python tests/test_eligibility.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.registry import Rep
from app.hubspot import eligibility as E
from app.hubspot.properties import p
from app.models import EligibilityReason

NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)


def company(cid, name, *, owner="83840653", adr="", open_deals="0", lifecycle="lead",
            status="", last_contacted=None, locations="50", open_locations=None):
    """Build a raw HubSpot-style object using the configured internal names."""
    props = {
        p("name"): name, p("domain"): f"{name.lower()}.com",
        p("hubspot_owner_id"): owner, p("adr"): adr,
        p("open_deals"): open_deals, p("lifecyclestage"): lifecycle,
        p("company_status"): status, p("vertical"): "Food & Beverage",
        p("location_count"): locations,
    }
    if open_locations is not None:
        props[p("location_count_fallback")] = open_locations
    if last_contacted is not None:
        props[p("notes_last_contacted")] = last_contacted
    return {"id": cid, "properties": props}


class FakeClient:
    def __init__(self, results):
        self._results = results
    async def search(self, *a, **k):
        return self._results
    async def aclose(self):
        pass


REP = Rep(
    email="justin@delightree.com", rep_name="Justin Hoke",
    hubspot_owner_id="83840653", ae_owner_ids=["91491264", "63616141"],
    signature="Best, Justin Hoke | Book a Meeting | Delightree",
    home_area_codes=["303"],
)

# epoch-millis and ISO both exercised
RECENT_ISO = "2026-06-20T10:00:00Z"      # 11 days before NOW -> too recent
OLD_ISO = "2026-01-05T10:00:00Z"         # ~6 months -> dormant, eligible
OLDER_EPOCH = str(int(datetime(2025, 3, 1, tzinfo=timezone.utc).timestamp() * 1000))


def run(results, completed=None):
    fake = FakeClient(results)
    return asyncio.run(
        E.candidate_pool(REP, completed_company_ids=completed or set(), now=NOW, client=fake)
    )


def test_gates():
    results = [
        company("1", "EligibleOwned", owner="83840653", last_contacted=OLD_ISO),
        company("2", "EligibleAE", owner="91491264", adr="83840653", last_contacted=OLDER_EPOCH),
        company("3", "NeverContacted", owner="83840653", last_contacted=None),
        company("4", "HasOpenDeal", open_deals="2", last_contacted=OLD_ISO),
        company("5", "TooRecent", last_contacted=RECENT_ISO),
        company("6", "IsCustomer", lifecycle="customer", last_contacted=OLD_ISO),
        company("7", "Blacklisted", status="Blacklist", last_contacted=OLD_ISO),
        company("8", "ParentBrand", status="Not Prospectable: Parent Brand", last_contacted=OLD_ISO),
        company("9", "TooSmall", locations="12", last_contacted=OLD_ISO),
        company("10", "AlreadyWorked", last_contacted=OLD_ISO),
        company("11", "UnknownLocs", locations="", last_contacted=OLD_ISO),  # kept for web verify
        # primary total_location_count empty -> falls back to Open Locations = 40 -> eligible
        company("12", "FallbackLocs", locations="", open_locations="40", last_contacted=OLD_ISO),
        # fallback also under floor -> skipped
        company("13", "FallbackSmall", locations="", open_locations="5", last_contacted=OLD_ISO),
        company("14", "OnboardingCust", lifecycle="252674132", last_contacted=OLD_ISO),
        # eligible but deprioritized to P2 (not excluded)
        company("15", "NoContactsStatus", status="Not Prospectable: No Contacts", last_contacted=OLD_ISO),
    ]
    r = run(results, completed={"10"})
    got = {c.id: c for c in r.eligible}

    assert set(got) == {"1", "2", "3", "11", "12", "15"}, f"eligible ids wrong: {sorted(got)}"
    assert got["1"].matched_reason == EligibilityReason.OWNED_BY_REP
    assert got["2"].matched_reason == EligibilityReason.AE_OWNED_ADR_REP
    assert got["11"].location_count is None       # unknown kept
    assert got["12"].location_count == 40         # backfilled from Open Locations
    assert got["15"].priority == 2 and got["15"].priority_reason == "Not Prospectable: No Contacts"
    assert got["1"].priority == 1                 # normal companies stay P1
    reasons = {name: reason for name, reason in r.skipped}
    assert reasons["HasOpenDeal"] == EligibilityReason.HAS_OPEN_DEAL
    assert reasons["TooRecent"] == EligibilityReason.RECENTLY_CONTACTED
    assert reasons["IsCustomer"] == EligibilityReason.IS_CUSTOMER
    assert reasons["OnboardingCust"] == EligibilityReason.IS_CUSTOMER
    assert reasons["Blacklisted"] == EligibilityReason.EXCLUDED_STATUS
    assert reasons["ParentBrand"] == EligibilityReason.EXCLUDED_STATUS
    assert "NoContactsStatus" not in reasons      # no longer skipped -> now eligible P2
    assert reasons["TooSmall"] == EligibilityReason.BELOW_LOCATION_FLOOR
    assert reasons["FallbackSmall"] == EligibilityReason.BELOW_LOCATION_FLOOR
    assert reasons["AlreadyWorked"] == EligibilityReason.ALREADY_WORKED
    print("test_gates OK")


def test_selection_ordering():
    # contacted (warm) before never-contacted; oldest-dormant first among contacted;
    # P2 ("No Contacts") sinks below all P1 regardless of how old it is.
    results = [
        company("never", "Never", last_contacted=None),
        company("recent-dormant", "RecentDormant", last_contacted=OLD_ISO),      # 2026-01
        company("oldest", "Oldest", last_contacted=OLDER_EPOCH),                 # 2025-03
        company("p2-old", "P2Old", status="Not Prospectable: No Contacts",
                last_contacted=OLDER_EPOCH),                                     # oldest, but P2
    ]
    r = run(results)
    order = [c.id for c in r.eligible]
    assert order == ["oldest", "recent-dormant", "never", "p2-old"], order
    print("test_selection_ordering OK")


if __name__ == "__main__":
    test_gates()
    test_selection_ordering()
    print("\nall eligibility tests passed")
