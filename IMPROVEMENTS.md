# Improvement list

These are deliberately staged ideas. An improvement is not ready to build until its cost,
privacy, source, and reading-time impact are understood.

Items 1 and 2 were staged early and are unstarted as of 17 September 2026. Item 3 now has the
sweep sheet under it; the habit it serves is still the user's. Items 4-9 came out of a review of
the repo on that date: they are gaps in features that already exist, not new ideas. The
numbering is staging order, not priority — of the nine, 8, 5 and 4 are the ones that cost
something to leave alone.

## 1. Newcomer explanations

Help explain unfamiliar industry terms and why an item matters, while keeping the evidence
boundary clear.

Requirements:

- Separate **what the email says**, **what is inferred**, and **what still needs checking**.
- Mark inference explicitly with language such as `Possible meaning` or `Needs confirmation`.
- Never present an inference as a legal, compliance, or client-advice conclusion.
- Link to the original email and, where available, the relevant primary source.
- Treat explanations as learning aids, not advice.
- Prefer a local glossary and rule-based explanations before using an AI model.
- ACT items still require reading the primary source.

Example format:

```text
KNOW
What it says: The email mentions a proposed superannuation reform.
Possible meaning: This may affect future policy settings.
Check: Read the Treasury or legislation source before drawing conclusions.
Source: original email link
```

Plan, 17 September 2026 — a hand-written local glossary and a place to read it.

- `data/glossary.json` holds the terms: the term itself, what it plainly means, why it matters
  to someone learning, and where to confirm it. Written by hand from the regulator's own
  wording, not generated.
- Matching is whole-word against the title and teaser already in the digest. No model, no
  network, no key. A term with no confident plain meaning is left out rather than guessed at.
- It surfaces on the sweep sheet from item 3, which is where the reading happens. An item names
  the terms it used; the explanation itself appears once per sheet, in a Terms section at the
  end, so a term running through twenty items is read once and not twenty times.
- The shape is the example above, unchanged: what it says, what that may mean, what to check,
  and the link. `Possible meaning` and `Check` stay as the words, because they are what keeps
  an inference from reading as a conclusion.
- Gates: cost nil, privacy nil (nothing leaves the laptop), source is the glossary itself and it
  cites where to confirm each entry, reading time is one explanation per term per sheet.
- What it must not do: present an inference as a legal, compliance or client-advice conclusion,
  or let a plain-English gloss stand in for reading an ACT item at its source.

Built, 17 September 2026 — `data/glossary.json` holds 32 hand-written terms, and the sweep sheet
names the ones an item used and explains each once at the end.

One change from the plan above, made while building it. `Possible meaning` on every entry was
wrong: ASIC is the corporate regulator, and hedging that teaches distrust of the whole sheet. So
a settled term reads `In plain English` and `Check`, while an entry marked `changing` — a
proposal, a threshold, a rule under review — keeps `Possible meaning` and `Needs confirmation`.
Four entries are marked that way today: DBFO, Div 296, Statement of Advice, wholesale client.
Nothing is inferred about what an item means, which is the separation item 1 asks for: the
item's own words sit above, and the glossary explains a word, not the story.

Still open:

- The glossary only grows by hand. A term that keeps appearing and is not in it is invisible;
  noticing that is currently yours.
- The explanations reach the sweep sheet only. The dashboard, the email and the WhatsApp digest
  do not show them.

## 2. API cost management

If an AI API is added later, the system must make cost a controlled resource rather than an
unknown bill.

Requirements:

- AI is off by default.
- Use local rules and extractive summaries first.
- Process only user-selected items, not every email.
- Batch one review rather than making live calls.
- Set maximum items, input characters, output tokens, and calls per week.
- Estimate and display cost before a batch runs where pricing allows it.
- Require explicit approval before the first paid batch and after a budget change.
- Use a separate prepaid API balance and provider spending limit; a Claude app subscription
  must not be assumed to cover API use.
- Record date, model, item count, token limits, and estimated/actual cost without storing a
  content firehose.
- Stop when any budget or usage limit is reached. No automatic retry loops.

Suggested initial controls:

```text
AI default: off
Review frequency: weekly
Maximum items: 10
Maximum calls: 1 per week
Budget: user chooses a hard weekly and monthly limit
Fallback: local extractive summary or manual Claude review
```

## 3. Weekly industry review

Support a sustainable learning habit rather than maximising the number of summaries.

