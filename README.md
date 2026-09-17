# Industry Update Monitor

A free-first monitoring project for the Australian financial advice industry.

## What it does
Every week it reads eight public RSS feeds from the Australian financial advice
press and the prudential regulator, flags each article ACT / KNOW / NOTE with a
confidence score, checks that every link resolves, and emails you the result.
No API key and no per-run cost by default; summaries are optional and can run
on a model on your own machine. Nothing behind a paywall.

Feeds currently configured: Financial Standard, Professional Planner, FAAA,
Riskinfo, Money Management, ifa, SMSF Adviser, and APRA. ASIC, the ATO, ABS and
AFCA publish no usable feed, so those stay on the manual weekly check — each
one's entry in [data/sources.json](data/sources.json) records what was probed
and when.

## Core rule
Feeds in, free sources out. Never fetch, store, or reconstruct anything behind a paywall.

The project only reads content the publisher has made public, and it treats AI/email features as optional, explicit, and reversible.

## What is included
- Python monitor, classifier and source logic in [src/monitor.py](src/monitor.py)
- Email newsletter in [src/email_sender.py](src/email_sender.py)
- WhatsApp newsletter in [src/whatsapp_sender.py](src/whatsapp_sender.py)
- Gmail read-only helper in [src/gmail_reader.py](src/gmail_reader.py)
- Local Gmail dry-run script in [src/gmail_dry_run.py](src/gmail_dry_run.py)
- Optional web dashboard in [web/app/page.tsx](web/app/page.tsx)
- Source list in [data/sources.json](data/sources.json)
- project rules and planning docs in the root of the repo

## Quick start

New here, or setting up on another machine? **[SETUP.md](SETUP.md)** walks the
whole thing from prerequisites to a working digest, and links every optional
add-on with what it costs. The short version:

### Python CLI
```bash
cd /Users/bella/Projects/advice-monitor
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python src/monitor.py
```

#### Tuning the digest

Every item is flagged ACT / KNOW / NOTE by a weighted keyword classifier and
given a 0-1 confidence. No AI is involved. Confidence rises with how far the
winning score cleared its threshold and how far clear it stayed of the
runner-up, so a borderline call reads as borderline.

```bash
python src/monitor.py --flags ACT,KNOW --min-confidence 0.7   # only calls it is sure about
python src/monitor.py --days 7                                # last week only
python src/monitor.py --no-check-links                        # skip link validation (faster)
python src/monitor.py --sources                               # print the source list first
```

### Reading the digest

Every item carries a flag, a confidence, a whole-sentence summary drawn from the
publisher's own teaser, and a checked link.

```bash
python src/monitor.py --preview                    # output/digest_preview.html
python src/monitor.py --email                      # HTML newsletter by email
python src/monitor.py --whatsapp                   # WhatsApp newsletter
python src/monitor.py --whatsapp --per-flag 3      # top 3 per flag
```

`--whatsapp` sends through Twilio using `TWILIO_ACCOUNT_SID`,
`TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` and `WHATSAPP_TO`. **With no
credentials set it prints the exact messages it would send**, so the newsletter
can be proof-read for free. Long digests are split on item boundaries — never
mid-article — and a section continued into the next message repeats its heading.

| Flag | Default | Effect |
| --- | --- | --- |
| `--days` | 14 | Drop items older than N days (`0` = no limit) |
| `--min-confidence` | 0.0 | Drop items whose flag confidence is below this |
| `--flags` | `ACT,KNOW,NOTE` | Which tiers to include |
| `--limit` | 50 | Maximum items in the digest |
| `--no-check-links` | off | Skip the HEAD/GET check that drops dead links |
| `--per-flag` | 6 | Max items per flag in the WhatsApp newsletter |
| `--gmail` | off | Also read newsletters from the Gmail label (read-only, opt-in) |
| `--gmail-max` | 25 | Maximum newsletters to read |
| `--sweep` | `output/sweep-<date>.md` | Write a tickable sheet for the weekly sweep |
| `--ollama` | off | Summarise through a model on this machine (see [OLLAMA_SETUP.md](OLLAMA_SETUP.md)) |
| `--ollama-reply` | `output/ollama-reply.md` | Where the model's raw reply is kept for checking |
| `--brief` | `output/briefing.md` | Write a paste-ready briefing for an AI web tool |
| `--deep` | off | Detailed prompt and smaller pastes; pair with `--flags ACT,KNOW` |
| `--group-by` | — | Split that briefing into one file per group: `topic`, `flag`, or `topic,flag` |
| `--topic` | — | Brief only these categories, e.g. `Compliance,Regulation` |
| `--import-summaries` | — | Merge summaries pasted back from an AI web tool |
| `--digest` | `web/lib/digest.json` | The digest those two commands read and write |

