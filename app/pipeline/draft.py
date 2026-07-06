"""STEP 4 - Vinci drafting via the Anthropic API (strict tool use).

The Vinci playbook is NOT hardcoded here - it is loaded at runtime from
app/playbooks/vinci.md (the canonical, version-controlled source of truth). To
change how emails are written, edit that file (reviewable diff) and the next run
picks it up.

Output is captured via a STRICT tool schema (not free-text JSON), so the model's
result is always valid structured data - no fragile JSON parsing, no
"unparseable output" failures.

Produces two distinct A/B emails plus a LinkedIn cold message for the top contacts
(6-8 per company, per spec), signature left OFF (the page appends it).

Gated on ANTHROPIC_API_KEY: no key -> contacts render without emails and a flag
notes drafting was skipped. Drafting != cleared for send; the verification flag
stays on every contact regardless.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..config import get_settings
from ..models import Company, Contact
from ..tiering import TIER_ORDER

MAX_EMAIL_CONTACTS = 8   # draft for up to 8 contacts/company; list extras (per spec sec B)
MAX_TOKENS = 16000       # headroom for 8 contacts x (2 emails + LinkedIn); non-streaming is fine

PLAYBOOK_PATH = Path(__file__).resolve().parent.parent / "playbooks" / "vinci.md"

# Strict tool schema: forces the model to return validated structured output.
DRAFT_TOOL = {
    "name": "submit_drafts",
    "description": "Return the drafted A/B emails and LinkedIn message for each contact.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "emails": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "string", "description": "Echo the contact_id exactly as provided."},
                        "a_subj": {"type": "string", "description": "Email A subject, lowercase, <=33 chars."},
                        "a_body": {"type": "string", "description": "Email A body, 90-130 words, plain text, no signature."},
                        "b_subj": {"type": "string", "description": "Email B subject, lowercase, <=33 chars."},
                        "b_body": {"type": "string", "description": "Email B body, 90-130 words, distinct value prop, plain text, no signature."},
                        "li_msg": {"type": "string", "description": "LinkedIn cold message, <=90 words, soft ask, no signature."},
                    },
                    "required": ["contact_id", "a_subj", "a_body", "b_subj", "b_body", "li_msg"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["emails"],
        "additionalProperties": False,
    },
}


@lru_cache
def load_playbook() -> str:
    return PLAYBOOK_PATH.read_text()


def build_system_prompt() -> str:
    """The canonical Vinci playbook + output constraints. Structure is enforced by
    the tool schema, so this only carries the writing rules."""
    return (
        "You are Vinci, Delightree's only outbound copywriter. Follow the playbook below "
        "EXACTLY. Recipient verification and roster sourcing are handled upstream by the app; "
        "you only WRITE. Write PLAIN TEXT only (no markdown, no asterisks). Do NOT include a "
        "signature or sign-off; the page appends it. Return your work by calling the "
        "submit_drafts tool with one entry per contact_id provided.\n\n"
        "=== VINCI PLAYBOOK (canonical source of truth) ===\n" + load_playbook()
    )


def _select_contacts(company: Company) -> list[Contact]:
    ordered = sorted(company.contacts, key=lambda c: (TIER_ORDER.get(c.tier, 9), c.name.lower()))
    return [c for c in ordered if c.verif_status.value != "held_out"][:MAX_EMAIL_CONTACTS]


def _user_prompt(company: Company, contacts: list[Contact]) -> str:
    import json
    roster = [
        {"contact_id": c.id or c.name, "name": c.name, "title": c.title,
         "tier": c.tier, "denver_lunch": c.local}
        for c in contacts
    ]
    return (
        f"Company: {company.name} ({company.domain})\n"
        f"Vertical: {company.vertical}\n"
        f"Suggested proof point (apply the recognizable-brand rule; swap if a better "
        f"recognizable customer fits): {company.proof}\n"
        f"Warm reconnect: {company.reconnect_ok}\n"
        f"Context / solution hypothesis:\n{company.overview}\n\n"
        f"Write A/B emails + a LinkedIn message for each of these {len(contacts)} contacts, "
        f"then call submit_drafts with one entry per contact_id:\n"
        f"{json.dumps(roster, indent=2)}"
    )


def draft_available() -> bool:
    """True only for a real, non-placeholder key."""
    key = (get_settings().anthropic_api_key or "").strip()
    return key.startswith("sk-ant-") and "xxxx" not in key.lower()


def draft_company(company: Company) -> Company:
    """Fill A/B emails + LinkedIn message for the top contacts via strict tool use.
    No-op (with a flag) if no API key or the anthropic package is not installed."""
    if not draft_available():
        company.flags = (company.flags + " Email drafting skipped (no valid ANTHROPIC_API_KEY).").strip()
        return company

    contacts = _select_contacts(company)
    if not contacts:
        return company

    try:
        import anthropic  # lazy import so the app runs without the package until step 4 is used
    except ImportError:
        company.flags = (company.flags + " Email drafting skipped (anthropic package not installed).").strip()
        return company

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=MAX_TOKENS,
            system=build_system_prompt(),
            tools=[DRAFT_TOOL],
            tool_choice={"type": "tool", "name": "submit_drafts"},
            messages=[{"role": "user", "content": _user_prompt(company, contacts)}],
        )
    except anthropic.APIError as e:
        company.flags = (company.flags + f" Email drafting API error: {str(e)[:80]}.").strip()
        return company

    payload = next(
        (b.input for b in resp.content if getattr(b, "type", "") == "tool_use" and b.name == "submit_drafts"),
        None,
    )
    if not payload:
        company.flags = (company.flags + " Email drafting returned no tool output; retry.").strip()
        return company

    by_id = {c.id or c.name: c for c in contacts}
    drafted = 0
    for e in payload.get("emails", []):
        c = by_id.get(e.get("contact_id"))
        if not c:
            continue
        c.a_subj, c.a_body = e.get("a_subj", ""), e.get("a_body", "")
        c.b_subj, c.b_body = e.get("b_subj", ""), e.get("b_body", "")
        c.li_msg = e.get("li_msg", "")
        drafted += 1
    company.flags = (company.flags + f" Drafted A/B emails + LinkedIn messages for {drafted} contact(s).").strip()
    return company