- Track total review time and useful items.
- Review ACT items first, then selected KNOW items, then NOTE items if time remains.
- Reassess source value and API spending after several weekly reviews.
- Keep paid subscriptions as a future decision based on a recurring unmet need.

Built, 17 September 2026 — `python src/monitor.py --sweep` writes a sheet for one week's
reading: a box per item in ACT, KNOW, NOTE order, and at the foot of it the minutes, the useful
count, and a table of what each publication gave you that week. It reads the digest on disk,
reaches no publisher, costs nothing, and refuses to write over a sheet that may already hold
your ticks.

Still open, and deliberately so:

- The reading is the habit and stays yours. The sheet is where it is recorded, not a substitute.
- Reading several filled-in sheets back to compare sources across weeks. Worth doing only once
  there are several, and only if the "earned their place" lines are being filled in.
- A source that published nothing this week appears nowhere on the sheet, because the digest
  records what arrived, not what did not. A silent source is a real signal and is currently
  yours to notice.
- API spending has nothing to reassess while item 2 is unstarted and no key exists.
## 4. Summaries reach every route they are promised on

A summary pasted back by hand appears on the dashboard and nowhere else. The emailed and
WhatsApp digests drop it silently and show the publisher's teaser instead, so the routes
actually read each week are the ones missing the work.

Requirements:

- `_item_html` in `src/email_sender.py` and `_format_item` in `src/whatsapp_sender.py` read only
  the `summary` field. Neither looks at `ai_summary`, which is where an imported summary lands.
- Label the origin wherever it is shown, as the dashboard already does ("Summarised by hand"),
  so a hand-written summary never reads as something this tool generated.
- Keep the source link on the item. A summary is triage; it never replaces reading the source.
- `EMAIL_DIGEST_PLAN.md` already lists this as a success criterion, so this finishes a built
  feature rather than adding one.
- No cost and no new source: the summary is already in the digest file on disk.

Built, 17 September 2026 — `attach_saved_summaries` puts summaries already recorded in the digest
back onto freshly fetched items, so a run that emails or WhatsApps the week carries them. Both
renderers show the summary above the publisher's teaser, never instead of it, and label who wrote
it through one shared `summary_origin`: "Summarised by hand", or "Summarised by a local model
(qwen3:8b)". The dashboard now uses the same wording rather than falling through to a bare
"Summary", which read as though this tool had written it.

## 5. Switch on the Gmail newsletter intake

Four configured sources publish no feed and arrive only as email: ABS, FS Industry Moves,
Macquarie Technical Services and CFS FirstTech. Two of those are ACT-flagged. The code to read
them exists and is tested; it has never run, so those sources reach no digest.

Requirements:

- What is missing is `credentials.json` (a Google OAuth desktop client), not code. `--gmail` and
  `src/gmail_reader.py` are built, and the test suite (140 when this was written, 202 as of
  17 Sep 2026) passes without it.
- The boundary stays as `.github/copilot-instructions.md` sets it: read-only, the
  `industry-update-monitor` label only, no attachments, no link-following, no Gmail writes.
- Do not enable Google Cloud billing or a free trial. Stop if billing is required.
- Reading-time impact: up to 25 newsletters a run. Start at `--gmail-max 10` and see what it does
  to the length of a sweep before making it routine.
- Until this is on, treat ABS, Macquarie and CFS as bookmark-and-check in the weekly sweep, and
  do not read a quiet digest as "nothing happened there".

## 6. A weekly run that does not depend on remembering

There is no schedule. Every digest exists because someone ran the command, which makes the
habit the tool was built to support the one part it does not support.

Requirements:

- Cheapest first: a local `launchd` or `cron` entry costs nothing and needs no hosting. GitHub
  Actions is also free but needs the repo pushed — see item 8.
- A scheduled run must not be able to send email or WhatsApp unless those credentials are
  deliberately present. The default stays "write the digest, send nothing".
- A failed or empty fetch must say so. An empty digest that looks like a successful quiet week is
  worse than an error.
- No new source and no new cost: this reruns what already runs.

### Proposed plan, 17 September 2026 — for approval, not yet built

A single `launchd` agent on this laptop. Not GitHub Actions: that needs item 8's remote, which is
blocked, and it would put the digest on someone else's machine for no gain.

- **File:** `~/Library/LaunchAgents/com.advice-monitor.weekly.plist`, loaded once with
  `launchctl load`. Nothing installed, nothing running in the background between firings.
