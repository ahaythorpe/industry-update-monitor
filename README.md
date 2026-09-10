# Industry Update Monitor

A free-first monitoring project for the Australian financial advice industry.

## What it does
Every week it reads seven public RSS feeds from the Australian financial advice
press, flags each article ACT / KNOW / NOTE with a confidence score, checks that
every link resolves, and emails you the result. No AI, no API key, no per-run
cost, nothing behind a paywall.

Feeds currently configured: Financial Standard, Professional Planner, FAAA,
Riskinfo, Money Management, ifa, SMSF Adviser. ASIC, ABS and AFCA no longer
publish usable feeds, so those stay on the manual weekly check.

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

A source's `flag` in `data/sources.json` is a **prior**, not a verdict — it
nudges the score in its direction, but the item's own words decide the flag.

#### Adding a source

A source is fetched if it has an `rss` URL, and `validate_feed_source` requires
it to be free, on the same host as `home`, and to look like a feed. Verify a new
feed returns current items before adding it — some publishers serve a valid but
stale or empty feed. ASIC, ABS and AFCA no longer offer usable feeds and stay
bookmark-and-check.

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