A source's `flag` in `data/sources.json` is a **prior**, not a verdict — it
nudges the score in its direction, but the item's own words decide the flag.

#### Adding a source

A source is fetched if it has an `rss` URL, and `validate_feed_source` requires
it to be free, on the same host as `home`, and to look like a feed. Verify a new
feed returns current items before adding it — some publishers serve a valid but
stale or empty feed — `ministers.treasury.gov.au/rss.xml` parses perfectly and
its newest entry is from 2023. ASIC, the ATO, ABS and AFCA offer no usable feed
and stay bookmark-and-check. APRA's feed is live but carries only statistics
publications, so its prior is NOTE; its enforcement announcements have no feed.

### The weekly sweep

The digest tells you what arrived. The sweep sheet is for the reading itself —
one file a week, in the order the flags already imply, with somewhere to record
how long it took and what was worth it.

```bash
python src/monitor.py --sweep                    # output/sweep-2026-09-17.md
python src/monitor.py --sweep output/catch-up.md # or name the file yourself
```

Every item gets a box, its publication, its confidence, its teaser and its
link. Underneath is the record the habit needs: minutes, useful items, and a
table of what each publication actually gave you that week — the basis for
deciding, after several sweeps, which sources have earned their place.

It refuses to write over a sheet that already exists, because a sheet worked on
by hand is the only copy of that record. It reads the digest already on disk,
so like `--brief` it reaches no publisher and costs nothing.

A ticked ACT box means you went to the primary source. Nothing in the sheet
replaces that, and it says so at the bottom.

#### Terms you do not know yet

An item that uses `CSLR`, `anti-hawking` or `Div 296` names them under the
teaser, and the sheet explains each one once at the end, under **Terms on this
sheet**. The glossary is [data/glossary.json](data/glossary.json) — written by
hand, read from disk, no model and no key.

Each entry says what the term means, why it matters, and where to confirm it. A
settled term is stated plainly (`In plain English`); a proposal, threshold or
rule under review is marked `Possible meaning` and `Needs confirmation`, because
those are the ones where a summary is not good enough. A term is matched on its
own spelling — `ART` the tribunal is matched, `art` is not — so nothing is
inferred about what an item means. Four terms per item is the cap.

To add a term, add an entry to the glossary: `term`, `means`, `matters`,
`check`, optionally `also` for other spellings and `changing: true` if its
substance is still moving. The tests check every entry says what it means and
where to check it.

### Newsletters from Gmail

Four configured sources have no feed at all — ABS, FS Industry Moves, and the
two ACT-flagged product technical services, Macquarie Technical Services and
CFS FirstTech. They arrive in your inbox, so the digest never saw them.
`--gmail` reads them from one Gmail label and treats each one as a digest item:
same flags, same confidence, same dedupe, same dashboard.

```bash
python src/monitor.py --json --gmail        # feeds + newsletters
python src/monitor.py --gmail --gmail-max 10
```

Setup, once (all of it yours to do — the tool never asks for your password):

1. In Gmail, create a label `industry-update-monitor` and a filter that applies
   it to the newsletters you want read. Nothing outside that label is visible
   to the tool.
2. In Google Cloud Console, create an OAuth **desktop** client with the Gmail
   API enabled, download it as `credentials.json` in the repo root (it is
   git-ignored), and run with `--gmail`. Your browser handles the consent; the
   resulting `token.json` stays local.

The scope is `gmail.readonly` and `gmail_reader.py` refuses any label but the
configured one, so the tool cannot read the rest of your mail, and cannot send,
label, archive or delete anything. Without `credentials.json` the run says so
and stops; every other command works without Gmail.

A newsletter item links to the message in your own mailbox, so it is never
link-checked (that link redirects to a Google login for anything but your
browser) and the dashboard badges it **Newsletter** with an "Open in Gmail"
link rather than pretending it is a public article.

### Summaries from a model on this machine

The same round trip as below, with a local model doing the pasting. No key, no
account, no bill, and nothing leaves the laptop.

```bash
ollama serve                                     # in its own terminal
python src/monitor.py --json                     # this week's digest
python src/monitor.py --ollama                   # or: --ollama qwen3:8b
```