- **When:** Monday 07:00. `launchd` runs a missed job when the laptop next wakes, which `cron`
  does not — that matters on a machine that is closed at night.
- **What it runs:** `.venv/bin/python src/monitor.py --json --sweep --brief`, from the repo root.
  That refreshes the dashboard's `web/lib/digest.json`, writes the week's sweep sheet and the
  briefing. Nothing else.
- **What it must not do:** no `--email`, no `--whatsapp`, no `--gmail`. The default stays *write
  the digest, send nothing*. Delivery stays a thing you trigger, so a scheduled job can never
  send on your behalf while you are not looking.
- **When it fails:** stdout and stderr to `output/weekly-run.log`, and the run appends a dated
  one-line result — items fetched, or the error. An empty digest that reads as a quiet week is
  the specific failure this must not produce, so *nothing fetched* has to look different from
  *nothing happened*.
- **Turning it off** is one command, `launchctl unload`, and deleting the file. Worth writing into
  `SETUP.md` alongside turning it on, since a schedule you cannot stop is worse than none.

Open question for the owner: Monday 07:00 assumes you read this at the start of the week. If the
sweep actually happens Friday afternoon, say so and the time changes — the habit sets the
schedule, not the other way round.

Cost: nothing. No hosting, no account, no new source.

Built and installed, 17 September 2026 — **Monday 07:00**, chosen by the owner. The agent is
`~/Library/LaunchAgents/com.advice-monitor.weekly.plist` (template in `scripts/`), running
`scripts/weekly-run.sh`. Registered and verified: `runs = 0`, waiting for Monday, and `RunAtLoad`
is deliberately absent so installing the schedule did not trigger a run.

Testing it before Monday found a flaw in the plan above: `--sweep` refuses to overwrite an
existing sweep sheet, because that sheet may hold your ticks. Correct behaviour, but it would have
written a false ERROR into the log every time a sheet already existed. The runner now leaves an
existing sheet untouched and refreshes only the digest and briefing, saying so in the log. Second
test run: exit 0, 50 items, sheet intact.

Off switch documented in `SETUP.md` alongside the on switch, since a schedule you cannot stop is
worse than none.



## 7. Decide the database question instead of half-answering it

`web/lib/supabase.ts` and `database/schema.sql` are written but connected to nothing — the
dashboard reads `web/lib/digest.json`. The plan reads as though this were done.

Requirements:

- Consequence today: read/unread state lives in one browser's local storage. Clearing browsing
  data loses it, and it does not follow you to another device. `web/app/dashboard.tsx` says so in
  a comment; nothing user-facing does.
- Decide one way: connect it, or delete the unused code and correct `WEB_PLATFORM_PLAN.md`.
  Either is honest. Keeping both is what makes the plan misleading.
- Privacy: a hosted database moves teasers and links off this laptop. Free tier only, and no
  paid tier without a reason that has already been felt.
- Storage boundary is unchanged either way — teaser and link, never article text.

Decided and done, 17 September 2026 — **deleted**. `web/lib/supabase.ts` is removed and
`@supabase/supabase-js` is out of `web/package.json`; `tsc --noEmit` passes, which confirms
nothing was importing it. `WEB_PLATFORM_PLAN.md`, `INTEGRATIONS.md` and `README.md` now say the
dashboard reads a JSON file rather than promising a database.

The cost, recorded rather than buried: read state stays in one browser's local storage. It does
not follow you between machines. Chosen deliberately over a hosted database, which would have
moved teasers and links off this laptop for a benefit that has not been felt.



## 8. Keep the current work on the shelf copy, and off this laptop

Updated 17 September 2026. **The merge half of this item is done.** `main` is at `adf1079`, and
every branch — `fix/classification-and-delivery`, `docs/whatsapp-implementation`,
`docs/handover-whatsapp-ollama-zip`, `feat/ollama-and-summaries-everywhere` — is fully contained
in it, none of them ahead by a single commit. The shelf copy no longer misrepresents the project.

What is left is the off-this-laptop half, and it is blocked. There is still no git remote, so
this machine is still the only copy of the work.

