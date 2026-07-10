"""Outbound notifications to the TEAM (never to prospects).

Slack via an incoming-webhook URL. If SLACK_WEBHOOK_URL is unset this is a no-op,
so the app runs fine without it (same pattern as the enrichment providers).
"""
from __future__ import annotations

import httpx

from .config import get_settings


def slack_enabled() -> bool:
    return bool(get_settings().slack_webhook_url)


def post_weekly_summary(plans: list[tuple]) -> bool:
    """plans: list of (rep, plan dict). Posts a Friday summary linking to the
    portal's Next Week page. Returns True on success, False on no-op/failure."""
    s = get_settings()
    if not s.slack_webhook_url or not plans:
        return False
    base = s.public_base_url.rstrip("/")
    lines = ["*\U0001F4CB Next week's prospecting slates are ready*"]
    for rep, plan in plans:
        n = sum(len(d.get("accounts", [])) for d in plan.get("days", []))
        lines.append(f"• *{rep.rep_name}* — {n} account(s) planned across the week")
    lines.append(f"\nOpen your preview → {base}/next-week")
    try:
        r = httpx.post(s.slack_webhook_url, json={"text": "\n".join(lines)}, timeout=15)
        return r.status_code < 400
    except httpx.HTTPError:
        return False
