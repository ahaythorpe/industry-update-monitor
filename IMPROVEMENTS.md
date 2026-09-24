# Improvement list

These are deliberately staged ideas. An improvement is not ready to build until its cost,
privacy, source, and reading-time impact are understood.

Items 1 and 2 were staged early; item 1 was built on 17 September 2026 and item 2 is unstarted.
Item 3 now has the sweep sheet under it; the habit it serves is still the user's. Items 4-9 came out of a review of
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
- `archive/EMAIL_DIGEST_PLAN.md` already lists this as a success criterion, so this finishes a built
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

Status, 23 September 2026 — **still not connected.** There is no `credentials.json`, and `--gmail`
has never run (the suite is 209 tests now, still passing without it). A Gmail label called "Advice
Monitor" exists, but `src/gmail_reader.py` reads only a label named exactly
`industry-update-monitor` and refuses any other, so that label is not read. The steps, and the
label note, are [SETUP.md Part 4](SETUP.md#part-4--the-gmail-newsletter-intake).

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

Extended, 23 September 2026 — after the digest, `scripts/weekly-run.sh` now runs `--ollama` (item
11) as a separate step, logged on its own line. If Ollama is not answering on localhost it logs
`SUMMARIES SKIPPED` and the digest is untouched. Still no `--email`, `--whatsapp` or `--gmail`:
summarising stays on this machine, so the "send nothing" default holds.



## 7. Decide the database question instead of half-answering it

`web/lib/supabase.ts` and `database/schema.sql` are written but connected to nothing — the
dashboard reads `web/lib/digest.json`. The plan reads as though this were done.

Requirements:

- Consequence today: read/unread state lives in one browser's local storage. Clearing browsing
  data loses it, and it does not follow you to another device. `web/app/dashboard.tsx` says so in
  a comment; nothing user-facing does.
- Decide one way: connect it, or delete the unused code and correct `archive/WEB_PLATFORM_PLAN.md`.
  Either is honest. Keeping both is what makes the plan misleading.
- Privacy: a hosted database moves teasers and links off this laptop. Free tier only, and no
  paid tier without a reason that has already been felt.
- Storage boundary is unchanged either way — teaser and link, never article text.

Decided and done, 17 September 2026 — **deleted**. `web/lib/supabase.ts` is removed and
`@supabase/supabase-js` is out of `web/package.json`; `tsc --noEmit` passes, which confirms
nothing was importing it. `archive/WEB_PLATFORM_PLAN.md`, `archive/INTEGRATIONS.md` and `README.md` now say the
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

Done, 17 September 2026 — pushed to a separate **private** repo,
`github.com/ahaythorpe/industry-update-monitor`, which is now `origin`. The public
`ahaythorpe/advice-monitor` is untouched and must stay that way. Pushing is by hand, so `main` can
sit a few commits ahead of `origin` between pushes.

## 9. Correct the plans that describe things that were never built

Several planning docs describe switches and finished milestones that do not exist. The repo's own
rule is that a feature which is not configured must not appear to work.

Requirements:

- `USE_AI` appears in `archive/EMAIL_DIGEST_PLAN.md` and `archive/WEB_PLATFORM_PLAN.md` as a working switch. It
  exists nowhere in the code.
- `archive/WEB_PLATFORM_PLAN.md` lists its MVP criteria as met — worker writes to the database, dashboard
  reads from it, read state persists. None of those are true. See item 7.
- `archive/PRD.md` Phase 1 still says the next step is running it on real feeds; it has been run. The
  Phase 2 status line predates the Gmail work in `src/gmail_reader.py`.
- The `SAFEGUARDS.md` build checklist stays unticked, correctly — those boxes gate items 1 and 2
  of this list and nothing has passed them.
- Costs nothing and changes no behaviour. It decides whether the next person can trust the docs.

Done, 17 September 2026 — and it was worse than this item recorded. `USE_AI` was in **four** docs,
not the two named above, and one of them told you to do something impossible.

- `archive/EMAIL_SETUP.md` instructed the reader to "flip `USE_AI = True`" and run `--email --ai`.
  Neither the switch nor the `--ai` flag has ever existed. That section now states plainly that
  there is no switch, no key and no per-week cost, and points at the two routes that are real:
  `--ollama` and `--import-summaries`.
- `archive/EMAIL_DIGEST_PLAN.md` passed `use_ai=USE_AI` into a function signature that never took it, and
  promised AI summaries would "just work" with no code change. Corrected in place, with the step
  marked done-differently rather than deleted.
- `archive/WEB_PLATFORM_PLAN.md` ticked all eight MVP criteria ✅. Checked line by line against the code:
  three are true, one is true only in `localStorage` on one browser, and three are false — the
  worker writes `web/lib/digest.json`, the dashboard reads that file, and `web/lib/supabase.ts`
  is **imported by nothing**. Replaced with a table of what actually passes.
- `archive/BUILD_STEPS.md` told the reader to set the flag "wherever it lives". Marked never-built.
- `archive/PRD.md` Phase 1 said the next step was running it on real feeds; it has been run for weeks.
  Phase 2's status predated the Gmail work and now says the honest thing: the code is built and
  tested, has never run, and is waiting on `credentials.json`.

Verified rather than assumed: `grep -rn USE_AI` over `src/`, `web/` and `tests/` returns nothing,
and there is no `anthropic`, `openai` or `api_key` anywhere in `src/`. The docs were describing a
paid AI integration this repo has never had.



## 10. WhatsApp delivery, finished properly

> **Retired 23 September 2026 — see [item 15](#15-telegram-replaces-whatsapp-as-the-phone-channel).**
> The phone channel is now Telegram. What follows is kept as the record of how the send
> endpoint's safety rule was decided; that rule carried over to Telegram unchanged.

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
  either side of it: [archive/WHATSAPP_IMPLEMENTATION.md](archive/WHATSAPP_IMPLEMENTATION.md). The
  decision now lives in [HANDOVER.md](HANDOVER.md#telegram-the-phone-channel-and-why-not-whatsapp).

Checked 17 September 2026, before deciding anything: **nothing is exposed today, and there was
nothing to remove.** `vercel env ls` on the linked project returns "No Environment Variables
found", so the deployed dashboard cannot send — it previews. The public repo's full history was
cloned and scanned: no `.env`, no credentials file, and no token-shaped string in any of its 7
commits; every Twilio reference is `process.env.NAME`.

That does not close the item, it only dates it. The endpoint is still a send-to-anyone API the
moment a credential is added, and it is published at `github.com/ahaythorpe/advice-monitor` for
anyone to read. The fix is still A or B above, and it should land before Twilio is ever
configured, not after. The two commands to re-check this, and the masked shape of where the
credentials belong, were in SETUP.md Part 5, now [archive/WHATSAPP_TWILIO_RETIRED.md](archive/WHATSAPP_TWILIO_RETIRED.md).

Closed, 17 September 2026. The endpoint took option A — it reads `WHATSAPP_TO` from the server
environment and ignores the request's recipient — and the dashboard's recipient box is gone rather
than left as a field that does nothing. Both warnings that described the old behaviour were
rewritten, since a fix that leaves the warnings stale is half a fix.

The second requirement above was still open after that: a summary pasted back by hand reached the
command line's WhatsApp but not the dashboard's. Item 4 fixed `src/whatsapp_sender.py` and missed
`web/lib/whatsapp.ts`, so the button sent the publisher's teaser and dropped the summary silently.
Fixed the same way as the Python side — labelled with who wrote it, above the teaser rather than
instead of it — with three tests so it cannot drift again unnoticed. That miss is the argument for
the parity tests item 12 asks for.

Left open, checked against the code on 23 September 2026 — none of it blocks use, all of it is in
the web route: `perFlagLimit` is not clamped, a Twilio refusal is reported as a bare HTTP status
rather than translated the way the command line does it, and a partial send does not say how many
parts arrived. Not fixed on the WhatsApp route — it was removed on 23 September 2026 — but all
three are fixed in the Telegram route that replaced it (item 15).



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
  [SETUP.md Part 2](SETUP.md#part-2--ollama-summaries-from-a-model-on-this-laptop). Constraints:
  [HANDOVER.md](HANDOVER.md#summaries-the-round-trip-and-ollama).

Built, 17 September 2026 — `--ollama`, nine tests against a fake Ollama on localhost, and a real
run through `qwen3:8b`. It refuses any host but this machine, caps a run (now 12 pastes of 5 items, 10 minutes each), writes
the model's raw reply to disk before importing a word of it, and reports rather than retries.

Since 23 September 2026 it also runs in the Monday job (item 6), with `OLLAMA_MODEL=qwen3:8b` in
`.env`. A 50-item week takes about 20 minutes.

Since 24 September 2026 the weekly run uses `gpt-oss:20b` instead (item 16), passed on the
command line with a 30-minute timeout per paste, and runs Sunday 21:00 rather than Monday 07:00
because a week now takes about 2.5 hours.

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
  loaded. Brief: [HANDOVER.md](HANDOVER.md#the-download-bundle).

Built, 17 September 2026. `README.md` and `links.md` are written into both routes' output:
`web/lib/bundle.ts` for the dashboard's zip, `format_bundle_readme` and `format_bundle_links` in
`src/monitor.py` for `--group-by`, which now leaves them in the briefing folder beside the
Markdown files.

The README names the digest and its date, counts the items, files and pastes, gives the four
steps of the round trip, and carries the boundary in the bundle rather than only in the repo —
titles and teasers only, do not ask a tool to fetch the links, and a 🔴 ACT item is read at its
source regardless. `links.md` is every item once with ID, flag, source, date, title and URL.

A newsletter is tested rather than assumed: `intake == "email"` is labelled "opens in your own
mailbox, not a public page" and is deliberately not offered under "Link:", because that URL only
opens for its owner's browser. Six tests either side cover the pair, including that a feed item
is still offered as a link and a newsletter never is.



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



## 15. Telegram replaces WhatsApp as the phone channel

Decided 23 September 2026 by the owner. **Why:** the Telegram Bot API is free for good — no
trial, no balance, no per-message charge, no card — while every WhatsApp route ends up costing
money: Twilio's trial credit runs out and then each message is a few cents, and Meta's own
WhatsApp Business route needs business verification and bills per conversation. WhatsApp also
refuses a message unless you have messaged it in the last 24 hours, which a weekly digest always
trips over. A free tool should not depend on a balance.

Built, 23 September 2026:

- `src/telegram_sender.py` and `python src/monitor.py --telegram [--from-digest]`. Sends only to
  `TELEGRAM_CHAT_ID` — your own chat with your own bot, **@advicemonitor_bot** — and previews
  without settings. `find_chat_id` finds the chat ID after you press Start on the bot.
- The dashboard's WhatsApp section became **Send this digest to Telegram**
  (`POST /api/telegram/send`, `web/lib/telegram.ts`). Same safety rule as item 10: the recipient
  comes from the server environment, never the request. The three gaps item 10 left open on the
  web route are closed here — the per-flag limit is clamped, Telegram's refusal is put into plain
  words, and a failure part-way says how many parts had arrived. `/api/status` reports Telegram
  as live only when both the token and the chat ID are present.
- Tests on both sides: `tests/test_telegram.py`, `web/lib/telegram.test.ts`.
- Docs: [SETUP.md Part 5](SETUP.md#part-5--telegram--free) is now the Telegram setup; the old
  Twilio page is [archive/WHATSAPP_TWILIO_RETIRED.md](archive/WHATSAPP_TWILIO_RETIRED.md).

Retired, not deleted: `src/whatsapp_sender.py` and `--whatsapp` still work and are still tested,
but are optional and not recommended. The dashboard's WhatsApp button, route, formatter and their
tests were removed.

Still open: the Monday run sends email only. Whether it also sends to Telegram is the owner's to
decide in `scripts/weekly-run.sh`. For the dashboard button to send rather than preview, the two
`TELEGRAM_` values also have to go in `web/.env.local` — never in Vercel.

---

## 16. Read on the dashboard, in plain English

Asked for 23 to 24 September 2026 by the owner: the newsletter was getting long, the summaries
were vague and full of acronyms, and the dashboard should organise the week itself rather than
lean on pasting into a chat.

Built, 24 September 2026:

- **Summaries.** `NEWSLETTER_PROMPT` asks for three or four short dot points in plain English,
  each carrying a real fact in bold; acronyms as plain words with the acronym in brackets; no
  filler such as "advisers should stay informed"; care with figures in tables. The local model
  now reads the whole article text the feed carries (`FEED_BODY_LIMIT` 12,000, up from 1,500),
  with `num_ctx` raised so the prompt is not silently cut. Chat pastes stay at 3,000 characters
  (`PASTE_BODY_LIMIT`). Replies that start `ID: ` now import.
- **Dashboard.** By urgency and By topic boxes that open into a pop-up with every story; dotted
  glossary terms with their meaning on hover or tap; a ⬇ on every box, pop-up and the whole week
  for a Markdown file to share or give an AI tool (`web/lib/sweep.ts`, never article text); the
  AI-chat export folded under Advanced; plain labels throughout.
- **Newsletter.** Plain labels (Act now, Worth knowing, Background), topic icons and urgency
  bars, every story with its dot points, a 📖 box under each story explaining its terms, a
  👀 Read these yourself list for stories the model could not read, a 📖 Jargon buster, and
  topics as drop-downs (open in the email, so Gmail loses nothing).
- **Alert mode.** With `DASHBOARD_URL` set, the email and Telegram message become a one-minute
  Act now alert with a link to the dashboard. Off until the dashboard is online.
- **Telegram button.** `web/lib/telegram.ts` rewritten to send the same single message as
  `--telegram`.
- **Link check.** HEAD only; a refusal leaves the link unchecked instead of opening the page
  with a GET (`tests/test_link_check.py`, SAFEGUARDS.md section A).

Still open:

- ~~**Which model writes the summaries.**~~ Decided 24 September 2026: `gpt-oss:20b`, with the
  run moved to Sunday 21:00 so the week is ready by Monday. On a test of three stories `qwen3:8b` misread a money
  table ("Dixon Advisory will pay $83.5M", which was the cost of its collapse), one story at a
  time or three. `gpt-oss:20b` got the facts right but takes about 2.5 hours a week. Claude Haiku
  would cost about US 8 cents a week on a prepaid credit. The owner's to decide.
- ~~**Putting the dashboard online**~~ Done 24 September 2026, **public with no login**, at the
  owner's request: see item 18. Alert mode stays off.
- **"This week in 30 seconds"**, deadlines as tags, and plain headlines: suggested, not built.

## 17. Official and fund-manager sources through Gmail

ASIC, AFCA determinations, Treasury, ABS and the ATO publish no usable feed (checked
24 September 2026: Treasury's `rss.xml` is empty, AFCA blocks automated requests), so they reach
the digest only second-hand through the trade press. Macquarie is signed up but arrives by email,
which the Monday run does not read. Canaccord Genuity Wealth and Morgan Stanley publish their
investment views by newsletter too.

Proposed, not built: sign up to each body's free email alerts, file them under the
`industry-update-monitor` label with one Gmail filter, give `src/gmail_reader.py` its read-only
access once, add `--gmail` to the Monday run, and show the fund-manager views as their own
📈 Big-picture investing topic, with official releases marked as such. Needs the owner for the
sign-ups and the one Google sign-in.

## 18. A public dashboard, with past weeks

Asked for 24 September 2026 by the owner: a link other people can open, updated by itself, that
keeps earlier weeks.

Built, 24 September 2026:

- **Public at https://advice-monitor.vercel.app**, the `advice-monitor` Vercel project, deployed
  from `web/` with `vercel deploy --prod`. Hosted mode (item 16) hides the owner's settings and
  sending, and never serves article text. The project holds **no environment variables**; keep
  it that way. The public GitHub repo of the same name is not the deploy source and is untouched.
- **Updated by the Sunday run**, as its last step. A deploy swaps in whole, so readers see last
  week until the new one is ready, and a failed deploy leaves last week up and says so in the log.
- **Past weeks.** `scripts/archive_week.py` saves each week, without article text, to
  `web/lib/archive/<Monday>.json`; a Sunday run counts toward the Monday after it. The dashboard
  links to `/archive`, and each week is a static page at `/week/<Monday>`. Backfilled from git
  history for the weeks of 7, 14 and 21 September.

Left as is, by the owner's choice: urgency labels stay as they are, and the email and Telegram
stay the full newsletter.
