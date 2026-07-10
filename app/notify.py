"""Outbound notifications to the TEAM (never to prospects).

Two Slack modes, preferred in this order:
  1. Bot token (SLACK_BOT_TOKEN): DMs EACH rep their own plan, matched by email
     (rep.email == their Slack email, so no manual ID mapping). Needs scopes
     users:read.email and chat:write.
  2. Incoming webhook (SLACK_WEBHOOK_URL): posts ONE channel summary with a link.
If neither is set this is a no-op, so the app runs fine without Slack.
"""
from __future__ import annotations

from datetime import date

import httpx

from .config import get_settings

SLACK_API = "https://slack.com/api"


def slack_enabled() -> bool:
    s = get_settings()
    return bool(s.slack_bot_token or s.slack_webhook_url)


def _fmt_day(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%a %b %-d")
    except ValueError:
        return iso


def _plan_lines(plan: dict) -> list[str]:
    """The day-by-day body for one rep's plan."""
    lines: list[str] = []
    for day in plan.get("days", []):
        accts = day.get("accounts", [])
        if not accts:
            continue
        names = ", ".join(a.get("name", "") for a in accts)
        lines.append(f"*{_fmt_day(day['date'])}:* {names}")
    return lines


def _dm_rep(token: str, rep, plan: dict, base: str) -> bool:
    """Look the rep up by email and DM them their week. Returns True if sent."""
    try:
        with httpx.Client(timeout=15, headers={"Authorization": f"Bearer {token}"}) as c:
            lk = c.get(f"{SLACK_API}/users.lookupByEmail", params={"email": rep.email}).json()
            if not lk.get("ok"):
                return False
            uid = lk["user"]["id"]
            body = _plan_lines(plan)
            if not body:
                return False
            n = sum(len(d.get("accounts", [])) for d in plan.get("days", []))
            text = (f":clipboard: *Your prospecting slate for next week* "
                    f"(week of {_fmt_day(plan.get('week_of',''))}) — {n} account(s)\n"
                    + "\n".join(body)
                    + f"\n\nOpen the full preview → {base}/next-week")
            r = c.post(f"{SLACK_API}/chat.postMessage",
                       json={"channel": uid, "text": text}).json()
            return bool(r.get("ok"))
    except httpx.HTTPError:
        return False


def _post_webhook(url: str, plans: list, base: str) -> bool:
    lines = ["*\U0001F4CB Next week's prospecting slates are ready*"]
    for rep, plan in plans:
        n = sum(len(d.get("accounts", [])) for d in plan.get("days", []))
        lines.append(f"• *{rep.rep_name}* — {n} account(s) planned")
    lines.append(f"\nOpen your preview → {base}/next-week")
    try:
        r = httpx.post(url, json={"text": "\n".join(lines)}, timeout=15)
        return r.status_code < 400
    except httpx.HTTPError:
        return False


def send_weekly(plans: list) -> dict:
    """plans: list of (rep, plan dict). DMs each rep if a bot token is set; else
    posts one channel summary via webhook; else no-op. Returns a small report."""
    s = get_settings()
    base = s.public_base_url.rstrip("/")
    if not plans:
        return {"mode": "none", "sent": 0}
    if s.slack_bot_token:
        sent = sum(1 for rep, plan in plans if _dm_rep(s.slack_bot_token, rep, plan, base))
        return {"mode": "dm", "sent": sent, "of": len(plans)}
    if s.slack_webhook_url:
        ok = _post_webhook(s.slack_webhook_url, plans, base)
        return {"mode": "webhook", "sent": 1 if ok else 0}
    return {"mode": "none", "sent": 0}
