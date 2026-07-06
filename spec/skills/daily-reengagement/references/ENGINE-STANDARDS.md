> SHARED TEMPLATE: any owner ids / names below (e.g., Justin = 83840653) are EXAMPLES. Replace with your own ids from config.json / rep-profile before running. Run-history notes are Justin's; reference only.

# Daily Re-Engagement Engine - Standards (Rulebook)
_Owner: Justin Hoke (justin@delightree.com) · Updated: 2026-06-18 · Read KNOWLEDGE.md for full ICP/persona/email detail._

The weekday 7AM scheduled task embeds these rules. Always read KNOWLEDGE.md too.

> ⚑ CANONICAL CONTACT STANDARD (per Justin, 2026-06-24): **VERIFICATION-PROTOCOL.md** governs every contact this engine returns (3-source active-employment check with LIVE LinkedIn decisive, exhaustive ICP coverage with net-new sourcing, and full prior-deal/conversation history). It SUPERSEDES any contact rule below that conflicts with it. Read it every run.


## DAILY POOL (pick exactly 3)
Eligibility (ALL true):
1. Ownership: hubspot_owner_id = 83840653 (Justin) OR (owner IN [Ben 91491264, Keegan 63616141, Ashley 89337815] AND adr = "83840653").
2. No active deal: hs_num_open_deals = 0.
3. Recency guard: notes_last_contacted is EMPTY (never contacted - eligible) OR 30+ days old. (notes_last_contacted excludes marketing emails.) No minimum dormancy beyond 30 days.
4. Exclude company_status "Blacklist" and "Not Prospectable: Parent Brand". "Recycle" is fine.
5. Skip company_ids already in tracker.json.
Selection: prefer companies WITH prior history (warm reconnections), oldest-dormant first; fill remainder with never-contacted. Exactly 3/day, weekdays.

## RECONNECTION, NOT COLD
Pull past context (notes, meetings, email subjects, closed-lost deals) and reference REAL history. Never invent a demo/meeting. Never-contacted = treat as first touch (still fine).

## TIERING (High=T1 / Moderate=T2 / Low=T3, BY LOCATION BAND) - from Building Target Prospect Lists
- 10-25 loc: T1 = CEO/Founder, Operations. T2 = Training, Support, FBCs. T3 = Franchise Dev, HR, Finance.
- 26-50 loc: T1 = Operations, Support, Compliance, CEO/Founder. T2 = Training, FBCs, District/Regional VPs, Growth, CSO/CGO/CTO. T3 = Franchise Dev, HR, Finance.
- 50+ loc: T1 = Operations, Support, Compliance, PLUS any C-Suite/Founder/President (ALWAYS T1, per C-Suite override). T2 = Training, Finance, FBCs, District/Regional VPs, Growth. T3 = Franchise Dev, HR, Finance.
Determine the band from current location count (verify via web). Franchise Dev/HR/Finance always T3. COVERAGE: include EVERY ICP-fitting HQ contact, NO cap - see VERIFICATION-PROTOCOL.md sec 2 (no more 'aim 4-7'; trimming the list is not allowed).

## CONTACTS & OUTPUT
- Verify each T1/T2 ACTIVE via ZoomInfo (FULL_MATCH elsewhere = departed -> DO NOT EMAIL block + find replacement).
- T1 + T2: write A/B emails (two distinct value props), NO LIMIT on count. Source a missing email via ZoomInfo/Apollo; if none, draft anyway + flag a verified pattern guess.
- T3 = CALL LIST ONLY: name, role, phone(s), LinkedIn. NO email written. SOURCE phone numbers (direct + mobile) via ZoomInfo if missing. Show ALL numbers found, no DNC filtering (just label DNC if known).
- LinkedIn hyperlink on every contact (verified or labeled search link).
- Auto-match a CUSTOMER PROOF POINT by vertical (KNOWLEDGE.md proof list, or HubSpot lifecyclestage=customer in same industry); name it in Email A.
- Drafts only - never enroll. Flag active sequences [ACTIVE SEQUENCE - DO NOT CONTACT], bad emails, duplicates, stale titles.

## EMAIL STYLE (Delightree Email Playbook - see KNOWLEDGE.md sec 5)
> RECOGNIZABLE-BRAND RULE (per Justin, 2026-06-25): when naming a customer proof point, PREFER Delightree's most recognizable customers (match the prospect's vertical first: Tony Roma's & L&L = restaurants, The Picklr & BodyBar = fitness, MassageLuXe & Next Health = health/personal care, Oxi Fresh & PMI = home services, Sandbox VR & Slick City = entertainment, Creative World School = childcare; full list in KNOWLEDGE.md sec 4) even across industries, and NOTE the different vertical in the line. Recognizable national brand > niche same-vertical. Real customers only. See KNOWLEDGE.md sec 4.
90-130 words. 6-part anatomy. ONE sourced third-party stat (IFA/FRANdata/Black Box/Cornell/Gong). "Delightree" only in the CTA. 3 lowercase subjects <=33 chars. CTA by seniority. Human tone, NO em dashes, NO AI tells. Lead with opportunity. Signature: "Best, Justin Hoke | Book a Meeting | Delightree".

