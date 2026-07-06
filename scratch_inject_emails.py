"""One-off: hand-drafted A/B emails (as Vinci, to the ported playbook) injected into
the current slate so the full page can be reviewed WITHOUT an Anthropic key.
Production path is app/pipeline/draft.py (calls the API). Keyed by (company, name, title).
"""
import json, sys
sys.path.insert(0, ".")
from app.render import render_html
from app.models import PageData, Company, Contact, VerificationStatus
from app import storage
from app.registry import require_rep

OWNER = "83840653"
data = json.load(open(f"data/{OWNER}/data.json"))

# (company, name, title) -> (a_subj, a_body, b_subj, b_body)
E = {
# ---------------- Native Grill and Wings (F&B) ----------------
("Native Grill and Wings","Dan Chaon","CEO"): (
 "consistency at wings scale",
 "Native Grill runs a sports-bar format where the guest experience is made or lost at the unit level, and the gap between your strongest and weakest store tends to widen before it narrows as you add locations. The IFA counted roughly 851,000 U.S. franchise units in 2025, and the brands pulling ahead make their standards visible in real time instead of auditing after the fact. Group texts and quarterly field visits miss most of what actually happens on a Friday night. L&L Hawaiian Barbecue runs 170+ location audits a month from a phone. Worth a short look at how that would map to Native Grill on Delightree?",
 "opening the next location faster",
 "Most multi-unit brands lose weeks per opening to checklists living in binders and inboxes, and every location that opens a month late is revenue you never recover. U.S. franchise output passed 936 billion dollars in 2025, and the operators capturing that share make new-store openings repeatable rather than heroic. Adding HQ headcount or sending more templates rarely closes the gap. L&L Hawaiian Barbecue standardized its pre-opening and daily ops so new units ramp without hand-holding. Curious whether faster, cleaner openings would change the growth math at Native Grill with Delightree?",
),
("Native Grill and Wings","Gregg Nettleton","President and Chief Operating Officer"): (
 "what field visits miss",
 "As COO you see the same pattern every operator hits: execution that looks fine on a field visit and drifts the other 89 days. Franchise GDP grew about 5 percent to 578 billion dollars in 2025, and the brands outperforming are the ones turning standards into daily, checkable behavior at the store. Clipboards and monthly reports tell you what happened, not what is happening. L&L Hawaiian Barbecue moved to real-time audits across 170+ locations and cut ops complexity by roughly 80 percent. Would it be useful to see how that would look across Native Grill on Delightree?",
 "audits without the clipboard",
 "Compliance at a sports-bar brand is mostly invisible until something goes wrong at one unit and becomes a brand problem. Around 20,000 new franchise units opened in the U.S. in 2025, which means more locations and more surface area for things to slip. Hiring more field consultants or tightening the manual does not scale with the footprint. L&L Hawaiian Barbecue runs its audits and corrective actions in one place, so issues get caught and closed before they spread. Open to a quick look at higher, faster audit scores across Native Grill with Delightree?",
),
("Native Grill and Wings","Jami Lee","Chief Executive Officer"): (
 "the standards drift problem",
 "Every growing food brand fights standards drift: the recipes, service steps, and cleanliness that made the first units great get diluted as the map fills in. The IFA put U.S. franchising at roughly 851,000 units in 2025, and the winners are making consistency measurable rather than hoping for it. A shared drive of PDFs and a quarterly visit will not hold the line. L&L Hawaiian Barbecue keeps 170+ locations on the same playbook and audits them monthly from a phone. Worth a short conversation about holding Native Grill's standards as you scale, using Delightree?",
 "training that actually sticks",
 "Turnover in wings and sports-bar concepts means you are training new staff constantly, and inconsistent onboarding shows up fast in ticket times and guest scores. Franchising added around 210,000 jobs in the U.S. in 2025, so the training load is only growing. Longer manuals and one-off store meetings do not move completion rates. L&L Hawaiian Barbecue gets verifiable, mobile training done across every location so new hires ramp the same way everywhere. Would it be worth seeing how Native Grill could make onboarding consistent with Delightree?",
),
("Native Grill and Wings","Judith Anderson","Vice President"): (
 "one source of truth for ops",
 "Most VPs at growing brands are stitching together tools and threads to figure out what is actually happening across units, and the answer is usually a few days old by the time it arrives. The IFA counted roughly 851,000 U.S. franchise units in 2025, and the brands ahead of the curve run operations from a single source of truth. Email, texts, and spreadsheets each hold a piece, and none of them hold the picture. L&L Hawaiian Barbecue runs 170+ location audits a month in one platform. Happy to show how L&L does it on Delightree if useful for Native Grill.",
 "less time chasing updates",
 "A lot of the VP job at multi-unit brands is chasing status: who did the reset, who finished the LTO training, which store missed the checklist. About 20,000 new units opened across U.S. franchising in 2025, which only adds to the chase. More reports and more check-in calls do not give you time back. L&L Hawaiian Barbecue put its tasks, audits, and comms in one place and cut ops complexity by roughly 80 percent. I can walk you through how that would free up Native Grill's field team with Delightree.",
),
("Native Grill and Wings","Julie Gilow","Director, Training"): (
 "training completion you can see",
 "Training in a high-turnover concept is only as good as what sticks on the floor, and most brands cannot see completion by store until it is too late to fix. Franchising added around 210,000 U.S. jobs in 2025, so the volume of new hires to onboard keeps rising. Printed manuals and in-store shadowing give you no line of sight into who actually finished. Clean Eatz went from zero to 100 percent verifiable training compliance after moving onboarding to mobile. Happy to show how that approach would work for Native Grill's training on Delightree.",
 "onboarding that ramps faster",
 "The faster a new hire reaches full productivity, the less it costs you in errors and guest experience, but ramp time is hard to compress with classroom-style onboarding. Roughly 20,000 new franchise units opened in the U.S. in 2025, each needing staff trained the same way. Longer sessions and more PDFs do not shorten the ramp. L&L Hawaiian Barbecue delivers standardized mobile training across every location so new staff get productive faster. Open to a short walkthrough of faster onboarding for Native Grill with Delightree?",
),
("Native Grill and Wings","Stephen Snyder","Manager, Information Technology & Systems"): (
 "fewer tools, one platform",
 "Most growing brands accumulate a stack: one tool for tasks, another for audits, a drive for SOPs, and a chat app for comms, and IT ends up supporting all of it. U.S. franchise output topped 936 billion dollars in 2025, and the operators scaling cleanly are consolidating rather than adding logins. More point tools mean more integrations to babysit and more shadow IT. Slick City replaced five separate tools across 32+ territories with one platform. Open to a 15 minute look at what Native Grill could consolidate onto Delightree?",
 "rollouts without the headache",
 "Every new location and every process change lands on IT to configure, provision, and support, and that overhead grows with the footprint. About 20,000 new U.S. franchise units opened in 2025, so rollout volume is climbing industry-wide. Custom-building or wiring together more systems adds maintenance you will own forever. Slick City standardized its operations stack so new territories come online without a custom setup each time. Happy to show how Native Grill could simplify rollouts and support with Delightree in a quick call.",
),
# ---------------- Chopt Creative Salad (F&B) ----------------
("Chopt Creative Salad","Ana Rodriguez","Regional VP, Operations"): (
 "visibility across your region",
 "Running a region of fast-casual units means your read on execution is only as fresh as your last visit, and the busiest stores are usually the ones you see least. The IFA counted roughly 851,000 U.S. franchise units in 2025, and the brands ahead run their regions on real-time data instead of memory. Drive-time and spreadsheets do not scale across a growing map. L&L Hawaiian Barbecue runs 170+ location audits a month from a phone. Happy to show how L&L does it on Delightree if it is useful for your Chopt region.",
 "prep and food-safety on track",
 "In a salad concept, prep discipline and food safety are the whole game, and a single slip at one unit can become a brand headline. Around 20,000 new franchise units opened in the U.S. in 2025, widening the surface area for misses. More surprise visits and longer checklists do not fix consistency. L&L Hawaiian Barbecue runs daily line checks and audits in one place across every location. I can walk you through how that would tighten food safety across your Chopt region with Delightree.",
),
("Chopt Creative Salad","Jose Hernandez","Regional VP, Operations"): (
 "one view of every store",
 "As a Regional VP you are accountable for stores you cannot be standing in, and by the time an issue reaches you it has usually cost a few shifts. U.S. franchise output passed 936 billion dollars in 2025, and the operators capturing it run on one live view of every unit. Texts and monthly reports each hold a fragment of the truth. L&L Hawaiian Barbecue put audits, tasks, and comms in one platform across 170+ locations. Happy to show how that would give you a single view of your Chopt region on Delightree.",
 "faster fixes, fewer repeats",
 "The cost in operations is rarely the first mistake, it is the same mistake repeating across stores before anyone connects the dots. About 20,000 new U.S. franchise units opened in 2025, so patterns get harder to spot as regions grow. Emailing reminders and re-training one store at a time does not stop the repeat. L&L Hawaiian Barbecue closes corrective actions in one place and cut ops complexity by roughly 80 percent. I can show you how to catch and close issues faster across Chopt with Delightree.",
),
("Chopt Creative Salad","Tom Kelleher","Chief Operations Officer"): (
 "standards that hold at scale",
 "The COO problem at a scaling food brand is that the systems that ran 20 stores quietly stop working at 60, usually without a clear signal until scores slip. Franchise GDP grew about 5 percent to 578 billion dollars in 2025, and the outperformers make standards checkable daily rather than quarterly. Adding field headcount buys time, not consistency. L&L Hawaiian Barbecue runs 170+ location audits monthly and cut ops complexity by roughly 80 percent. Worth a short look at how Chopt could hold its standards through the next stage on Delightree?",
 "less load on your HQ team",
 "As Chopt grows, more of the day at HQ gets spent answering the same store questions and re-sending the same guidance. The IFA put U.S. franchising near 851,000 units in 2025, so that support load compounds with every opening. Hiring more coordinators scales cost, not leverage. L&L Hawaiian Barbecue gave locations self-serve answers and one place for tasks, so HQ fields fewer one-off asks. Open to seeing how Chopt could cut HQ load while improving execution with Delightree?",
),
("Chopt Creative Salad","Aubrey Kenny","Director, Training & Development"): (
 "completion by store, live",
 "Training a fast-casual brand only works if it lands on the line, and most teams cannot see completion by store until numbers slip. Franchising added around 210,000 U.S. jobs in 2025, so the onboarding volume keeps climbing. Classroom sessions and PDFs give you no visibility into who actually finished. Clean Eatz reached 100 percent verifiable training compliance after going mobile. Happy to walk you through how Chopt could see training completion by location on Delightree.",
 "menu changes that stick",
 "In a creative-salad concept the menu moves constantly, and every LTO or recipe change is a retraining event across every store. Roughly 20,000 new franchise units opened in the U.S. in 2025, each needing the same updates to land cleanly. Emailing a new spec sheet does not confirm anyone learned it. L&L Hawaiian Barbecue pushes updates and verifies training in one place across 170+ locations. Open to a short walkthrough of rolling out menu changes cleanly at Chopt with Delightree?",
),
("Chopt Creative Salad","Jose Ventura","General Manager"): (
 "your shift, all in one place",
 "A GM's day is task-switching across prep, people, safety, and guests, and most of the tools meant to help are scattered across paper and phones. About 20,000 new U.S. franchise units opened in 2025, and the brands ahead give managers one place to run the shift. Another binder or another group chat adds noise, not clarity. L&L Hawaiian Barbecue put daily tasks, line checks, and comms in a single app across every location. Happy to show you how that would simplify a shift at your Chopt store with Delightree.",
 "less time on paperwork",
 "The parts of the GM job that eat time, logs, checklists, and chasing sign-offs, are exactly the parts that should be automatic. U.S. franchise output topped 936 billion dollars in 2025, and operators are freeing managers to run the floor instead of the clipboard. Stacking more forms does not give the shift back. L&L Hawaiian Barbecue digitized its line checks and cut ops complexity by roughly 80 percent. Open to a quick look at cutting the paperwork at your Chopt store with Delightree?",
),
("Chopt Creative Salad","Tim Martone","Vice President, Information Technology"): (
 "consolidate the ops stack",
 "Scaling brands tend to collect tools, tasks here, audits there, SOPs on a drive, comms in chat, and IT inherits every integration and login. U.S. franchise output passed 936 billion dollars in 2025, and the operators scaling cleanly consolidate rather than add. More point tools mean more to secure and support. Slick City replaced five tools across 32+ territories with one platform. Happy to show what Chopt could consolidate onto Delightree in a short call.",
 "rollouts that do not fall on IT",
 "Every new store and process change becomes an IT project to configure and support, and that grows with the footprint. Around 20,000 new U.S. franchise units opened in 2025, so rollout volume is rising across the industry. Wiring together more systems adds maintenance you own forever. Slick City standardized its stack so new territories launch without custom setup. Open to a 15 minute look at simpler rollouts for Chopt with Delightree?",
),
# ---------------- UATP Management / Urban Air (Fitness & Entertainment) ----------------
("UATP Management","Chandler Jackson","Director, Operations"): (
 "visibility across the parks",
 "Running operations across adventure parks means safety, staffing, and guest flow all have to be right at once, and your read on any park is only as current as your last walk-through. The IFA counted roughly 851,000 U.S. franchise units in 2025, and the brands ahead run on real-time data across locations. Radios and spreadsheets do not scale with the map. Slick City, an entertainment franchise that consolidated five tools into one platform, standardizes operations across new locations so nothing slips as they open. Happy to show how that would look across your parks on Delightree.",
 "safety checks, done and logged",
 "In high-energy park environments, safety and equipment checks are the difference between a normal day and an incident, and paper logs are hard to trust and harder to audit. About 20,000 new U.S. franchise units opened in 2025, widening the operational surface area. More laminated checklists do not guarantee the check happened. Slick City runs standardized opening and safety routines across territories in one place. I can walk you through provable safety checks across your parks with Delightree.",
),
("UATP Management","Phillip Jackson","Chief Executive Officer"): (
 "execution as you scale parks",
 "The CEO challenge in a fast-growing park brand is that the systems that ran a handful of parks quietly stop working across dozens, usually before any dashboard shows it. Franchise GDP grew about 5 percent to 578 billion dollars in 2025, and the brands outperforming turn standards into daily, checkable behavior. Adding regional headcount buys time, not consistency. Slick City, an entertainment franchise that consolidated five tools into one platform, keeps new locations on one playbook as it grows. Worth a short conversation about holding execution across Urban Air's parks with Delightree?",
 "one platform, less HQ load",
 "As the park count grows, HQ spends more of the day answering the same questions and re-sending the same guidance to the field. The IFA put U.S. franchising near 851,000 units in 2025, so that load compounds with every opening. Hiring more coordinators scales cost, not leverage. Slick City gives locations self-serve answers and one place for tasks and comms, so HQ fields fewer one-off asks. Open to seeing how Urban Air could cut HQ load while tightening execution on Delightree?",
),
("UATP Management","Thom Perot","Director, Operations"): (
 "one live view of each park",
 "As a Director of Operations you own outcomes at parks you cannot be standing in, and issues usually reach you after they have cost a shift or a guest experience. U.S. franchise output passed 936 billion dollars in 2025, and the operators capturing it run on one live view per location. Texts and weekly reports each hold a fragment. Slick City, an entertainment franchise that consolidated five tools into one platform, runs tasks and audits in one platform across territories. Happy to show how that would give you a single view of each park on Delightree.",
 "faster fixes across parks",
 "The real cost is rarely the first miss, it is the same miss repeating across parks before anyone connects the dots. About 20,000 new U.S. franchise units opened in 2025, making patterns harder to spot as you grow. Re-training one park at a time does not stop the repeat. Slick City closes corrective actions in one place across its locations. I can show you how to catch and close issues faster across Urban Air's parks with Delightree.",
),
("UATP Management","Tim Sharp","Vice President, Operations"): (
 "standards that hold at scale",
 "The VP of Ops problem in a scaling park brand is holding the line on standards across a map that keeps growing, without living on the road. The IFA counted roughly 851,000 U.S. franchise units in 2025, and the brands ahead make standards checkable daily rather than on the next visit. Drive-time and spreadsheets do not scale. Slick City, an entertainment franchise that consolidated five tools into one platform, keeps new locations on the same playbook as it opens. Happy to show how Slick City does it on Delightree if useful for Urban Air.",
 "onboarding new parks faster",
 "Every new park is a race to get staff trained and processes live, and time lost to setup is revenue you do not recover. Around 20,000 new U.S. franchise units opened in 2025, each needing a clean, repeatable launch. Emailing templates and running one-off trainings does not compress the ramp. Slick City standardized its openings so new locations come online without heavy HQ lift. Open to a short walkthrough of faster park openings for Urban Air with Delightree?",
),
("UATP Management","Tim Sharp","President"): (
 "the drift problem at scale",
 "The pattern every growing park brand hits is standards drift: the safety, service, and cleanliness that defined the first parks get diluted as the count climbs. Franchise output in the U.S. topped 936 billion dollars in 2025, and the winners make consistency measurable instead of assumed. A shared drive and a quarterly visit will not hold it. Slick City, an entertainment franchise that consolidated five tools into one platform, keeps its locations on one playbook as it grows. Worth a short look at protecting Urban Air's standards through the next stage on Delightree?",
 "growth without more HQ heads",
 "Scaling parks usually means scaling HQ headcount just to keep the field supported, which caps how efficiently you grow. The IFA put U.S. franchising near 851,000 units in 2025, and the operators pulling ahead scale support without scaling staff. More coordinators is cost, not leverage. Slick City gives locations self-serve answers and one operational home, so HQ stays lean. Open to seeing how Urban Air could grow parks without adding HQ load, using Delightree?",
),
("UATP Management","Chris Kelley","Director, Training & Culture"): (
 "training that reaches the floor",
 "Training and culture only matter if they show up in how staff run the park on a busy Saturday, and most brands cannot see whether training landed by location. Franchising added around 210,000 U.S. jobs in 2025, so the onboarding volume keeps rising. Orientation days and PDFs give you no line of sight into completion. Clean Eatz reached 100 percent verifiable training compliance after moving to mobile. Happy to show how Urban Air could see training completion by park on Delightree.",
 "consistent culture across parks",
 "Culture is hard to scale when every park hires and trains a little differently, and the differences compound as you grow. Roughly 20,000 new U.S. franchise units opened in 2025, each needing the same standards to land. More handbooks do not create consistency. Slick City delivers standardized training and comms across its locations so the experience feels the same everywhere. Open to a short walkthrough of consistent onboarding across Urban Air with Delightree?",
),
("UATP Management","John Kelly","Director, Field Marketing"): (
 "local promos executed right",
 "Field marketing only works when every park actually executes the promotion on time and on brand, and most brands cannot confirm it happened until the numbers come in. U.S. franchise output passed 936 billion dollars in 2025, and the operators winning locally make execution checkable, not assumed. Emailing a promo kit does not confirm the park set it up. Slick City, an entertainment franchise that consolidated five tools into one platform, pushes campaigns and verifies execution in one place across territories. Happy to show how Urban Air could confirm local promos land on Delightree.",
 "one channel to every park",
 "Getting a consistent message to every park usually means a pile of emails and group chats, and you are never sure it reached the floor. Around 20,000 new U.S. franchise units opened in 2025, making clean field comms harder as you grow. More email blasts do not guarantee it landed. Slick City runs field comms and confirmations in one platform across its locations. Open to a quick look at one reliable channel to every Urban Air park with Delightree?",
),
("UATP Management","Mel Sinclair","Manager, Franchise Training"): (
 "trackable training rollouts",
 "Rolling out training across franchise parks is only useful if you can see who completed it, and spreadsheets of sign-offs are slow and easy to game. Franchising added around 210,000 U.S. jobs in 2025, so the training load keeps growing. Chasing completion by email does not scale. Clean Eatz reached 100 percent verifiable training compliance after going mobile. Open to a 15 minute walkthrough of trackable training rollouts for Urban Air's parks on Delightree?",
 "onboarding new parks cleanly",
 "When a new park opens, getting staff trained the same way as everywhere else is what protects the guest experience from day one. About 20,000 new U.S. franchise units opened in 2025, each needing a repeatable onboarding path. One-off sessions per park do not scale. Slick City standardized location onboarding so new locations ramp consistently. Happy to show how Urban Air could standardize new-park training with Delightree in a quick call.",
),
}