**The name is taken, by something else.** `github.com/ahaythorpe/advice-monitor` already exists
and is **public**. It was created 1 September 2026 with a history unrelated to this repo, and it
holds the `web/` dashboard only — the Next.js app, `app/`, `components/`, `next.config.ts`. The
local `web/.vercel` folder suggests it is what Vercel deploys. Pushing this repo to that remote
would overwrite a live public site with unrelated history. Do not do it.

Requirements:

- Push to a **separate, private** repo under a different name, and check with whoever published
  the demo before choosing it, so two repos with near-identical names do not become a trap later.
- Private rather than public, because of what travels with this repo and does not travel with the
  demo: which newsletters are subscribed to (`free_subscriptions/`), a filed advice document
  (`data/filed_example_2026-08-19.md`), and the mailbox setup. None of that is a credential; all
  of it is a working life, and none of it has to be world-readable to be backed up. The demo is
  public on purpose — it is a shop window with nothing behind it. Different thing, different call.
- Secrets verified on 17 September 2026 rather than assumed: `.env`, `.env.*`, `credentials.json`
  and `token.json` are git-ignored, and `git log --all` shows that none of them has ever been
  committed, on any branch.
- Free: a private GitHub repo costs nothing at this size.

## 9. Correct the plans that describe things that were never built

Several planning docs describe switches and finished milestones that do not exist. The repo's own
rule is that a feature which is not configured must not appear to work.

Requirements:

- `USE_AI` appears in `EMAIL_DIGEST_PLAN.md` and `WEB_PLATFORM_PLAN.md` as a working switch. It
  exists nowhere in the code.
- `WEB_PLATFORM_PLAN.md` lists its MVP criteria as met — worker writes to the database, dashboard
  reads from it, read state persists. None of those are true. See item 7.
- `PRD.md` Phase 1 still says the next step is running it on real feeds; it has been run. The
  Phase 2 status line predates the Gmail work in `src/gmail_reader.py`.
- The `SAFEGUARDS.md` build checklist stays unticked, correctly — those boxes gate items 1 and 2
  of this list and nothing has passed them.
- Costs nothing and changes no behaviour. It decides whether the next person can trust the docs.

Done, 17 September 2026 — and it was worse than this item recorded. `USE_AI` was in **four** docs,
not the two named above, and one of them told you to do something impossible.

- `EMAIL_SETUP.md` instructed the reader to "flip `USE_AI = True`" and run `--email --ai`.
  Neither the switch nor the `--ai` flag has ever existed. That section now states plainly that
  there is no switch, no key and no per-week cost, and points at the two routes that are real:
  `--ollama` and `--import-summaries`.
- `EMAIL_DIGEST_PLAN.md` passed `use_ai=USE_AI` into a function signature that never took it, and
  promised AI summaries would "just work" with no code change. Corrected in place, with the step
  marked done-differently rather than deleted.
- `WEB_PLATFORM_PLAN.md` ticked all eight MVP criteria ✅. Checked line by line against the code:
  three are true, one is true only in `localStorage` on one browser, and three are false — the
  worker writes `web/lib/digest.json`, the dashboard reads that file, and `web/lib/supabase.ts`
  is **imported by nothing**. Replaced with a table of what actually passes.
- `BUILD_STEPS.md` told the reader to set the flag "wherever it lives". Marked never-built.
- `PRD.md` Phase 1 said the next step was running it on real feeds; it has been run for weeks.
  Phase 2's status predated the Gmail work and now says the honest thing: the code is built and
  tested, has never run, and is waiting on `credentials.json`.

Verified rather than assumed: `grep -rn USE_AI` over `src/`, `web/` and `tests/` returns nothing,
and there is no `anthropic`, `openai` or `api_key` anywhere in `src/`. The docs were describing a
paid AI integration this repo has never had.



## 10. WhatsApp delivery, finished properly

Sending works from the command line and the formatting is tested on both sides. What is not
finished is the part that decides whether it can be deployed at all.

Requirements:

- `POST /api/whatsapp/send` takes the recipient from the request body and has no authentication
  and no rate limit. Deployed with Twilio credentials present, anyone with the URL can send on
  the account. Close it, or keep sending on the command line and say so in the docs that
  currently describe the endpoint.
- A summary pasted back by hand never reaches WhatsApp — see item 4, same cause.
- The sandbox's 24-hour window and 72-hour join are facts to report, not to retry around. The
  agent rules ban retry loops, and a retry against a messaging API is how a free trial becomes a
  bill.
