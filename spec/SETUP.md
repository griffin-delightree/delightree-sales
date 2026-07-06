# SETUP - stand up your own copy (15-20 min)

Everything here is yours to edit. Nothing sends automatically - all output is drafts.

## 1. Install
Open this `.plugin` file in Claude Cowork and click Install (or Settings > Capabilities > add). You'll see 7 skills appear: global-rules, recon, kyle, vinci, santa, conductor, daily-reengagement, plus rep-profile.

## 2. Connect YOUR tools
In Cowork, connect your own accounts: HubSpot, ZoomInfo, Apollo, Gmail, Google Drive, Slack, and Chrome (stay logged into LinkedIn in that browser - that's how contacts get verified). The plugin uses whatever you connect; it never touches anyone else's data.

## 3. Put in YOUR info (two places)
a) Open the **rep-profile** skill and replace every [FILL IN] - your name, email, HubSpot owner id, your AE(s) + their owner ids, signature, booking link, home city + area codes.
b) In `skills/daily-reengagement/references/config.example.json`, copy it to `config.json` and set the same values (hubspot_owner_id, ae_owner_ids, rep_name, rep_email, signature, booking_link, home_city, home_area_codes).

NOTE: The bundled ENGINE-STANDARDS.md and KNOWLEDGE.md contain Justin's owner ids (e.g., 83840653) as EXAMPLES. Replace them with your own, or rely on your config.json - do not run against Justin's ids.

## 4. (Optional) Stand up the daily engine
Copy the files in `skills/daily-reengagement/references/` into a new "Daily Prospecting Engine" folder in your Claude folder. Rename `tracker.template.json` to `tracker.json`. Then ask Claude to "set up my daily re-engagement to run every weekday at 7AM."

## 5. Use it
- Full account package: paste a brand name or URL and say "run conductor."
- Just research: "run recon on [brand]." Strategy only: "run kyle on [brand]." A single email: "vinci, write to [name] at [brand]." A gift: "santa, gift idea for [name]."
- Daily slate: "run my daily prospecting" (or let the 7AM task do it).

## How the skills fit together (no overlap)
- global-rules = safety gates (verification, parent/AE/deal guardrails, 2025 data, drafts only). Every skill checks in with it.
- recon = data + verified contacts. kyle = strategy + business case + champion. vinci = the only email writer. santa = gifts (only when asked). conductor = orchestrates recon+kyle+vinci into one package. daily-reengagement = the 3-account daily slate.
