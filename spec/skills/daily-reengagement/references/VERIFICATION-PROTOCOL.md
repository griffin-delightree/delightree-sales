# Contact Standard - Verification, Coverage & Prior-Context Protocol
_Canonical rules for EVERY contact returned by ANY Delightree prospecting skill (Vinci, Kyle, Recon, Conductor, Santa) and the Daily Re-Engagement engine. Set by Justin 2026-06-24. SUPERSEDES all earlier verification notes._

## 0. THE BAR (non-negotiable, every run)
Every contact handed to Justin must be:
(a) a CURRENT employee of the target company, re-verified THIS run;
(b) part of an EXHAUSTIVE ICP set (no trimming); and
(c) accompanied by the FULL prior deal/conversation history.
If a contact cannot clear (a), it does not ship. If sources conflict, HOLD OUT and flag - never guess.

## 1. ACTIVE-EMPLOYMENT VERIFICATION - 3 sources, LinkedIn DECIDES
Run all three for EVERY contact, every time:

1) LIVE LINKEDIN (primary, decisive). Open the person's actual LinkedIn profile in the connected Chrome browser
   (mcp__Claude_in_Chrome__navigate to the profile URL, then mcp__Claude_in_Chrome__get_page_text). Confirm the TARGET
   company is their CURRENT role with NO end-date. NOT a current employee if LinkedIn shows: a different current employer,
   the brand only under past/previous experience, an end-date on that role, a brokerage/franchise-sales firm
   (Franchise Opportunity Consultants/FOC, FranServe, FranChoice, IFPG, etc.), or #OpenToWork.
2) ZOOMINFO (corroborating ONLY). Pull employmentHistory + positionStartDate + validDate to find people and contact data.
   NEVER use it to override a LinkedIn departure signal - it LAGS (documented misses: Ray Johnson, Eric Wheeler,
   Kevin Bauerle all showed FULL_MATCH/active after leaving Just Love Coffee).
3) COMPANY ABOUT/TEAM PAGE (corroborating + context). Read the company's own About / Team / Leadership page for current
   leadership, title changes, location count, and recent news. WARNING: a name on a team page is NOT proof of employment -
   franchise brands routinely list OUTSOURCED franchise-sales brokers as "team" (this is exactly how Eric Wheeler and
   Kevin Bauerle slipped through; both are FOC, not Just Love employees).

CONFLICT RULE: if LinkedIn disagrees with ZoomInfo or the company page → HOLD OUT. Do not present as active. Log the
conflict in CONTACT-VERIFICATION-LOG.md and tell Justin to confirm on the live profile.
IDENTITY RULE: confirm SAME person (employment history, location, role lineage) before trusting any same-name match.
BROWSER UNAVAILABLE: do NOT silently fall back. Flag every contact you could not LinkedIn-verify as
"⚠ NOT LINKEDIN-VERIFIED - confirm before contact" and say so explicitly to Justin.

## 2. EXHAUSTIVE ICP COVERAGE - no cap, source net-new
Return EVERY contact that fits ICP, every run. There is NO 4-7 limit. The set = BOTH of:
- Every HQ contact already in HubSpot that fits an ICP role; AND
- Net-new HQ contacts sourced from ZoomInfo to fill any ICP role the brand has but HubSpot is missing.
ICP roles (HQ / corporate only): Operations (all levels), Franchise Support, Compliance/QA, Training/L&D, FBCs/Field
Consultants, District/Regional VPs, Growth, CEO/Founder/President, COO/CSO/CGO/CTO, Franchise Development, HR/People, Finance.
EXCLUDE: single-unit franchisees, store-level/sales roles (design consultants, baristas, etc.), and outsourced brokers.
(Franchisee / area-developer / multi-unit-operator contacts are OFF by default - only include if Justin asks for that toggle.)
Still TIER everyone (T1/T2/T3 per the band rules) - but INCLUDE all who fit; do not curate down.

## 3. FULL PRIOR-CONTEXT DIG - every company, before drafting
Pull and summarize the COMPLETE HubSpot history:
- DEALS (all, incl. CLOSED-LOST): name, stage, amount, close date, owner, and the closed-lost REASON; note any prior pilot/POC.
- MEETINGS (meetings object): date, attendees, outcome.
- CALLS / NOTES: surface any real conversation, commitment, or objection.
- EMAIL THREADS: separate genuine two-way replies from one-way outbound.
Output a "Prior context" summary per COMPANY, and per CONTACT where there is real history (who was talked to, when, what
was said/decided, why it stalled).
WARM vs FRESH gate: frame as WARM RECONNECT only if a logged MEETING, a real two-way conversation, or a closed-lost deal
exists - and reference it specifically (deal name, lost reason, what changed since). One-way outbound = FRESH; never imply
a relationship that did not happen.

## 4. LOGGING
Record every check in CONTACT-VERIFICATION-LOG.md: VERIFIED ACTIVE (with the 3 sources + date), DEPARTED, or HELD OUT/UNCERTAIN.
Read the log before every run; never re-surface a DEPARTED or HELD-OUT contact as active.


---

# Delightree Prospecting - Contact & Account Standard v3
_Set by Justin 2026-06-25. SUPERSEDES prior contact/coverage notes where they conflict. PASTE THIS into every skill's `## Global Rules` (Vinci, Kyle, Recon, Conductor, Santa) and keep it in the Drive enablement doc. Canonical copy: VERIFICATION-PROTOCOL.md._