- Cost stays nil: trial credit, shared sandbox number, never buy a number, never upgrade.
- The four ways to close the endpoint, with trade-offs and a recommendation, and the jobs
  either side of it: [WHATSAPP_IMPLEMENTATION.md](WHATSAPP_IMPLEMENTATION.md). Brief:
  [HANDOVER.md](HANDOVER.md), stream A.

Checked 17 September 2026, before deciding anything: **nothing is exposed today, and there was
nothing to remove.** `vercel env ls` on the linked project returns "No Environment Variables
found", so the deployed dashboard cannot send — it previews. The public repo's full history was
cloned and scanned: no `.env`, no credentials file, and no token-shaped string in any of its 7
commits; every Twilio reference is `process.env.NAME`.

That does not close the item, it only dates it. The endpoint is still a send-to-anyone API the
moment a credential is added, and it is published at `github.com/ahaythorpe/advice-monitor` for
anyone to read. The fix is still A or B above, and it should land before Twilio is ever
configured, not after. `WHATSAPP_SETUP.md` now carries the two commands to re-check this and the
masked shape of where the credentials belong.



## 11. Summaries from a model on this machine (Ollama)

Phase 3 without a key and without a bill. The cost gate that blocks item 2 does not apply — there
is no per-call price — so this is the cheapest route to automated summaries the project has.

Requirements:

- Reuse the manual round trip: the prompt, the blocks, the reply format and the ID matching all
  exist and are tested. This is a transport, not a new feature.
- The input stays the feed's own title and teaser. A local model is not a reason to fetch an
  article body.
- Record the origin as `ollama:<model>` and label it in the dashboard as a local model. A summary
  that reads as "Summary" with no origin breaks the honesty rule by omission.
- Off unless asked for, capped, and loud when Ollama is not running. No retry loop and no
  fallback to anything paid.
- The only network call is to 127.0.0.1, asserted in a test that runs with no model installed.
- Costs: no money. ~5 GB of disk, ~8 GB of memory while it runs, and a warm laptop.
- Install, model choice, a curl that proves it before any code, and the wiring:
  [OLLAMA_SETUP.md](OLLAMA_SETUP.md). Brief: [HANDOVER.md](HANDOVER.md), stream B.

Built, 17 September 2026 — `--ollama`, nine tests against a fake Ollama on localhost, and a real
run through `qwen3:8b`. It refuses any host but this machine, caps a run at ten pastes, writes
the model's raw reply to disk before importing a word of it, and reports rather than retries.

Still open, and the reason this is not finished business:

- Whether a local model is good enough to trust for KNOW items. On the first real run, one of
  three summaries added a word the teaser did not contain. That is a reading question, not a
  code question, and only weeks of sweeps answer it.
- `--deep` through a local model is untested. The prompt exists; the second pass sends far more
  text per paste and will be much slower.

## 12. A download an AI tool can be handed as-is

Every item's link is already in the download, on its own `LINK:` line, and the prompt tells the
model to keep it. What is missing is everything around them: unzip today and you get a handful of
Markdown files with no entry point.

Requirements:

- A `README.md` inside the zip: which digest it came from, how many items and pastes, what to do
  with it, and the one-line boundary — titles and teasers only, do not ask a tool to fetch the
  links.
- A `links.md` inside the zip: every item once, with ID, flag, source, date, title and URL. That
  is the list to hand to a tool or to open by hand.
- A newsletter's link is a mailbox URL only its owner's browser can open, and must be labelled
  rather than offered as a public article. Test `intake == "email"`; `email_newsletter` is the
  sources.json value and reaches no item.
- The command line writes the same two files, and the existing parity test covers them. Two
  routes, one output, or they drift.
- The prompt stays SAFEGUARDS section D verbatim and the IDs stay the monitor's refs, or
  `--import-summaries` attaches a summary to the wrong article.
- Costs nothing and reaches no publisher: it is built in the browser from the digest already
  loaded. Brief: [HANDOVER.md](HANDOVER.md), stream C.

## 13. Government sources that publish no feed

The tracker now carries one government feed, APRA's, and it is the only one. Everything else
official is a manual check, which means the ACT tier depends on you remembering to look.

Checked 17 September 2026:

- **APRA** — `apra.gov.au/rss.xml` is live and current, and every entry is a statistics
  publication. Added with a NOTE prior. Its enforcement and prudential announcements are not in
  it and have no feed of their own.
