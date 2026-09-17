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
  `src/gmail_reader.py` are built, and 140 tests pass without it.
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

## 8. Keep the current work on the shelf copy, and off this laptop

As of 17 September 2026 every commit of the previous three weeks sits on
`fix/classification-and-delivery`. `main` is still at 31 August, and there is no git remote, so
the only copy of the work is this machine.

Requirements:

- Merge the branch into `main` so the shelf copy stops misrepresenting the project.
- Then push to a private GitHub repo. `README.md` already documents the push and assumes it has
  happened.
- Confirm before the first push that nothing secret goes with it. `.env`, `credentials.json` and
  `token.json` are git-ignored; verify rather than assume.
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