## A. EMAIL EVERY TIER (T1, T2 AND T3)
- Every tier gets TWO emails (A/B, two distinct value props), same 6-part anatomy/playbook. No tier is call-list-only anymore.
- T3 angle is ROLE-SPECIFIC: Franchise Development = faster launches / pre-opening tracking; HR/People = onboarding, training completion, retention; Finance = ROI, labor saved, cost of audit misses / AUV.
- T3 ALSO keeps the full call list: every phone (with HQ/shared-line flags) + LinkedIn, in addition to the A/B emails.
- No email + no clear pattern -> draft anyway with a FLAGGED pattern guess (firstname@domain), same as T1/T2.

## B. CONTACT COUNT
- Draft emails for 6-8 contacts per company (prioritize by tier / seniority / champion fit). If more than 8 ICP-fitting HQ contacts exist, LIST the extras (name, title, phone, LinkedIn, email if found) but do not draft emails for them.
- Source net-new HQ contacts from ZoomInfo for any ICP role HubSpot is missing (Operations, Support, Compliance/QA, Training/L&D, FBCs, Regional/District VPs, Growth, CEO/President, COO/CSO/CGO/CTO, Franchise Dev, HR, Finance). Exclude franchisees, store-level/sales reps, and outsourced brokers (FOC, FranServe, FranChoice, IFPG).

## C. ACTIVE-EMPLOYMENT VERIFICATION (re-verify EVERY run, including carryovers)
- Three sources: (1) LIVE LinkedIn in the connected Chrome browser = decisive; (2) ZoomInfo employmentHistory; (3) company About/Team page.
- NOT active if LinkedIn shows a different current employer, the brand only under past experience, an end-date on the role, or a brokerage firm.
- If LinkedIn cannot be opened this run -> fall back to ZoomInfo: accept "active" only if validated within ~90 days, and add a short note "LinkedIn not checked this run."
- #OpenToWork while still listing the company as current -> INCLUDE with a caution flag (do not silently treat as clean-active).
- Same-person check (history / location / role lineage) before trusting any same-name match. Log every check in CONTACT-VERIFICATION-LOG.md.

## D. PRIOR CONTEXT (look back 24 months, every company)
- Pull and summarize: deals (incl. CLOSED-LOST with stage, amount, close date, lost reason) + notes + meetings + logged calls/replies (enough to detect any real prospect response).
- WARM RECONNECT only if the PROSPECT actually engaged us: a reply, a logged conversation, a note of what they said, or a meeting. Unreplied one-way outbound = FRESH. Never imply a relationship that did not happen.
- CLOSED-LOST -> reference the prior deal and lost reason, and lead with WHAT HAS CHANGED on our end to address why it did not work last time.
- If anyone asked us to follow up (a date or condition), that account is HIGHER PRIORITY -> flag at the TOP of the account who said it, when, and the context; time the outreach to when they asked.

## E. PARENT / AE-OVERLAP / ACTIVE-DEAL GUARDRAILS (check FIRST, before research)
- PARENT / HOLDING: flag the parent first thing. If an AE is working the parent brand -> DO NOT prospect. If research shows no clear decision-making structure -> flag who the parent is and move on. List any parent-company contacts under a separate "Parent Company" section.
- PARENT TOUCH TEST: if the parent has had a meeting in the last 30 days, OR a future meeting scheduled, OR an open deal -> do NOT prospect the child brand. If the parent is untouched with no future tasks -> the child brand is fair to prospect.
- ACTIVE-DEAL / BEING-WORKED (the company itself): ONLY an OPEN DEAL or a FUTURE-DATED MEETING blocks prospecting. Active sequences, recent replies, or a PAST meeting do NOT block. A past meeting with no open deal and no future meeting = prospect as a WARM RECONNECT.
- On any guardrail failure mid-research -> DROP and REPLACE with the next eligible company (keep the slate at 3 clean targets).

## F. PER-COMPANY STRATEGY (add to every account)
- SOLUTION HYPOTHESIS: the specific operational gap Delightree solves for this brand at its size/stage.
- BUSINESS CASE: the cost of that gap + the outcome (visibility, audit scores, task/training completion, faster openings, less HQ load) framed for this brand.
- TARGET CHAMPION: name the single best-fit champion (usually Operations / Support) and why.

## G. EMAIL PLAYBOOK (constraints, every email)
- 90-130 words; 6-part anatomy; ONE sourced 2025 third-party stat (default IFA 2025 Franchising Economic Outlook); "Delightree" only in the CTA; 3 lowercase subjects <=33 chars; CTA by seniority; human tone; NO em dashes; no AI tells.
- PROOF POINTS: prefer Delightree's most RECOGNIZABLE customers (Tony Roma's, L&L Hawaiian BBQ, Hawaii Fluid Art, Slick City, Beem) even cross-industry, and NOTE the different vertical in the line. Real customers only. 2025 data only.
- Denver-metro contacts (non-HQ area code 303/720/970, or Denver-metro HQ) -> offer "lunch on us." Phone-flag HQ/shared lines.
- Signature: "Best, Justin Hoke | Book a Meeting | Delightree". DRAFTS ONLY - Justin enrolls.
