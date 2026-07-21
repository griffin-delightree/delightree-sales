"""STEP 3 - Enrichment + verification.

Turns a CandidateCompany into a fully-populated Company:
  - pull associated HubSpot contacts, tier each (size-band matrix + C-suite override),
  - source net-new ICP contacts via ZoomInfo/Apollo IF configured (no-op otherwise),
  - stamp EVERY contact with a VerificationStatus (server ceiling = corroborated;
    never LinkedIn-verified) + the mandatory confirm-before-outreach flag,
  - flag HQ / shared phone lines, tag Denver-metro contacts,
  - attach a vertical-matched customer proof point,
  - assemble a basic overview / flags (the LLM step enriches these when a key exists).

Warm/fresh: defaults to FRESH (the spec's safe default - never imply a relationship
that did not happen). Warm detection from meetings/replies is a later enhancement.
"""
from __future__ import annotations

from collections import Counter

from ..config import get_settings
from ..models import CandidateCompany, Company, Contact
from ..registry import Rep
from .. import zoominfo
from ..tiering import tier_for, TIER_ORDER, Role
from ..verification import assess, label_for, linkedin_url, sources_note
from ..hubspot.client import HubSpotClient, HubSpotError
from ..hubspot.contacts import contacts_for_company, contact_name, contact_email, contact_linkedin

# vertical (industry_mapped) -> SUGGESTED proof point, from Vinci's canonical
# recognizable-brand library (app/playbooks/vinci.md). Vinci applies the
# recognizable-brand rule and may swap; this is only the per-vertical hint.
_PROOF = {
    "Food & Beverage": "L&L Hawaiian Barbecue, the national QSR franchise: 170+ location audits per month via mobile, about 80% less ops complexity.",
    "Fitness & Wellness": "Beem Light Sauna, a wellness franchise using Delightree's AI knowledge base so locations self-serve answers.",
    "Health & Medical": "Beem Light Sauna, a wellness franchise using Delightree's AI knowledge base so locations self-serve answers.",
    "Entertainment": "Slick City, an entertainment franchise that replaced five tools with Delightree and runs repeatable openings across 32+ territories.",
    "Education": "Hawaii Fluid Art, a 200+ location franchise using Delightree for self-serve support and onboarding.",
    "Retail": "Tony Roma's, the national restaurant franchise (different vertical, but a brand you will recognize): real-time launch visibility across openings.",
    "Automotive": "Tony Roma's, the national restaurant franchise (different vertical, but a brand you will recognize): real-time launch visibility across openings.",
    "Business Services": "Slick City, an entertainment franchise (different vertical) that replaced five tools with Delightree across 32+ territories.",
    "Home Services": "Tony Roma's, the national restaurant franchise (different vertical, but a brand you will recognize): real-time launch visibility across openings.",
}
_PROOF_DEFAULT = "Tony Roma's, the national restaurant franchise (different vertical, but a brand you will recognize): real-time launch visibility across openings."


def contact_record_url(portal_id: str, contact_id: str) -> str:
    if portal_id and contact_id:
        return f"https://app.hubspot.com/contacts/{portal_id}/record/0-1/{contact_id}"
    return f"https://app.hubspot.com/contacts/contacts/{contact_id}" if contact_id else ""


def company_record_url(portal_id: str, company_id: str) -> str:
    if portal_id and company_id:
        return f"https://app.hubspot.com/contacts/{portal_id}/record/0-2/{company_id}"
    return f"https://app.hubspot.com/contacts/companies/{company_id}" if company_id else ""


def _digits(phone: str) -> str:
    """Normalize a phone to its national 10-digit form for comparison."""
    d = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return d


def _area_code(phone: str) -> str:
    d = _digits(phone)
    return d[:3] if len(d) >= 10 else ""


def _providers_configured() -> tuple[bool, bool]:
    s = get_settings()
    zoominfo = bool(s.zoominfo_username and s.zoominfo_password)
    apollo = bool(s.apollo_api_key)
    return zoominfo, apollo