It reads the digest on disk, sends each paste to `127.0.0.1:11434`, and merges
the replies straight back in. The model's raw reply is kept at
`output/ollama-reply.md` — **read it.** A local model invents as readily as any
other: in the first real run here, one summary said an adviser was banned for
"incompetence", a word that appeared nowhere in the teaser. Summaries are
labelled `ollama:<model>` and shown as "Summarised by a local model", never as
this tool's own work, and an ACT item is still read at its source.

It refuses any host but localhost, caps a run at ten pastes, and never retries.
Narrow a big week with `--flags ACT,KNOW`. Install, model choice and the rest:
[OLLAMA_SETUP.md](OLLAMA_SETUP.md).

### Summaries without an API key

Phase 3 with you as the transport. The tool writes a briefing, you paste it
into an AI web tool, and you paste the reply back — no key, no cost, and the
prompt is [SAFEGUARDS.md](SAFEGUARDS.md) section D verbatim with an ID added so
replies can be matched to items.

```bash
python src/monitor.py --json                            # this week's digest
python src/monitor.py --brief                           # output/briefing.md, ~15 items per paste
#   paste each block into the AI web tool, save its reply as output/reply.md
python src/monitor.py --import-summaries output/reply.md
```

#### One paste per group

Every item carries a category as well as its flag: Compliance, Regulation,
Super & tax, Insurance, Key personnel movements, Business, Markets & investing,
Fees & pricing, Practice & technology, or **General** when no rule matches.

General is the fallback, not a subject: a large pile there means rules are
missing, not that there is a theme to read end to end. It sat at 19 of 50 items
until Markets & investing, Fees & pricing and Practice & technology were added
to cover what was actually in it; it is now 2. If a recognisable subject starts
collecting there again, that is the signal to write another rule. A plain
`--brief` chunks 15 items at a time in flag order, so one paste mixes staff
changes with Compliance. `--group-by` cuts it along either axis, or both:

```bash
python src/monitor.py --brief --group-by topic          # compliance.md, regulation.md, …
python src/monitor.py --brief --group-by flag           # act.md, know.md, note.md
python src/monitor.py --brief --group-by topic,flag     # compliance-act.md, compliance-know.md, …
```

`--topic` and `--flags` narrow what goes in before it is grouped, so a week's
reading can be cut down to one paste:

```bash
python src/monitor.py --brief --topic Compliance,Regulation --flags KNOW
```

`--group-by` names the folder after `--brief`, so `output/briefing.md` becomes
`output/briefing/`. A combination with nothing in it gets no file rather than an
empty one, and a group too big for one paste is still split on item boundaries.
The prompt, the IDs and `--import-summaries` are unchanged, so a reply from any
of these files imports exactly like any other.

#### Or download it from the dashboard

The dashboard has the same thing as a button. Filter to what you want — category,
flag, source, date, search — then **Download for summarising** saves exactly what
is on screen.

- **Split files by** — two tick boxes, **Category** and **Urgency**. Tick both
  for `compliance-act.md`, `compliance-know.md`, …; tick one for
  `compliance.md` or `act.md`; untick both for a single undivided file.
- **Download as** — a zip holding one Markdown file per group, or one Markdown
  file with the groups one after another.

Underneath are two rows of tick chips, **Urgency** and **Category**, that scope
the download without disturbing the filters deciding what you are reading. They
apply together: leave only `KNOW` ticked in one row and only `Super & tax` in
the other and you get the KNOW items on tax, nothing else. Each chip carries
the count it would contribute given the other row's choice, so a category with
no KNOW items this week reads `(0)` and is greyed rather than promising a file.
Narrow to a single group and the download is named after it
(`super-tax-know-2026-09-14.md`).

**ⓘ Never scrapes paid sources** in that panel opens a plain-English
explanation of where the text comes from and why no article body can reach it. The reverse nesting (`act-compliance.md`) is not in the
UI; it is `--group-by flag,topic` on the command line.

It is built in the browser from the digest already loaded, so it costs no request
and reaches no publisher. `web/lib/briefing.ts` produces the same bytes as
`--brief` for the same items — checked against it over a real digest — so the
reply imports the same way whichever route you took.

Summaries land in the digest labelled `"ai_source": "manual"`, and the
dashboard shows them under **Summarised by hand** so they never read as
something this tool generated. They survive the next `--json` run, so a week's
pasting is not thrown away by the following week's fetch. Reply lines whose ID
is not in the digest are reported, never guessed at.

