"""STEP 2 - HubSpot eligibility query for one rep -> candidate pool.

Reproduces the spec's eligibility rules (ENGINE-STANDARDS.md + VERIFICATION-
PROTOCOL.md), scoped to a single rep by owner_id / adr:

  Ownership : hubspot_owner_id == rep.owner  OR  (owner IN rep.ae_owner_ids AND adr == rep.owner)
  No open deal      : hs_num_open_deals == 0
  Dormancy guard    : notes_last_contacted EMPTY (never contacted) OR >= dormancy_days old
  Status exclusions : company_status not in {Blacklist, Not Prospectable*}   (Recycle is fine)
  Not a customer    : lifecyclestage != customer
  Already worked    : company id not in tracker.completed_company_ids
  Location floor    : >= location_floor locations (unknown-from-HubSpot is KEPT for web verify in step 3)

Design note: only the OWNERSHIP branches are pushed to the HubSpot search
(required scoping + biggest reducer, and it keeps us inside HubSpot's 5
filter-group limit). Every other gate is applied in Python from the fetched
properties, where "Not Prospectable: Parent Brand" style contains-matching and
empty-value handling are reliable. This is well within one rep's book size.

NOT decided here (needs deal-association inspection / web verify -> step 3):
  - closed-WON exclusion (closed-LOST is allowed as a warm reconnect)
  - authoritative unit-count verification (FDD + web + Apollo)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from ..config import get_settings
from ..models import CandidateCompany, EligibilityReason
from ..registry import Rep
from .client import HubSpotClient
from .properties import (
    p,
    all_internal_names,
    EXCLUDED_STATUS_VALUES,
    EXCLUDED_LIFECYCLE_VALUES,
    DEPRIORITIZED_STATUS_VALUES,
)


# ------------------------- helpers -------------------------

def _to_int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def parse_hs_datetime(v) -> datetime | None:
    """HubSpot datetime values arrive as epoch-millis strings or ISO-8601.
    Returns tz-aware UTC datetime, or None if empty/unparseable."""
    if v in (None, "", "null"):
        return None
    s = str(v)
    if s.isdigit():  # epoch millis
        return datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _status_excluded(status: str) -> bool:
    s = (status or "").lower()
    return any(bad.lower() in s for bad in EXCLUDED_STATUS_VALUES)


def _status_deprioritized(status: str) -> str | None:
    """Return the matched deprioritized status value, or None."""
    s = (status or "").lower()
    for val in DEPRIORITIZED_STATUS_VALUES:
        if val.lower() in s:
            return val
    return None


def _is_customer(lifecycle: str) -> bool:
    return (lifecycle or "").lower() in {v.lower() for v in EXCLUDED_LIFECYCLE_VALUES}


# ------------------------- query -------------------------

def build_filter_groups(rep: Rep) -> list[dict]:
    """OR of ownership branches. Filters within a group are AND'd by HubSpot."""
    owner_prop, adr_prop = p("hubspot_owner_id"), p("adr")
    groups: list[dict] = [
        {"filters": [{"propertyName": owner_prop, "operator": "EQ", "value": rep.hubspot_owner_id}]}
    ]
    if rep.ae_owner_ids:
        groups.append(
            {
                "filters": [
                    {"propertyName": owner_prop, "operator": "IN", "values": rep.ae_owner_ids},
                    {"propertyName": adr_prop, "operator": "EQ", "value": rep.hubspot_owner_id},
                ]
            }
        )
    return groups


# ------------------------- result of a run -------------------------

@dataclass
class EligibilityRun:
    rep_email: str
    owner_id: str
    fetched: int
    eligible: list[CandidateCompany]
    skipped: list[tuple[str, EligibilityReason]] = field(default_factory=list)  # (company name, reason)

    def summary(self) -> str:
        from collections import Counter
        c = Counter(r for _, r in self.skipped)
        skip_bits = ", ".join(f"{r.value}={n}" for r, n in c.most_common()) or "none"
        return (
            f"[{self.rep_email} / owner {self.owner_id}] "
            f"fetched {self.fetched} -> {len(self.eligible)} eligible; skipped: {skip_bits}"
        )


# ------------------------- main entrypoint -------------------------