# LinkedIn cold messages (demo: Native Grill only, to show the full card end-to-end).
# Real API drafting writes these for every contact from app/playbooks/vinci.md.
LI = {
("Native Grill and Wings","Dan Chaon","CEO"): "Dan, scaling Native Grill's sports-bar format usually means the gap between your best and worst store widens before it narrows. The IFA counted about 851,000 U.S. franchise units in 2025, and the brands holding standard make execution visible in real time instead of auditing after the fact. Curious how you keep the 30th store running like the 3rd. Open to comparing notes on how L&L Hawaiian Barbecue does it on Delightree?",
("Native Grill and Wings","Gregg Nettleton","President and Chief Operating Officer"): "Gregg, most COOs find a field visit shows a clean store that drifts the other 89 days. About 20,000 new U.S. franchise units opened in 2025, so the surface area for slippage only grows. L&L Hawaiian Barbecue moved to real-time audits across 170+ locations and cut ops complexity by roughly 80 percent. Worth a short look at how that maps to Native Grill on Delightree?",
("Native Grill and Wings","Jami Lee","Chief Executive Officer"): "Jami, standards drift is the quiet tax on a growing food brand: the recipes and service steps that made the first units great dilute as the map fills in. Franchising added around 210,000 U.S. jobs in 2025, so you are onboarding constantly. Would it be useful to see how Native Grill could keep training consistent across every unit with Delightree?",
("Native Grill and Wings","Judith Anderson","Vice President"): "Judith, a lot of the VP role is chasing status across units, and the answer is usually days old by the time it lands. L&L Hawaiian Barbecue put tasks, audits, and comms in one place across 170+ locations. Happy to show how that would free up your field team on Delightree if useful.",
("Native Grill and Wings","Julie Gilow","Director, Training"): "Julie, training in a high-turnover concept is only as good as what sticks on the floor, and most brands cannot see completion by store until it is too late. Clean Eatz went from zero to 100 percent verifiable training compliance after moving onboarding to mobile. Open to a quick look at trackable training for Native Grill on Delightree?",
("Native Grill and Wings","Stephen Snyder","Manager, Information Technology & Systems"): "Stephen, growing brands tend to accumulate a stack, and IT ends up supporting all of it. Slick City replaced five separate tools across 32+ territories with one platform. Open to a 15 minute look at what Native Grill could consolidate onto Delightree?",
}

