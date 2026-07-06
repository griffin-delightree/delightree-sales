# Delightree Prospecting (Cowork plugin)

A complete ADR prospecting system: six scoped, non-overlapping skills plus a Daily Re-Engagement engine. Drafts only - you review and enroll.

## What's inside
- **global-rules** - safety canon (verification, parent/AE/deal guardrails, 2025 data, drafts only). Every skill checks in with it.
- **recon** - account + contact intel; verifies every contact (live LinkedIn + ZoomInfo + company page).
- **kyle** - account strategy, business case, target champion, objections, call/LinkedIn plan.
- **vinci** - the only writer; A/B emails + LinkedIn messages to the playbook.
- **santa** - personalized gift research (runs only when asked).
- **conductor** - orchestrator; one command = full account package.
- **daily-reengagement** - the 3-account daily slate engine + build script.

## Setup (once per rep)
1. Install this plugin in Claude Cowork (Settings > Capabilities, or open the .plugin file and click Install).
2. Connect your own tools: HubSpot, ZoomInfo, Apollo, Gmail, Google Drive, Slack, and Chrome (logged into LinkedIn).
3. Edit `skills/daily-reengagement/references/config.example.json` -> save as your own `config.json` with YOUR HubSpot owner id, your AE owner ids, your signature, booking link, and home city/area codes.
4. (Optional) Copy the engine reference files into a "Daily Prospecting Engine" folder in your Claude folder and schedule the weekday 7AM run.

## Run it
- Drop a brand name or URL and say "run conductor" for a full account package.
- Or say "run my daily prospecting" / let the scheduled engine surface your 3 each morning.

Everything is drafts only - nothing is ever sent or enrolled automatically.