async def enrich_company(client: HubSpotClient, rep: Rep, cand: CandidateCompany,
                         portal_id: str = "") -> Company:
    zoominfo_on, apollo_on = _providers_configured()
    hq_phone = (cand.raw.get("phone") or "").strip()

    # 1) pull HubSpot contacts (degrade gracefully if the token lacks contacts scope)
    try:
        raw_contacts = await contacts_for_company(client, cand.id)
        contacts_error = ""
    except HubSpotError as e:
        raw_contacts, contacts_error = [], str(e)

    # 2) build + tier contacts, drop excluded roles
    built: list[Contact] = []
    phone_counter: Counter[str] = Counter()
    for obj in raw_contacts:
        pr = obj.get("properties", {})
        name = contact_name(pr)
        title = pr.get("jobtitle") or ""
        tier, role = tier_for(title, cand.location_count)
        if role is Role.EXCLUDED or tier == "":
            continue

        email = contact_email(pr)
        direct, mobile = (pr.get("phone") or "").strip(), (pr.get("mobilephone") or "").strip()
        shown_phone = mobile or direct
        for ph in (direct, mobile):
            if ph:
                phone_counter[_digits(ph)] += 1

        # verification: server never opens LinkedIn -> ceiling is corroborated/not-verified
        status = assess(linkedin_checked=False, zoominfo_active=None, apollo_active=None)
        li = linkedin_url(contact_linkedin(pr), name, cand.name)

        built.append(
            Contact(
                id=obj.get("id", ""),
                name=name, title=title, tier=tier,
                li=li,
                email=email or "not found",
                email_note=("verified in HubSpot" if email else "no email on file - source or pattern-guess before outreach"),
                phone=shown_phone or "not found",
                hub=(pr.get("hs_lead_status") or pr.get("lifecyclestage") or "").strip(),
                hub_url=contact_record_url(portal_id, obj.get("id", "")),
                verif_status=status,
                verif_label=label_for(status),
                verif_sources=sources_note(zoominfo=zoominfo_on, apollo=apollo_on, company_page=False),
                local=bool(_area_code(shown_phone) in rep.home_area_codes and _area_code(shown_phone) != _area_code(hq_phone)),
            )
        )

    # 2b) net-new contacts from ZoomInfo (gated by ZOOMINFO_SOURCING; fully non-breaking)
    zi_added = 0
    if get_settings().zoominfo_sourcing and zoominfo.configured():
        try:
            seen_names = {c.name.strip().lower() for c in built}
            seen_emails = {c.email.strip().lower() for c in built if c.email and c.email != "not found"}
            for zi in await zoominfo.source_contacts(company_name=cand.name, domain=cand.domain, cap=8):
                nm = zi["name"].strip().lower()
                em = (zi["email"] or "").strip().lower()
                if nm in seen_names or (em and em in seen_emails):
                    continue
                c = _zi_contact(zi, rep, cand, hq_phone, apollo_on)
                if c is None:
                    continue
                built.append(c)
                seen_names.add(nm)
                if em:
                    seen_emails.add(em)
                for ph in (zi["phone"], zi["mobile"]):
                    if ph:
                        phone_counter[_digits(ph)] += 1
                zi_added += 1
        except Exception:
            zi_added = 0

    # 3) phone flagging (HQ main / shared lines), comparing on normalized digits
    hq_digits = _digits(hq_phone)
    for c in built:
        if not c.phone or c.phone == "not found":
            continue
        nd = _digits(c.phone)
        note = ""
        if hq_digits and nd == hq_digits:
            note = " [matches HQ main line - NOT a direct dial]"
        elif phone_counter[nd] >= 2:
            note = " [shared company line - likely not a direct dial]"
        if note:
            c.phone = c.phone + note

    # 4) sort by tier then name
    built.sort(key=lambda c: (TIER_ORDER.get(c.tier, 9), c.name.lower()))

    # 5) overview / flags (basic; LLM step enriches)
    overview = _basic_overview(cand)
    flags = _flags(cand, built, contacts_error, zoominfo_on, apollo_on, zi_added)
    proof = _PROOF.get(cand.vertical, _PROOF_DEFAULT)

    return Company(
        id=cand.id, name=cand.name, domain=cand.domain, vertical=cand.vertical or "Franchise",
        status=cand.status, last_touch=cand.notes_last_contacted or "",
        hubspot=company_record_url(portal_id, cand.id) or cand.hubspot_url,
        reconnect_ok=False, proof=proof, hq_phone=hq_phone,
        overview=overview, flags=flags, contacts=built,
    )