# per-email expansion sentence, inserted before the CTA to reach the 90-word floor
EXPAND = {
("Native Grill and Wings","Jami Lee","Chief Executive Officer","b"): "Inconsistent onboarding also shows up in the P and L as longer ramp times and higher early turnover at the units that can least afford it.",
("Native Grill and Wings","Julie Gilow","Director, Training","b"): "Every extra week a new hire takes to reach full speed is measurable cost in errors, comps, and slower tickets during peak.",
("Native Grill and Wings","Stephen Snyder","Manager, Information Technology & Systems","a"): "Each disconnected tool is another vendor to manage, another security review, and another thing that breaks during a Friday rush.",
("Native Grill and Wings","Stephen Snyder","Manager, Information Technology & Systems","b"): "That maintenance never shows up in the project plan, yet it quietly becomes most of what your team spends its week on.",
("Chopt Creative Salad","Ana Rodriguez","Regional VP, Operations","b"): "A missed line check at one store is a note, the same miss across ten stores in a week is a brand risk.",
("Chopt Creative Salad","Jose Hernandez","Regional VP, Operations","b"): "Catching the pattern early is the difference between a quick coaching conversation and a region-wide problem.",
("Chopt Creative Salad","Tom Kelleher","Chief Operations Officer","b"): "The brands that scale support instead of headcount are the ones that keep margins intact while the map keeps growing.",
("Chopt Creative Salad","Aubrey Kenny","Director, Training & Development","a"): "Without that line of sight, retraining becomes guesswork and the same gaps resurface every quarter at the stores that need it most.",
("Chopt Creative Salad","Aubrey Kenny","Director, Training & Development","b"): "When a change does not land evenly, guests notice the difference between locations well before the numbers show it to you.",
("Chopt Creative Salad","Jose Ventura","General Manager","a"): "The result is a manager who spends the shift leading the team rather than hunting for the right checklist.",
("Chopt Creative Salad","Jose Ventura","General Manager","b"): "Time off the clipboard is time on the guest, which is where a fast-casual brand actually wins or loses.",
("Chopt Creative Salad","Tim Martone","Vice President, Information Technology","a"): "Each added login is one more onboarding step for every new manager and one more account to deprovision when they leave.",
("Chopt Creative Salad","Tim Martone","Vice President, Information Technology","b"): "The work never appears on a roadmap, yet it consumes the capacity you wanted for higher-value projects, and standardizing once means every future store inherits the same setup.",
("UATP Management","Chandler Jackson","Director, Operations","b"): "A safety miss that never gets logged stays invisible until the day it becomes an incident report.",
("UATP Management","Phillip Jackson","Chief Executive Officer","a"): "Regional leaders can only be in one park at a time, so the map keeps outgrowing the people watching it.",
("UATP Management","Phillip Jackson","Chief Executive Officer","b"): "Scaling support instead of headcount is what keeps unit economics intact as the park count climbs.",
("UATP Management","Thom Perot","Director, Operations","b"): "Spotting it once, across every park, turns a recurring headache into a single fix you make one time.",
("UATP Management","Tim Sharp","Vice President, Operations","a"): "The parks that drift the most are usually the ones your travel schedule reaches the least.",
("UATP Management","Tim Sharp","Vice President, Operations","b"): "Every week a new park takes to reach full operation is peak-season revenue you do not get a second chance at.",
("UATP Management","Tim Sharp","President","a"): "A shared drive tells everyone what the standard is, not whether a single park is actually meeting it.",
("UATP Management","Tim Sharp","President","b"): "Growth that depends on adding coordinators eventually caps how fast you can open, so leverage is what makes the next twenty parks easier than the last.",
("UATP Management","Chris Kelley","Director, Training & Culture","a"): "If you cannot see completion by park, culture becomes a hope rather than a standard you can hold people to.",
("UATP Management","Chris Kelley","Director, Training & Culture","b"): "The differences start small and then define how a guest experiences one park versus another, and consistency is what lets a new park feel like the brand on day one.",
("UATP Management","John Kelly","Director, Field Marketing","a"): "A promotion that runs in half your parks is a campaign you paid for in full and only half launched.",
("UATP Management","John Kelly","Director, Field Marketing","b"): "Confirmation, not hope, is what tells you the message actually reached the floor of every park.",
("UATP Management","Mel Sinclair","Manager, Franchise Training","a"): "Sign-off spreadsheets are slow to compile and easy to fudge, so the number is never one you fully trust when it matters.",
("UATP Management","Mel Sinclair","Manager, Franchise Training","b"): "A repeatable path means the tenth park opens as smoothly as your best one instead of repeating the mistakes of your first.",
}