## OUTPUT FORMAT (per company) - matches Steak 'n Shake run
Header (name/domain/vertical/status/Updated/HubSpot link/last touch) -> DEPARTED block (if any) -> COMPANY OVERVIEW (300-450 wds incl. reconnection hook + Delightree angle) -> FLAG -> T1 (A/B each) -> T2 (A/B each) -> T3 (call list) -> CUSTOMER PROOF POINT.

## FILES & ARTIFACT
Write data.json (schema in the scheduled task) + runs/<date>/<Company>.md; update tracker.json (streak++, append run + ids); run build_artifact.py; update_artifact id "daily-reengagement". Notify on completion.

## PHONE FLAGGING (HQ / shared lines)
Pull each company's HQ main number (HubSpot company "phone"). For every contact number:
- If it matches the HQ main number -> append "⚑ [matches HQ main line - NOT a direct dial]".
- If the same number is shared by 2+ contacts (front-desk/shared line) -> append "⚑ [shared company line - likely not a direct dial]".
Keep verified mobiles/direct dials unflagged. Always SOURCE a direct/mobile via ZoomInfo when the only number on file is the HQ/shared line. Show the HQ number in each company view.

## DENVER / IN-PERSON LUNCH
Delightree is based in Denver. For any contact in the Denver metro - a NON-HQ phone with area code 303/720/970, or based at a Denver-metro HQ (per ZoomInfo location) - offer an in-person lunch ("lunch on us") as an alternative to a call in their outreach, and tag them "Denver-based - offer lunch." Do NOT offer lunch to out-of-metro/remote contacts (judge by their personal/mobile area code, not the shared HQ line).

## PAST-CONTEXT GATE (OVERRIDES the "RECONNECTION" section above)
Only frame a company as a WARM RECONNECT if there is a logged MEETING (HubSpot meetings object) OR a NOTE documenting a real event or a meaningful back-and-forth conversation (a meeting recap, an event, a real reply thread). 
Prior outbound EMAILS, SEQUENCES, or one-way outreach ATTEMPTS NEVER count and must NOT be referenced as past context. A bare data note (e.g. "70 locations") does not count either.
If the only history is outreach attempts, set reconnect_ok = false and write CLEAN FRESH OUTREACH: no "when we spoke", "I reached out", "we connected", "reconnect", "pick this back up", "reopen", "last spring/May/July/summer". Research-based personalization is still required - just never imply a relationship that does not exist. The artifact/run shows "Warm reconnect" only when reconnect_ok = true; otherwise "Fresh outreach."

## POOL EXCLUSIONS, FLOOR, EXHAUSTION (additions)
- EXCLUDE existing customers & prior wins: skip any company with lifecyclestage = "customer" OR a closed-won deal (recent_deal_amount present / a won deal stage). Never prospect someone already sold.
- LOCATION FLOOR: skip companies under 20 locations. Verify current unit count via web/ZoomInfo; if under 20, flag-and-skip and take the next eligible.
- POOL EXHAUSTION: when fewer than 3 eligible companies remain (all dormant accounts cycled via tracker.json), surface whatever IS available and NOTIFY Justin the list is exhausted. Do NOT auto-recycle or loosen the 30-day guard.

## STREAK
Streak = DAYS JUSTIN WORKS ALL 3 (marks all 3 reopened in the page). It increments only when all 3 are completed that day and BREAKS if a weekday is missed. Tracked client-side (localStorage), independent of whether the 7am run generated a list. The 7am run does NOT inflate the streak.

## T3 CALL LIST REQUIRED FOR EVERY COMPANY
Every company MUST ship a T3 call list (name, role, ALL phone numbers with HQ/shared flags, LinkedIn - NO email). If HubSpot has few/no low-tier contacts, SOURCE them via ZoomInfo (HR, Finance, Franchise Development, Area Developers, GMs, and any reachable decision-influencers) and pull their direct/mobile numbers. Never ship a company with an empty T3 list if callable contacts can be found.