- **ATO** — no feed anywhere. `/rss/mediareleases.xml`, `/rss.xml`, `/feed`,
  `/about-ato/media-centre/rss` and `/newsroom/smallbusiness/rss` all 404, and neither the media
  centre nor the newsroom advertises one. Added as bookmark-and-check with an ACT prior, since
  the ATO both administers tax and regulates SMSFs.
- **Treasury** — `treasury.gov.au/rss.xml` still parses and is still empty.
  `ministers.treasury.gov.au/rss.xml` parses and its newest entry is 11 May 2023: a valid, stale
  feed, and the reason a new source is probed for current items before it is added.
- **ASIC, AFCA, ABS** — unchanged, no usable feed.

Requirements, if this is taken further:

- Re-probe every few months. A regulator that has no feed today may have one next year, and the
  notes in `data/sources.json` record what was tried so the next probe is quick.
- An email alert is the honest fallback where a body offers one — ABS already works that way,
  and `--gmail` reads them. That is item 5.
- Do not scrape a media centre page to fake a feed. The rule is feeds in, free sources out, and
  a page is not a feed.
- Costs nothing either way: both routes are free public publishing.

## 14. Government bodies that are not on the source list at all

Item 13 covers the bodies already on the list that publish no feed. This one covers the bodies
that were never added. Probed 17 September 2026, to the same standard item 13 sets: a feed counts
only if it carries *current* items, because a valid stale feed is the trap.

- **Tax Practitioners Board (TPB)** — `tpb.gov.au/rss.xml` is live and current: 10 entries,
  newest dated 17 September 2026, recent items covering sanctions-power guidance and registration
  terminations. The strongest candidate on this list, and an ACT prior on the face of it, since
  the TPB registers tax (financial) advisers and its terminations and guidance change what an
  adviser may do. The only working government feed found in this probe.
- **AUSTRAC** — no feed. `austrac.gov.au/rss.xml`, `/feed` and `/news/rss` all 404, and the news
  and media page advertises none in its HTML. Bookmark-and-check would be the intake. Worth
  weighing because the AML/CTF changes reach into advice practices rather than staying with banks.
- **CSLR** — `cslr.org.au/feed` parses and carries 10 entries, but the newest is 2 July 2026, so
  it is a low-volume publisher rather than a live wire. Relevant — the CSLR levy is what the
  filed example of 19 August 2026 is about — but it would earn a NOTE prior, not an ACT one.
- **Federal Register of Legislation** — `legislation.gov.au/rss.xml` returns HTML, not a feed.
  Nothing to configure.

Requirements, if this is taken further:

- Add nothing on the strength of this probe alone. A source earns its place by publishing things
  worth reading over a few weeks, not by having a feed that responds.
- Watch reading time before the flag. TPB looks to publish roughly weekly; an ACT prior puts every
  one of those items in front of you at every sweep, which is the cost that item 3 is protecting.
- Record what was probed in `data/sources.json`, the way ASIC, ATO and Treasury already record
  theirs, so the next probe is quick.
- Do not scrape a media centre to fake a feed for AUSTRAC. Same rule as item 13: a page is not a
  feed.
- Costs nothing either way: all four are free public publishing.

Added, 17 September 2026, on the owner's instruction — the three probed above are now in
`data/sources.json`, and the monitor fetches them:

- **Tax Practitioners Board** — 🔴 ACT, RSS. Live on the first run: a Royal Assent item on the
  enhanced sanctions framework, dated the same day, plus a registration termination.
- **AUSTRAC news** — 🟠 KNOW, bookmark-and-check, since it has no feed. KNOW rather than ACT
  because AML/CTF obligations reach advice practices but rarely demand action in the week they
  are announced.
- **CSLR** — 🟢 NOTE, RSS. Configured despite being slow, with the prior set to match how rarely
  it speaks.

This goes against the caution written above — that a source should earn its place over a few
weeks rather than on one probe. That was the owner's call to make, and it is recorded here rather
than quietly overridden. What to watch, in this order: whether the TPB's weekly volume makes the
sweep too long at an ACT prior, and whether CSLR is worth keeping if it stays silent.

Known quirk, recorded so it is not rediscovered as a bug: the TPB feed's description repeats the
title and appends an internal ID, the date and the category before the real text, so its teasers
read oddly. The title and the link are correct, and an ACT item is read at its source anyway.

`legislation.gov.au` was not added — it serves HTML, not a feed. Nothing to configure.