Neither command touches the network: both read the digest already on disk.

**What may be summarised this way.** Regulator PDFs — ASIC reports and media
releases, Treasury consultation papers, AFCA determinations, ABS releases — are
free public documents, so upload them to the AI tool whole. Trade-press
articles are not: the input stays the feed's title and teaser, as
[SAFEGUARDS.md](SAFEGUARDS.md) section A requires. That boundary is the same
whether a summary is written by an API or by hand.

The tool never downloads a document. Save the regulator PDFs yourself during
the weekly sweep — no function in this codebase fetches a publisher document,
and that is worth keeping literally true.

### Web dashboard (optional)

The dashboard reads `web/lib/digest.json` — the real fetched, classified and
link-checked digest. Refresh it before starting, or it shows the last run.

```bash
cd /Users/bella/Projects/advice-monitor
python src/monitor.py --json          # writes web/lib/digest.json
cd web
npm install
npm run dev
```

Then open http://localhost:3000

What works there without any credentials:

- **Search** across titles, teasers, sources and topics.
- **Filters**: source, date range, flag, and link kind — plus "hide read".
- **Timeline**: the days that carried items; click one to filter to it.
- **Read state**: per item, kept in the browser's local storage, so the Unread
  count is real. It is one browser's state — there are no accounts.
- **Bibliography**: one entry per publication the digest drew on, with its home
  page — written by the monitor, not guessed from article links.
- **WhatsApp**: composes the newsletter and, with no Twilio credentials, shows
  the exact messages instead of sending. Same format and 1600-character
  splitting as `src/whatsapp_sender.py`.
- **Email**: `/api/email/preview` renders the digest as the email body to
  proof-read. Sending stays with the credentials, in `python src/monitor.py
  --email`.
- **Integration cards** report what the server can actually do (`/api/status`),
  rather than offering switches that only flip a piece of React state.

The AI summariser is not built. Classification is weighted keywords only — see
[BUILD_STEPS.md](BUILD_STEPS.md) for the opt-in AI stage.

JSON endpoints over the same digest: `GET /api/items` (`flag`, `source`,
`query`, `exactness`, `limit`), `POST /api/search`, `GET /api/status`.

## Testing
```bash
cd /Users/bella/Projects/advice-monitor
. .venv/bin/activate
python -m pytest -q
```

## Outside services

Every external service this can use — Twilio, SMTP, the Gmail API, Vercel, the
AI web tool — is listed in [INTEGRATIONS.md](INTEGRATIONS.md) with what it costs
and how to keep it free. Nothing is on unless you configure it, and
`/api/status` reports what the server can actually do rather than showing
switches that do nothing.

## How articles are collected and filtered

[HOW_IT_WORKS.md](HOW_IT_WORKS.md) walks the seven stages from source list to
digest and names the guard at each — including why a paid source cannot even be
configured, and the one honest caveat about the link check. It also covers
summarising with no API cost, which is the recommended way to use this.

## Picking up work on this

[HANDOVER.md](HANDOVER.md) is the brief for a developer who did not write this:
where each stream stands, what finished looks like, and the rules that do not
bend. It covers finishing WhatsApp delivery, summaries from a local model, and
making the downloaded briefing something an AI tool can be handed as-is.

[WHATSAPP_IMPLEMENTATION.md](WHATSAPP_IMPLEMENTATION.md) and
[OLLAMA_SETUP.md](OLLAMA_SETUP.md) are the per-stream briefs: how to finish
WhatsApp delivery without making a charge possible, and how to run a model on
this machine — Phase 3 with no key and no bill.

## Safety and guardrails
- No paywall bypassing
- No login flow required for default usage
- No Gmail or database access unless you configure it
- Classification is plain weighted keywords — no AI, no API key, no per-run cost
- Email and WhatsApp delivery are off unless explicitly enabled

## Optional live features (not enabled by default)
- Gmail label intake via the dry run
- SMTP email digest
- WhatsApp digest via Twilio
- Later Supabase-backed dashboard

These are documented in the project notes and should only be enabled when the user has intentionally configured them.

## GitHub push instructions
```bash
git init
git add .
git commit -m "Initial publish"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

If the repo already exists locally, use:
```bash
git remote add origin <your-github-repo-url>
git push -u origin main
```

## Notes
This repo is intended to stay honest: if a feature is not enabled or configured, it should not appear to work as if it were live.