def _zi_contact(zi: dict, rep: Rep, cand: CandidateCompany, hq_phone: str,
                apollo_on: bool) -> Contact | None:
    """Turn a ZoomInfo-sourced contact dict into a tiered, verification-flagged Contact."""
    title = zi.get("title") or ""
    tier, role = tier_for(title, cand.location_count)
    if role is Role.EXCLUDED or tier == "":
        return None
    shown_phone = zi.get("mobile") or zi.get("phone") or ""
    # ZoomInfo corroborated, but the server never opens LinkedIn -> still flagged
    status = assess(linkedin_checked=False, zoominfo_active=True)
    li = linkedin_url(zi.get("linkedin") or "", zi["name"], cand.name)
    email = zi.get("email") or ""
    return Contact(
        id="zi:" + str(zi.get("zi_id") or ""),
        name=zi["name"], title=title, tier=tier, li=li,
        email=email or "not found",
        email_note=("sourced via ZoomInfo" if email else "no email from ZoomInfo - pattern-guess before outreach"),
        phone=shown_phone or "not found",
        hub="net-new (ZoomInfo)", hub_url="",
        verif_status=status, verif_label=label_for(status),
        verif_sources=sources_note(zoominfo=True, apollo=apollo_on, company_page=False),
        local=bool(_area_code(shown_phone) in rep.home_area_codes and _area_code(shown_phone) != _area_code(hq_phone)),
    )


def _basic_overview(c: CandidateCompany) -> str:
    loc = f"{c.location_count} locations" if c.location_count is not None else "an unverified unit count (verify via web/FDD)"
    dormancy = (
        f"Last contacted {c.notes_last_contacted}; dormant, no open deal."
        if c.notes_last_contacted else "Never contacted; treat as a first, fresh touch."
    )
    return (
        f"{c.name} ({c.domain or 'domain unknown'}) is a {c.vertical or 'franchise'} brand with {loc}. "
        f"HubSpot status: {c.status or 'n/a'}. {dormancy}\n\n"
        "Solution hypothesis: at this size a brand typically struggles with consistent execution across units, "
        "manual audits/compliance, and slow new-location openings. Delightree unifies SOPs, task management, "
        "audits, training, and comms in one platform.\n\n"
        "Business case: more location-level visibility, higher audit and training-completion rates, faster "
        "openings, and less HQ support load, without adding corporate headcount.\n\n"
        "Target champion: the Operations leader (VP/Director of Operations or Franchise Support).\n\n"
        "[Add a key to enable the LLM step for a fully-researched 2025 overview.]"
    )


def _flags(c: CandidateCompany, contacts: list[Contact], contacts_error: str,
           zoominfo_on: bool, apollo_on: bool, zi_added: int = 0) -> str:
    bits: list[str] = []
    hub_n = len(contacts) - zi_added
    bits.append(f"{hub_n} contact(s) from HubSpot" + (f" + {zi_added} net-new from ZoomInfo." if zi_added else "."))
    bits.append("ALL contacts are NOT LinkedIn-verified - confirm each on the live profile before outreach.")
    if c.location_count is None:
        bits.append("Unit count unverified - confirm 20+ locations via web/FDD.")
    if c.priority == 2:
        bits.append(f"Deprioritized (P2): {c.priority_reason}.")
    if contacts_error:
        bits.append(f"HubSpot contacts fetch failed ({contacts_error[:80]}) - check token scopes.")
    s = get_settings()
    if s.zoominfo_sourcing and zoominfo.configured():
        if not zi_added:
            bits.append("ZoomInfo sourcing on (no net-new contacts returned for this company).")
    elif not (zoominfo_on and apollo_on):
        missing = [n for n, on in [("ZoomInfo", zoominfo_on), ("Apollo", apollo_on)] if not on]
        bits.append("Net-new sourcing disabled (" + ", ".join(missing) + " not configured).")
    return " ".join(bits)