def _expand(body: str, extra: str) -> str:
    """Insert `extra` as its own sentence immediately before the final (CTA) sentence."""
    parts = body.rstrip().split(". ")
    if len(parts) < 2:
        return body
    cta = parts[-1]
    return ". ".join(parts[:-1]) + ". " + extra + " " + cta


# rebuild PageData from stored data.json, then inject emails
companies = []
for co in data["companies"]:
    cts = []
    for ct in co["contacts"]:
        key = (co["name"], ct["name"], ct["title"])
        c = Contact(
            name=ct["name"], title=ct["title"], tier=ct["tier"], li=ct["li"],
            email=ct["email"], email_note=ct["email_note"], phone=ct["phone"],
            hub=ct.get("hub",""), hub_url=ct.get("hub_url",""), local=ct.get("local",False),
            verif_status=VerificationStatus(ct["verif_status"]),
            verif_label=ct["verif_label"], verif_sources=ct.get("verif_sources",""),
        )
        if key in E:
            c.a_subj, c.a_body, c.b_subj, c.b_body = E[key]
            for tag in ("a", "b"):
                ek = (co["name"], ct["name"], ct["title"], tag)
                body = getattr(c, tag + "_body")
                if ek in EXPAND and body:
                    setattr(c, tag + "_body", _expand(body, EXPAND[ek]))
            c.li_msg = LI.get(key, "")
        cts.append(c)
    n_emailed = sum(1 for c in cts if c.a_subj)
    flags = co["flags"].replace(" Email drafting skipped (no valid ANTHROPIC_API_KEY).", "")
    import re as _re
    flags = _re.sub(r"( A/B emails drafted for \d+ contact\(s\)\.)+", "", flags).strip()
    flags = flags + f" A/B emails drafted for {n_emailed} contact(s)."
    proof = co["proof"]
    if co["name"] == "UATP Management":
        proof = "Slick City, an entertainment franchise (Urban Air is an adventure-park brand, different vertical): replaced five tools with one platform across 32+ territories."
    companies.append(Company(
        id=co["id"], name=co["name"], domain=co["domain"], vertical=co["vertical"],
        status=co["status"], last_touch=co["last_touch"], hubspot=co["hubspot"],
        reconnect_ok=co["reconnect_ok"], proof=proof, hq_phone=co["hq_phone"],
        overview=co["overview"], flags=flags, contacts=cts,
    ))