## DATA RECENCY - 2025 ONLY (added per Justin, 2026-06-23; applies to ALL skills + this account)
Use ONLY 2025 data, quotes, and facts in every email, overview, and stat. Do NOT cite 2024 or older figures.
- Default sourced stat = IFA 2025 Franchising Economic Outlook (released Feb 2025): ~851,000 U.S. franchise units in 2025 (+2.5%, ~20,000 new units); ~210,000 jobs added (+2.4%); franchise GDP +5% to ~$578B; total output >$936.4B (+4.4%). Source: franchise.org 2025 outlook.
- Any other third-party stat (FRANdata, Black Box, Cornell, Gong) must be a 2025 figure or be dropped.
- Company facts (location counts, leadership, funding) must reflect 2025 reality, verified via 2025 web/LinkedIn.

## CONTACT VERIFICATION - LINKEDIN REQUIRED (added per Justin, 2026-06-23)
Every T1/T2 prospect must be confirmed actively employed at the company on LinkedIn before drafting. ZoomInfo lags (shows departed people as active) and conflates same-named companies. Maintain CONTACT-VERIFICATION-LOG.md and check it each run.

## NO PARENT / AE-OVERLAP COMPANIES (added per Justin, 2026-06-23)
Do not target a parent/holding company, ESPECIALLY one being worked by an AE, and do not target a brand whose parent is separately worked by an AE (e.g., Unleashed Brands = Keegan). If a company fails these guidelines, DROP it rather than force three.

## CONTACT VERIFICATION - DUAL-SOURCE ACTIVE-EMPLOYMENT PROTOCOL (HARDENED per Justin, 2026-06-24)
This OVERRIDES the earlier "LinkedIn required" note. NO contact ships (email OR call list) unless it passes this gate. The bar is: every contact handed to Justin must be ~1000% currently employed at the target company.

REQUIRED for EVERY contact (T1, T2, AND T3):
1. LINKEDIN (primary truth source): the person's live LinkedIn must show the TARGET company as their CURRENT employer. If LinkedIn shows the company under "previous/past experience", a different current employer, #OpenToWork, or an end-date on that role -> NOT active. ZoomInfo/HubSpot cannot override a LinkedIn departure signal.
2. COMPANY ABOUT/TEAM PAGE (second source): pull the company's own About Us / Team / Leadership page (and read its "about us" content for the current roster, leadership titles, location count and recent news). Cross-check the contact appears there or is consistent with it. Note the page's last-updated date.
3. ZoomInfo is SECONDARY/CORROBORATING ONLY. It LAGS and conflates same-named companies (documented: Pete Spillum, Scott Gultz, Eric Wheeler). A ZoomInfo FULL_MATCH/active is NOT sufficient on its own and NEVER overrides a LinkedIn or company-page departure signal. Always pull employmentHistory and check for an end-date on the current role.

CONFLICT RULE: if the company page and LinkedIn disagree (e.g., page lists them, LinkedIn shows a new employer), the contact is UNCERTAIN -> HOLD OUT. Do NOT present as active. Add to the company "departed" block as HELD OUT with the conflict spelled out, and tell Justin to confirm on the live LinkedIn before any outreach.

IDENTITY RULE: confirm it is the SAME person (employment history, location, role lineage) before trusting a same-name match. Two people share a name often.

LEADERSHIP RULE: read the About/Team page every run to catch title changes (CEO/President/COO churn). Update titles in data.json and log changes. Never carry a stale title forward.

LOGGING: record every check in CONTACT-VERIFICATION-LOG.md (VERIFIED ACTIVE with sources + date, DEPARTED, or HELD OUT/UNCERTAIN). Check the log before every run and never re-surface a DEPARTED or HELD-OUT contact as active.


## CONTACT STANDARD v2 - CANONICAL (per Justin, 2026-06-24; see VERIFICATION-PROTOCOL.md for full text)
This is the operative standard and SUPERSEDES the older verification/coverage notes above where they conflict.
1. ACTIVE-EMPLOYMENT (3 sources, LinkedIn decides). Every contact, every run: (a) open the person's LIVE LinkedIn in the
   connected Chrome browser and confirm the target company is their CURRENT role with no end-date; (b) corroborate with
   ZoomInfo employmentHistory (NEVER let ZoomInfo override a LinkedIn departure); (c) check the company About/Team page for
   leadership/title/location changes. A name on a team page is NOT proof of employment (franchise brands list outsourced
   sales brokers like FOC/FranServe). Conflict -> HOLD OUT + flag. Can't open LinkedIn -> flag "NOT LINKEDIN-VERIFIED".
