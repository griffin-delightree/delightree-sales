#!/usr/bin/env python3
"""Dev CLI for the Delightree prospecting portal.

Each pipeline step gets a subcommand so you can test them in isolation, matching
the build order. Steps beyond eligibility are added as they land.

Usage:
  python cli.py reps                       # list registered reps
  python cli.py eligibility <email>        # STEP 2: candidate pool for one rep (needs HUBSPOT_TOKEN)
  python cli.py eligibility <email> --limit 20 --verbose
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.registry import load_reps, require_rep
from app.hubspot.eligibility import candidate_pool
from app.hubspot.client import HubSpotError


def cmd_reps(_args) -> int:
    reps = load_reps()
    if not reps:
        print("No reps registered. Add entries to reps.json.")
        return 1
    for email, r in reps.items():
        flag = "" if r.active else "  (inactive)"
        print(f"{email:35s} owner={r.hubspot_owner_id:12s} AEs={r.ae_owner_ids}{flag}")
    return 0


async def _run_eligibility(email: str, limit: int | None, verbose: bool) -> int:
    rep = require_rep(email)
    run = await candidate_pool(rep)
    print(run.summary())
    print("-" * 72)
    pool = run.eligible[:limit] if limit else run.eligible
    for i, c in enumerate(pool, 1):
        dorm = c.notes_last_contacted or "never contacted"
        loc = c.location_count if c.location_count is not None else "?"
        prio = "  P2" if c.priority == 2 else ""
        print(f"{i:3d}. {c.name:32.32s} {c.domain:26.26s} "
              f"loc={loc!s:>4} last={dorm:>12} [{c.matched_reason.value}]{prio}")
    if verbose and run.skipped:
        print("-" * 72)
        print("skipped:")
        for name, reason in run.skipped:
            print(f"   - {name:40.40s} {reason.value}")
    return 0


async def _run_slate(email: str, no_draft: bool) -> int:
    from app.pipeline.assemble import build_slate
    from app import storage
    rep = require_rep(email)
    page = await build_slate(rep, draft=not no_draft)
    print(f"Slate for {rep.rep_name} (owner {rep.hubspot_owner_id}): {len(page.companies)} company(ies)")
    for c in page.companies:
        n_emails = sum(1 for ct in c.contacts if ct.has_emails)
        print(f"  - {c.name:34.34s} {len(c.contacts):2d} contacts, {n_emails} with A/B emails "
              f"({'warm' if c.reconnect_ok else 'fresh'})")
    d = storage.owner_dir(rep.hubspot_owner_id)
    print(f"\nWrote: {d}/data.json, tracker.json, daily_reengagement.html")
    return 0


def cmd_slate(args) -> int:
    try:
        return asyncio.run(_run_slate(args.email, args.no_draft))
    except HubSpotError as e:
        print(f"HubSpot error: {e}", file=sys.stderr)
        return 2
    except KeyError as e:
        print(str(e).strip('"'), file=sys.stderr)
        return 2


async def _import_owners() -> int:
    import json
    from app.config import get_settings
    from app.hubspot.client import HubSpotClient
    from app.registry import load_reps

    async with HubSpotClient() as c:
        owners = await c.list_owners()

    path = get_settings().reps_file
    raw = json.loads(path.read_text()) if path.exists() else {}
    # defaults applied only to NEW entries; existing per-rep config is preserved
    created, updated = 0, 0
    for o in owners:
        email = (o.get("email") or "").strip().lower()
        if not email:
            continue
        name = f"{o.get('firstName','')} {o.get('lastName','')}".strip() or email
        oid = str(o.get("id", ""))
        if email in raw and not email.startswith("_"):
            raw[email]["hubspot_owner_id"] = oid       # keep AEs/signature/role/etc.
            raw[email]["rep_name"] = raw[email].get("rep_name") or name
            updated += 1
        else:
            raw[email] = {
                "rep_name": name, "hubspot_owner_id": oid, "ae_owner_ids": [],
                "signature": f"Best, {name} | Book a Meeting | Delightree",
                "booking_link": "", "home_city": "Denver",
                "home_area_codes": ["303", "720", "970"], "active": True, "role": "rep",
            }
            created += 1
    path.write_text(json.dumps(raw, indent=2))
    load_reps.cache_clear()
    print(f"Imported {len(owners)} HubSpot users -> reps.json ({created} new, {updated} updated).")
    print("Set passwords with:  python cli.py set-password <email> <password>   (or 'all')")
    return 0


def cmd_import_owners(_args) -> int:
    from app.hubspot.client import HubSpotError
    try:
        return asyncio.run(_import_owners())
    except HubSpotError as e:
        print(f"HubSpot error: {e}\n(the private app needs scope crm.objects.owners.read)", file=sys.stderr)
        return 2


def cmd_set_password(args) -> int:
    from app.auth import set_password
    from app.registry import load_reps
    if args.email == "all":
        reps = load_reps()
        for email in reps:
            set_password(email, args.password)
        print(f"Set the same password on all {len(reps)} reps. Rotate to per-user before real use.")
    else:
        from app.registry import get_rep
        if get_rep(args.email) is None:
            print(f"No rep '{args.email}' in reps.json (run import-owners first).", file=sys.stderr)
            return 2
        set_password(args.email, args.password)
        print(f"Password set for {args.email}.")
    return 0


def cmd_magiclink(args) -> int:
    from app.auth import make_magic_token
    if args.email == "all":
        from app.registry import active_reps
        reps = active_reps()
    else:
        reps = [require_rep(args.email)]
    for r in reps:
        token = make_magic_token(r.email)
        print(f"{r.email:35s} {args.base}/auth/magic?token={token}")
    return 0


def cmd_eligibility(args) -> int:
    try:
        return asyncio.run(_run_eligibility(args.email, args.limit, args.verbose))
    except HubSpotError as e:
        print(f"HubSpot error: {e}", file=sys.stderr)
        print("Check HUBSPOT_TOKEN in .env and the private-app scopes.", file=sys.stderr)
        return 2
    except KeyError as e:
        print(str(e).strip('"'), file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("reps", help="list registered reps").set_defaults(func=cmd_reps)

    e = sub.add_parser("eligibility", help="candidate pool for one rep (step 2)")
    e.add_argument("email")
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("--verbose", "-v", action="store_true", help="show skipped companies + reasons")
    e.set_defaults(func=cmd_eligibility)

    s = sub.add_parser("slate", help="build + render the daily slate for one rep (steps 3-5)")
    s.add_argument("email")
    s.add_argument("--no-draft", action="store_true", help="skip Anthropic email drafting")
    s.set_defaults(func=cmd_slate)

    m = sub.add_parser("magiclink", help="print a signed login link for a rep (or 'all')")
    m.add_argument("email", help="rep email, or 'all' for every active rep")
    m.add_argument("--base", default="http://localhost:8000", help="base URL of the deployed portal")
    m.set_defaults(func=cmd_magiclink)

    sub.add_parser("import-owners", help="pull every HubSpot user into reps.json").set_defaults(func=cmd_import_owners)

    sp = sub.add_parser("set-password", help="set a rep's portal password (or 'all')")
    sp.add_argument("email", help="rep email, or 'all'")
    sp.add_argument("password")
    sp.set_defaults(func=cmd_set_password)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