rep = require_rep("justin@delightree.com")
page = PageData(generated=data["generated"], signature=data["signature"], companies=companies)
storage.save_data_json(OWNER, page.to_data_json())
storage.save_page(OWNER, render_html(page, streak=1, rep_name=rep.rep_name))

# validate playbook constraints
import re
bad = []
for co in page.companies:
    for c in co.contacts:
        for tag, subj, body in [("A", c.a_subj, c.a_body), ("B", c.b_subj, c.b_body)]:
            if not body:
                continue
            wc = len(body.split())
            if "—" in body or "—" in subj: bad.append((co.name, c.name, tag, "EM DASH"))
            if wc < 90 or wc > 130: bad.append((co.name, c.name, tag, f"words={wc}"))
            if len(subj) > 33: bad.append((co.name, c.name, tag, f"subj={len(subj)}"))
            if body.lower().count("delightree") != 1: bad.append((co.name, c.name, tag, f"delightree x{body.lower().count('delightree')}"))
drafted = sum(1 for co in page.companies for c in co.contacts if c.a_subj)
print(f"injected emails for {drafted} contacts")
if bad:
    print("PLAYBOOK VIOLATIONS:")
    for b in bad: print("  ", b)
else:
    print("playbook check: all emails 90-130 words, no em dashes, subjects <=33, Delightree once in CTA")
