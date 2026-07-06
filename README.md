# Delightree Prospecting Portal

Centralized web app that ports the per-rep **delightree-prospecting** Cowork plugin
(`/spec`, read-only) into one server: every rep logs in with Google and sees their own
daily re-engagement slate, scoped to their HubSpot `owner_id`, generated server-side
from a single set of API credentials. Same output and visual as the existing HTML.

**Drafts only. The app never sends, enrolls, or schedules anything. No HubSpot write-back.**

## Status

| Step | What | State |
|------|------|-------|
| 1 | Scaffold + `reps.json` + `.env` config | ✅ done |
| 2 | HubSpot eligibility query → candidate pool | ✅ done (validated live: 165→45 for Justin) |
| 3 | Enrichment + verification layer w/ status flagging | ✅ done (HubSpot contacts + flags; ZoomInfo/Apollo optional) |
| 4 | Vinci drafting via Anthropic API | ✅ wired (activates with a real `ANTHROPIC_API_KEY`) |

> **Vinci playbook is the single source of truth in [`app/playbooks/vinci.md`](delightree-portal/app/playbooks/vinci.md)** — loaded at runtime by `draft.py`, not hardcoded. It drafts A/B emails **plus a LinkedIn cold message** per contact, using the canonical recognizable-brand proof library (Tony Roma's, L&L, Hawaii Fluid Art, Slick City, Beem). To update how emails are written, edit that file (reviewable diff); the next run picks it up. Keep it synced with the Vinci skill.
| 5 | `data.json` assembler → render via ported `build_artifact.py` | ✅ done |
| 6 | FastAPI serving + Google OAuth + rep-scoping | ✅ done (Google OAuth + magic-link) |
| 7 | Weekday 7AM scheduler per active rep | ⬜ next (see cost note below) |
| Deploy | Live HTTPS URL (Docker + Render blueprint) | ✅ ready — see [DEPLOY.md](delightree-portal/DEPLOY.md) |

> **Scheduler cost note:** auto-drafting a slate is ~30-60s + a few cents of Opus per company.
> Running all 43 imported users daily would be expensive and mostly wasteful (most aren't ADRs).
> Before enabling the 7AM job, decide *which* reps auto-run (likely just active ADRs) — that's a
> per-rep flag, not all-hands.

## Run the portal

```bash
source .venv/bin/activate
# 1) generate a slate for a rep (or use the in-app "Run my slate now" button)
PYTHONPATH=. python cli.py slate justin@delightree.com

# 2) start the web app
PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3) mint a login link per rep (no Google OAuth setup needed for testing)
PYTHONPATH=. python cli.py magiclink justin@delightree.com     # or 'all'
#   open the printed http://localhost:8000/auth/magic?token=... in a browser
```

Auth — three ways in, all resolving to a session-scoped rep (`owner_id`), so a rep can never
reach another rep's data via the app's routes:
- **Single team link with per-user passwords (non-Google, current default):** one URL → a
  **"select your HubSpot user" dropdown + per-user portal password** → your scoped portal.
  Passwords are salted PBKDF2 hashes in a **gitignored** `data/credentials.json` (never plaintext,
  never in `reps.json`). Populate the roster from HubSpot with `import-owners`; set passwords with
  `set-password`. ⚠️ Identity is still **self-declared** (the dropdown), gated by the per-user
  password — stronger than a shared code, but not verified SSO.
- **Google OAuth (verified SSO, wired, off by default):** set `GOOGLE_CLIENT_ID`/`SECRET`
  (restricted to `delightree.com`). Flip to this for real identity with zero rework.
- **Signed magic-links:** per-rep URLs for quick individual access.

The rep registry is generated from HubSpot: `python cli.py import-owners` pulls every HubSpot
user into `reps.json` (preserving per-rep config like `ae_owner_ids`, signature, `role`).
`role: "admin"` marks admins for the planned `/admin` cross-team tracking dashboard.
Enrichment/drafting providers (ZoomInfo, Apollo, Anthropic) light up automatically when their keys
are present; the page renders without them.

```bash
# populate all HubSpot users, then set passwords
PYTHONPATH=. python cli.py import-owners
PYTHONPATH=. python cli.py set-password justin@delightree.com 'their-password'   # per user
PYTHONPATH=. python cli.py set-password all 'temp-pass'                          # bulk (testing only)
```

## Layout

```
delightree-portal/
├── spec/                       read-only reference (the extracted plugin; source of truth)
├── app/
│   ├── config.py               env/.env settings (pydantic-settings)
│   ├── registry.py             reps.json loader + Rep model  ← ALL per-rep values live here
│   ├── models.py               CandidateCompany, Contact, VerificationStatus, EligibilityReason
│   └── hubspot/
│       ├── client.py           thin async HubSpot REST client (read-only, paginated search)
│       ├── properties.py       HubSpot property internal-name map (override via env)
│       └── eligibility.py      STEP 2: owner-scoped eligibility → candidate pool
├── tests/test_eligibility.py   offline test of every eligibility gate (no token needed)
├── cli.py                      per-step dev entrypoints
├── reps.json                   the rep registry
├── .env.example                copy to .env
└── requirements.txt
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in HUBSPOT_TOKEN
```

## Testing what exists

```bash
# offline: prove the eligibility gates (no HubSpot needed)
PYTHONPATH=. python tests/test_eligibility.py

# live: list reps, then run step 2 for one rep (needs HUBSPOT_TOKEN in .env)
PYTHONPATH=. python cli.py reps
PYTHONPATH=. python cli.py eligibility justin@delightree.com --limit 20 --verbose
```

## HubSpot property names (verified against the live schema 2026-07-02)

All internal names below were confirmed against the live portal, and the query shape was
smoke-tested against Justin's real book (166 companies, both ownership branches firing).

| logical | display label | internal name | notes |
|---------|---------------|---------------|-------|
| Company owner | "Owner" | `hubspot_owner_id` | standard field |
| ADR | "ADR" | `adr` | enumeration; values *are* owner ids (Justin=`83840653`) |
| Company status | "Company Status" | `company_status` | stored value ≠ label (e.g. `Actively Prospecting` shows "Working") |
| Vertical | "Industry (Mapped)" | `industry_mapped` | 8-category taxonomy |
| Location count | "Total Location Count" | `total_location_count` | primary unit count |
| Location fallback | "Open Locations" | `locations` | used only when primary is empty |

Disqualifying `company_status` values: `Blacklist`, `Not Prospectable: Parent Brand`,
`Not Prospectable: No Contacts` (contains-match on "Not Prospectable"). `Recycle` stays eligible.
Disqualifying `lifecyclestage`: `customer` (Active Customer) + `252674132` (Onboarding Customer).

Anything here can still be overridden without a code change via `HUBSPOT_PROPERTIES_FILE`.

## The `data.json` contract (reverse-engineered from `spec/.../build_artifact.py`)

The renderer (step 5) will reproduce `build_artifact.py`'s markup exactly. Its input shape,
derived from that script's JS, is the target the assembler (step 5) must emit:

```jsonc
{
  "generated": "2026-07-01",           // page date
  "signature": "Best, <rep> | Book a Meeting | Delightree",
  "companies": [{
    "id": "…", "name": "…", "domain": "…", "vertical": "…", "status": "…",
    "last_touch": "2026-01-05 …",      // .split(' ')[0] shown as "Dormant since"
    "hubspot": "https://app.hubspot.com/…",
    "reconnect_ok": false,             // true => "Warm reconnect"; false => "Fresh outreach"
    "proof": "…", "hq_phone": "…", "overview": "…", "flags": "…",
    "contacts": [{
      "tier": "T1|T2|T3", "name": "…", "title": "…", "li": "<linkedin url>",
      "email": "…", "email_note": "…",  // note containing NO EMAIL/BAD/INVALID → renders as warning
      "phone": "…", "hub": "…", "local": false,   // local=true => Denver lunch badge
      "a_subj": "…", "a_body": "…", "b_subj": "…", "b_body": "…"   // omit a_subj => no email block
    }]
  }]
}
```

Per-rep files are namespaced: `data/<owner_id>/{data.json,tracker.json,runs/}`.

## Verification note (important)

The spec's bar is "live LinkedIn in the rep's Chrome is decisive." A server can't do that.
`VerificationStatus` encodes this: server-side checks (ZoomInfo employmentHistory + Apollo +
company/team-page fetch) can reach at most `NOT_LINKEDIN_VERIFIED`, and the renderer will show
a visible **"NOT LINKEDIN-VERIFIED — confirm before outreach"** flag plus a one-click LinkedIn
link for every contact that isn't a logged live-LinkedIn confirmation. No contact is ever
presented as clean-active without it.