async def candidate_pool(
    rep: Rep,
    *,
    completed_company_ids: set[str] | None = None,
    now: datetime | None = None,
    client: HubSpotClient | None = None,
) -> EligibilityRun:
    """Return the full eligible pool for one rep, ordered by the spec's selection
    preference (prior-history/warm first, oldest-dormant first; never-contacted
    fill after). Picking exactly 3 + carryover is the slate step (later)."""
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    completed = completed_company_ids or set()
    cutoff = now - timedelta(days=settings.dormancy_days)

    owns = client or HubSpotClient()
    close = client is None
    try:
        raw = await owns.search(
            "companies",
            filter_groups=build_filter_groups(rep),
            properties=all_internal_names(),
        )
    finally:
        if close:
            await owns.aclose()

    eligible: list[CandidateCompany] = []
    skipped: list[tuple[str, EligibilityReason]] = []

    for obj in raw:
        pr = obj.get("properties", {})
        cid = obj.get("id", "")
        name = pr.get(p("name")) or "(unnamed)"

        open_deals = _to_int(pr.get(p("open_deals")))
        lifecycle = pr.get(p("lifecyclestage")) or ""
        status = pr.get(p("company_status")) or ""
        last_dt = parse_hs_datetime(pr.get(p("notes_last_contacted")))
        # Total Location Count is primary; fall back to Open Locations if empty.
        loc_raw = pr.get(p("location_count"))
        if loc_raw in (None, ""):
            loc_raw = pr.get(p("location_count_fallback"))
        loc = _to_int(loc_raw) if loc_raw not in (None, "") else None
        owner = pr.get(p("hubspot_owner_id")) or ""
        adr = pr.get(p("adr")) or ""

        # --- gates (each explains a skip for the audit trail) ---
        if cid in completed:
            skipped.append((name, EligibilityReason.ALREADY_WORKED)); continue
        if open_deals > 0:
            skipped.append((name, EligibilityReason.HAS_OPEN_DEAL)); continue
        if _is_customer(lifecycle):
            skipped.append((name, EligibilityReason.IS_CUSTOMER)); continue
        if _status_excluded(status):
            skipped.append((name, EligibilityReason.EXCLUDED_STATUS)); continue
        # dormancy: empty last-contacted = never contacted = eligible; else must be >= cutoff old
        if last_dt is not None and last_dt > cutoff:
            skipped.append((name, EligibilityReason.RECENTLY_CONTACTED)); continue
        # location band: skip only if KNOWN and outside [floor, ceiling]; unknown is
        # kept for web verification. Ceiling (max_locations) is off unless set per-rep.
        if loc is not None and loc < rep.effective_location_floor:
            skipped.append((name, EligibilityReason.BELOW_LOCATION_FLOOR)); continue
        if loc is not None and rep.max_locations is not None and loc > rep.max_locations:
            skipped.append((name, EligibilityReason.ABOVE_LOCATION_CEILING)); continue

        reason = (
            EligibilityReason.OWNED_BY_REP
            if owner == rep.hubspot_owner_id
            else EligibilityReason.AE_OWNED_ADR_REP
        )
        deprio = _status_deprioritized(status)
        eligible.append(
            CandidateCompany(
                id=cid,
                name=name,
                domain=pr.get(p("domain")) or "",
                vertical=pr.get(p("vertical")) or "",
                status=status,
                lifecyclestage=lifecycle,
                hubspot_owner_id=owner,
                adr=adr,
                open_deals=open_deals,
                notes_last_contacted=last_dt.date().isoformat() if last_dt else None,
                location_count=loc,
                hubspot_url=f"https://app.hubspot.com/contacts/companies/{cid}",
                matched_reason=reason,
                priority=2 if deprio else 1,
                priority_reason=deprio or "",
                raw=pr,
            )
        )

    eligible.sort(key=_selection_key)
    return EligibilityRun(
        rep_email=rep.email,
        owner_id=rep.hubspot_owner_id,
        fetched=len(raw),
        eligible=eligible,
        skipped=skipped,
    )


def _selection_key(c: CandidateCompany):
    """Ordering: priority 1 before 2 ("No Contacts" is P2); then spec ordering -
    companies WITH prior history first (warm reconnections), oldest-dormant first;
    never-contacted fill the remainder."""
    never = c.notes_last_contacted is None
    return (c.priority, never, c.notes_last_contacted or "9999-12-31")
