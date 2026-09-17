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
