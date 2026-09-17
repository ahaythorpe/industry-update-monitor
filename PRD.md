# Industry Update Monitor — Product Requirements (PRD)

A personal tool to stay across the Australian financial advice industry without drowning,
without paying, and without cutting any corners. Built for one user (you), possibly shareable
later. This PRD is the spec you build against in VS Code.

---

## 1. The problem
An online student, pre-industry, between jobs, needs to keep across regulation, disputes,
policy and industry news. In-person networking and paid events are not accessible/affordable.
The information exists but is scattered across regulators, trade press, and data bodies, and
arrives faster than it can be read. Missing a 🔴 ACT-level change (a new ASIC rule, an AFCA
determination) is the real cost.

## 2. The goal
One weekly habit that surfaces what matters, flagged by how much it demands, with the original
source always one click away. AI helps sort and compress; it never replaces reading the source
on anything you'd act on.

## 3. Who it's for
- Primary: you — a learner building genuine industry knowledge.
- Possible later: other students/new entrants in the same position.
- NOT for: giving advice, being a source of truth, or anything client-facing.

## 4. Core principle (non-negotiable)
**Feeds in, free sources out. Never fetch, store, or reconstruct anything behind a paywall.**
The tool only reads content legitimately delivered to you (RSS feeds, free newsletters, free
pages). When it hits a paywall it searches your FREE sources for the same story. It never logs
in, never reads locked text. This principle governs every feature.

## 5. The flag system (the heart of it)
Every item gets one flag, by what it demands of you:
- 🔴 **ACT** — changes what you'd actually do/say for a client. Read at source. Never AI-only.
- 🟠 **KNOW** — useful context, changes no rule today. AI summary fine; open source if it graduates.
- 🟢 **NOTE** — background/data/markets. Skim, file, move on.

## 6. Intake types (how each source reaches you)
- **email_alert** — regulator/official alerts (ASIC, ABS). Land in inbox → folder.
- **email_newsletter** — trade press (Financial Standard, Professional Planner, Riskinfo, FAAA,
  Macquarie, CFS). Same pipe.
- **bookmark_and_check** — no email (AFCA, Treasury). You visit these in the weekly sweep.
- **listen** — podcasts (ifa Show, SMSF Adviser Show). Consume in a podcast app; outside the tool.

Only email/RSS sources flow through the script. Bookmark and listen sources are habits, not code.

## 7. Features, in build order (each earns the next)

### Phase 1 — Sources + digest (no AI, no cost) [BUILT]
- `sources.json` holds the flagged, categorised source list.
- Script reads RSS feeds, prints a flagged digest with source links.
- Runs offline. No API key. Cannot incur cost.
- **Status (17 Sep 2026): built, tested and running on real feeds.** It has been run many times;
  the sweep sheet, the briefing and the dashboard all come out of it. The "next step" line this
  replaces had been stale for weeks.

### Phase 2 — Email intake (habit, not code) [IN PROGRESS]
- Gmail/Hotmail label "Industry Update Monitor" + filters route newsletters into one folder.
- Weekly sweep: open the folder, read top-down by flag.
- **Status (17 Sep 2026): the code is built and tested but has never run.** `src/gmail_reader.py`
  and `--gmail` read one label, read-only, and the suite of 202 tests passes without them. What is missing is
  `credentials.json` — see [SETUP.md](SETUP.md) Part 4 and item 5 in
  [IMPROVEMENTS.md](IMPROVEMENTS.md). Until it runs, ABS, FS Industry Moves, Macquarie Technical
  Services and CFS FirstTech reach no digest, so a quiet digest is not a quiet week.

### Phase 3 — AI weekly summary (cents/week) [NOT BUILT]
- Once a week, batch the week's items through a cheap model (Haiku).
- Output: one line per item — FLAG | one-sentence summary | LINK.
- Prompt bans invention, forces short output, keeps the link. (See SAFEGUARDS.md.)
- Cost control: batch weekly, teaser text only, small model, prepaid cap.

### Phase 4 — "Find it free" paywall handler [NOT BUILT]
- Input: only the free headline/teaser from a feed.
- Action: search your free sources for the same story, return free links.
- Never touches the locked article. (See SAFEGUARDS.md — this is the highest-risk feature.)

### Phase 5 — Ask-questions chatbot over filed summaries [NOT BUILT, LAST]
- Ask "what's happening in super, any client impact?" over your STORED summaries.
- Retrieval-first: filter to relevant summaries, send only those to the model.
- Cost control: query summaries not the firehose; small model for routine Qs.

## 8. Explicit non-goals
- No scraping. No paywall bypassing. No logging into publisher sites.
- Not real-time — weekly batch is the design, on purpose (cost + calm).
- Not a source of truth — always points to the primary source.
- Not advice — it's a learning/monitoring aid.
- Not multi-user at first — personal scale keeps cost and risk contained.

## 9. Cost model (verify current pricing before relying)
- Phases 1–2: $0.
- Phase 3: ~2c/week (Haiku, batched, teaser-only). ~$1/year.
- Phase 4: ~1-2c per lookup.
- Phase 5: fraction of a cent to a couple of cents per question (retrieval-first).
- Personal scale total: a few dollars a YEAR. Hard cap via prepaid credit + spend limit.

## 10. Success = 
You run a 30-45 min weekly sweep, see the 🔴 items you'd otherwise miss, and can talk about
what's happening in the industry with specifics. The tool makes the habit stick. That's it.
