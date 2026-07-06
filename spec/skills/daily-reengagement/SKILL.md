---
name: daily-reengagement
description: "Daily re-engagement prospecting engine for Delightree ADRs. Surfaces 3 dormant, no-open-deal accounts from your HubSpot book each weekday, fully researched with verified contacts and A/B emails, rendered as a live HTML tracker. Use when the user says 'run my daily prospecting', 'daily re-engagement', 'daily slate', or wants to set up the recurring 7AM run. Reads ENGINE-STANDARDS.md and KNOWLEDGE.md in references, follows the global-rules safety canon, invokes recon/kyle/vinci. Edit config.example.json with your owner id, AE ids, signature, booking link, city. Drafts only."
---

# Daily Re-Engagement Engine

Run a daily slate of 3 dormant, no-open-deal accounts from the rep's HubSpot book, fully researched and drafted, rendered as a live HTML tracker. DRAFTS ONLY.

## First-run setup (do once per rep)
1. Confirm connectors are linked: HubSpot, ZoomInfo, Apollo, Gmail, Google Drive, Slack, and Chrome (logged into LinkedIn for verification).
2. Copy `references/config.example.json` to the rep's project folder as `config.json` and fill in THEIR values: `hubspot_owner_id`, `ae_owner_ids`, `rep_name`, `rep_email`, `signature`, `booking_link`, `home_city`, `home_area_codes`. Do NOT reuse Justin's ids.
3. Copy `references/ENGINE-STANDARDS.md`, `references/KNOWLEDGE.md`, `references/VERIFICATION-PROTOCOL.md`, `references/MASTER-PROSPECTING-STANDARD-v3.md`, `references/build_artifact.py`, and `references/tracker.template.json` (rename to `tracker.json`) into the rep's "Daily Prospecting Engine" folder.
4. Schedule the run for weekday mornings (e.g., 7AM).

## Each run
1. Read ENGINE-STANDARDS.md (rulebook) and KNOWLEDGE.md (ICP/personas/playbook) in references; read tracker.json. The global-rules skill governs all safety gates.
2. SELECT the slate: rolling slate of 3 UNENROLLED companies. Carry over any prior-slate company not yet worked (keep its surfaced_date); fill to 3 with new eligible companies (owner = this rep OR AE-owned with adr = this rep; no open deal; dormant 30+ days or never contacted; not Blacklist/Not Prospectable; not a customer/won; 20+ locations; not already worked). If fewer than 3 remain, surface what is available and notify the rep.
3. RESEARCH all 3 via recon -> kyle -> vinci (santa only if asked), per the Contact and Account Standard v3.
4. WRITE data.json + runs/<date>/<Company>.md; update tracker.json (active_slate, completed ids, carryover_log). Do not touch the page-side streak.
5. BUILD views: run build_artifact.py (writes daily_reengagement.html AND index.html, the bookmarked file). Refresh the Cowork artifact if one exists.
6. Finish with a 3-line summary: today's 3 companies, total emails, total T3 call contacts, warm vs fresh count. DRAFTS ONLY - the rep enrolls.

## Notes
- This engine orchestrates the specialist skills; it does not redefine their rules. Verification, guardrails, and data-recency come from global-rules; ICP/tiering from kyle; the email playbook from vinci; sourcing/verification execution from recon.
- Full eligibility, slate/carryover logic, and output schema live in references/ENGINE-STANDARDS.md.