2. EXHAUSTIVE ICP COVERAGE (no cap). Return every ICP-fitting HQ contact: all qualifying HubSpot contacts PLUS net-new
   sourced from ZoomInfo for any missing ICP role (Operations, Support, Compliance, Training/L&D, FBCs, Regional/District
   VPs, Growth, CEO/President, COO/CSO/CGO/CTO, Franchise Dev, HR, Finance). Exclude franchisees/store-level/brokers. Tier
   everyone, but include all.
3. FULL PRIOR-CONTEXT DIG. Before drafting, pull and summarize ALL HubSpot history per company: deals (incl. closed-lost
   with stage/amount/close date/lost reason), meetings, logged calls, notes, and email threads. Summarize per company and
   per contact. WARM RECONNECT only if a real meeting/two-way conversation/closed-lost deal exists, referenced specifically;
   one-way outbound = FRESH.

## DAILY SLATE & CARRYOVER (per Justin, 2026-06-24) - OVERRIDES STEP 1 selection/retirement
The daily list is a ROLLING SLATE of 3 UNENROLLED companies. A company stays on the slate until Justin actually enrolls/works it; only then is it retired. Never retire a company merely for being surfaced.
tracker.json fields: `active_slate` = current 3 (each {id, name, surfaced_date}); `completed_company_ids` = ONLY companies enrolled/worked (retired permanently).
Each run, in order:
1. EVALUATE PRIOR SLATE. For each company on the previous `active_slate`, decide WORKED vs NOT WORKED since its surfaced_date.
   WORKED = any associated contact now has an active sequence (hs_sequences_is_enrolled = true) OR notes_last_contacted is on/after surfaced_date OR the company now has an open deal (hs_num_open_deals > 0).
   - WORKED  -> move its id to `completed_company_ids` and drop from the slate.
   - NOT WORKED -> CARRY OVER: keep it on today's slate with its ORIGINAL (earliest) surfaced_date; do not reset.
2. FILL TO 3. Add new eligible companies (normal eligibility, excluding `completed_company_ids` AND current carryovers), warm/oldest-dormant first, until the slate has exactly 3.
3. RESEARCH all 3 on the slate FRESH each run (carryover + new) per the Contact Standard (VERIFICATION-PROTOCOL.md). Write data.json + runs for the current slate of 3.
4. WRITE tracker: set `active_slate` to today's 3 (ids + surfaced_date), append worked ids to `completed_company_ids`, log any carryover in `carryover_log` ({date, carried:[ids]}). Streak stays page-side (untouched).
5. POOL FLOOR unchanged: if the eligible pool cannot fill to 3, surface what's available and NOTIFY Justin (never loosen the 30-day guard).
COMPLETION SIGNAL NOTE: the 7AM run cannot read the artifact's page-side "Mark reopened" clicks (localStorage). It infers "worked" from the HubSpot footprint above (enrollment/contact/deal). If Justin wants a company retired without a HubSpot footprint, he can move its id to completed_company_ids manually.


## CONTACT & ACCOUNT STANDARD v3 (per Justin 2026-06-25) - OVERRIDES conflicting rules above
Full text: MASTER-PROSPECTING-STANDARD-v3.md / VERIFICATION-PROTOCOL.md. Key changes: ALL tiers (T1/T2/T3) get A/B emails (T3 keeps its call list too; T3 angle is role-specific); draft emails for 6-8 contacts/company, list extras beyond 8; re-verify active employment every run (LinkedIn decides, ZoomInfo fallback if LinkedIn unavailable, #OpenToWork = include+flag); 24-month prior-context dig (deals+notes+meetings+replies); WARM only if the prospect actually responded; closed-lost = reference reason + what changed; parent/AE/active-deal guardrails checked FIRST (parent contacts under a 'Parent Company' section; only an open deal or future meeting blocks; follow-up asks = higher priority, flag at top); add a Solution Hypothesis + Business Case + Target Champion per company.


## C-SUITE ALWAYS TIER 1 (per Justin 2026-06-26)
Any C-level executive, Founder, or President is ALWAYS Tier 1 in every size band, regardless of the '50+ CEO drops off T1' guidance. Full tiering: KNOWLEDGE.md sec 2 / Kyle skill.


## OWNERSHIP LOCK (per Justin 2026-06-26) - ONLY these accounts
Touch a company ONLY if hubspot_owner_id = Justin Hoke (83840653), OR (hubspot_owner_id IN [Ben Newman 91491264, Ashley Mahan 89337815, Keegan Santasiere 63616141] AND adr = 83840653). No other owners, no other accounts.

## LOCATION COUNT (FDD + company + Apollo) (per Justin 2026-06-26)
Verify each company's CURRENT unit count from the most recent FDD and the company's own pages, cross-checked with Apollo and ZoomInfo; use the most accurate/recent figure. Enforce the 20+ location floor; skip anything under 20.
