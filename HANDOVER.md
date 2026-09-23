# Handover — for a developer picking this up

For developers who did not write this repo. It says what is where, what is
built, what is still open, and the rules that do not bend. The rules are not
style preferences: this project's whole claim is that it never touches a
paywall and never pretends a feature works when it does not.

The owner is not a developer. User-facing instructions live in
[README.md](README.md) and [SETUP.md](SETUP.md); keep them in plain English and
keep them true when you change behaviour.

## Read before touching anything

1. `.github/copilot-instructions.md` — the binding agent rules: source
   boundary, Gmail boundary, allowed inputs, output and cost boundary.
2. [SAFEGUARDS.md](SAFEGUARDS.md) — the design constraints, including section A
   (what may be sent to a model) and section D (the summarising prompt,
   verbatim).
3. [IMPROVEMENTS.md](IMPROVEMENTS.md) — the staged backlog. "Issues" in this
   project means its numbered items; there is no issue tracker. An idea is not
   ready to build until its cost, privacy, source and reading-time impact are
   understood. Stage the plan there first; the git history shows the pattern.

Two rules run through everything:

- **Nothing that is not configured may look live.** `/api/status` reports what
  the server can really do rather than showing switches that flip React state.
  Anything new follows that.
- **Every summary carries its source link, and an ACT item is read at its
  primary source.** No exceptions for a cleverer model.

```bash
. .venv/bin/activate && python -m pytest -q     # 209 tests, offline, a few seconds
cd web && npm test                              # vitest, the TypeScript side
```

Every test in this repo runs offline. Keep it that way: a test that needs the
network is a test that will be deleted by the next person.

---

## Where things are

| Path | What it is |
|---|---|
| `src/monitor.py` | Everything on the Python side: source gate, fetch, classify, link check, dedupe, digest JSON, briefing, sweep sheet, glossary, `--ollama`, `--import-summaries`, CLI |
| `src/email_sender.py` | HTML email via SMTP. Password from env, else the macOS Keychain (`_keychain_password`, service `advice-monitor-email`) |
| `src/telegram_sender.py` | Telegram formatting (HTML parse mode, 3900-char splitting between articles), `send_telegram_digest` to `TELEGRAM_CHAT_ID` only, `find_chat_id` |
| `src/whatsapp_sender.py` | **Retired 23 Sep 2026**, kept working: WhatsApp formatting, 1600-char splitting, Twilio send, `explain_twilio_error`. Not recommended — see [the Telegram section](#telegram-the-phone-channel-and-why-not-whatsapp) |
| `src/gmail_reader.py` | Read-only Gmail: `gmail.readonly` scope, only the `industry-update-monitor` label |
| `src/gmail_dry_run.py` | Local Gmail dry run |
| `data/sources.json` | The source list, with probe notes for sources that have no feed |
| `data/glossary.json` | Hand-written glossary for the sweep sheet |
| `scripts/weekly-run.sh`, `scripts/com.advice-monitor.weekly.plist` | The Monday 07:00 `launchd` run |
| `web/` | Next.js 16 dashboard. Reads `web/lib/digest.json`; no database |
| `web/lib/briefing.ts`, `web/lib/bundle.ts`, `web/lib/zip.ts` | The download panel's files, byte-identical to the CLI's `--brief --group-by` |
| `web/lib/telegram.ts` | Browser twin of `src/telegram_sender.py`'s formatter, plus `clampPerFlag` and `explainTelegramError` |
| `web/app/api/*` | `GET /api/items` (`flag`, `source`, `query`, `exactness`, `limit`), `POST /api/search`, `GET /api/status`, `/api/email/preview`, `POST /api/telegram/send` |
| `tests/` | pytest, all offline |
| `archive/` | Superseded plans and setup pages — history only; see [archive/README.md](archive/README.md) |

**Repos and deploys.** `origin` is `github.com/ahaythorpe/industry-update-monitor`
— **private**, the real project. `github.com/ahaythorpe/advice-monitor` is a
different, **public** repo holding only an older copy of the `web/` dashboard
with unrelated history. **Never push this repo there**; it would overwrite a
public site. Dashboard deploys are Vercel previews, made by hand from `web/`
(`cd web && npx vercel deploy`). The Vercel project must hold no credentials — no `TELEGRAM_*`
(and no retired `TWILIO_*`) — see [SETUP.md Part 5](SETUP.md#the-dashboard-button).
Never commit `.env`, `web/.env.local`, `credentials.json` or `token.json`; all
are git-ignored, and `git log --all` showed none ever committed (17 Sep 2026).

---

## Command-line reference

| Flag | Default | Effect |
| --- | --- | --- |
| `--json [PATH]` | `web/lib/digest.json` | Write the digest the dashboard reads |
| `--days` | 14 | Drop items older than N days (`0` = no limit) |
| `--min-confidence` | 0.0 | Drop items whose flag confidence is below this |
| `--flags` | `ACT,KNOW,NOTE` | Which tiers to include |
| `--limit` | 50 | Maximum items in the digest |
| `--no-check-links` | off | Skip the HEAD/GET check that drops dead links |
| `--sources` | off | Print the source list first |
| `--preview` | off | Write `output/digest_preview.html` (the email body) |
| `--email` | off | Email the digest to `EMAIL_ADDRESS` |
| `--telegram` | off | Send the digest to your own Telegram chat (`TELEGRAM_CHAT_ID`); prints a preview when not set up |
| `--from-digest` | off | Send the saved digest (summaries included) instead of fetching again |
| `--per-flag` | 6 | Max items per flag in the Telegram (or WhatsApp) newsletter |
| `--whatsapp` | off | **Retired, not recommended.** WhatsApp via Twilio; prints a preview with no Twilio credentials |
| `--whatsapp-to` | `$WHATSAPP_TO` | Recipient for the retired `--whatsapp` send |
| `--gmail` | off | Also read newsletters from the Gmail label (read-only, opt-in) |
| `--gmail-label` | `industry-update-monitor` | Exists, but `gmail_reader.read_label` refuses any other name |
| `--gmail-max` | 25 | Maximum newsletters to read |
| `--sweep [PATH]` | `output/sweep-<date>.md` | Tickable sheet for the weekly sweep; refuses to overwrite |
| `--brief [PATH]` | `output/briefing.md` | Paste-ready briefing for an AI web tool |
| `--deep` | off | Detailed prompt and smaller pastes; pair with `--flags ACT,KNOW` |
| `--group-by` | — | One file per group: `topic`, `flag`, `topic,flag` or `flag,topic` |
| `--topic` | — | Brief only these categories, e.g. `Compliance,Regulation` |
| `--import-summaries` | — | Merge summaries pasted back from an AI web tool |
| `--ollama [MODEL]` | `$OLLAMA_MODEL`, else `llama3.1:8b` | Summarise through a model on this machine |
| `--ollama-timeout` | 600 | Seconds per paste before giving up |
| `--ollama-chunk` | 5 | Items per paste through the model |
| `--ollama-reply` | `output/ollama-reply.md` | Where the model's raw reply is kept |
| `--digest` | `web/lib/digest.json` | The digest `--brief`, `--sweep`, `--ollama` and `--import-summaries` read |

### Tuning and extending

- **Classification** is weighted keywords, no AI. A term in the headline counts
  double. Confidence rises with how far the winner cleared its threshold and
  how far clear it stayed of the runner-up. A source's `flag` in
  `sources.json` is a **prior**, not a verdict.
- **Categories.** Every item gets one: Compliance, Regulation, Super & tax,
  Insurance, Key personnel movements, Business, Markets & investing, Fees &
  pricing, Practice & technology, or **General** when no rule matches. General
  is the fallback, not a subject: a large pile there means rules are missing. It
  sat at 19 of 50 until the last three categories were added; it is now about 2.
  If a recognisable subject collects there again, write another rule.
- **Adding a source.** A source is fetched if it has an `rss` URL, and
  `validate_feed_source` requires it to be free, on the same host as `home`, and
  to look like a feed. Probe a new feed for *current* items before adding it —
  `ministers.treasury.gov.au/rss.xml` parses perfectly and its newest entry is
  from 2023. Record what was probed in the source's notes. Never scrape a media
  centre page to fake a feed.
- **Adding a glossary term.** Add an entry to `data/glossary.json`: `term`,
  `means`, `matters`, `check`, optionally `also` for other spellings and
  `changing: true` if its substance is still moving (it then reads `Possible
  meaning` / `Needs confirmation`). Matching is on the term's own spelling; four
  terms per item is the cap. Tests check every entry says what it means and
  where to check it.

---

## Summaries: the round trip, and Ollama

Built. The manual round trip (`--brief` → paste → reply →
`--import-summaries`) defines the prompt, the item blocks, the reply format
(`ID | FLAG | summary | LINK`) and the ID matching. `--ollama` is a transport
into the middle of it, not a separate feature. Summaries are stored in the
digest with `ai_source` (`manual` or `ollama:<model>`), survive the next
`--json` run (`attach_saved_summaries`), and are labelled through one
`summary_origin` on every route — dashboard, email, Telegram, and the
"Finished summaries" download.

Constraints anyone changing `--ollama` must keep:

- **Opt-in.** No flag, no model call. `OLLAMA_MODEL` in `.env` sets the model
  (the owner uses `qwen3:8b`).
- **Reuse `format_briefing`.** `BRIEF_PROMPT` is SAFEGUARDS section D verbatim
  and must not be reworded to make a small model behave — change the model or
  the block size instead. `--deep` / `DEEP_PROMPT` is the second pass, same
  rule. `--deep` through a local model is untested.
- **POST to `/api/generate` on localhost** (`LOCAL_HOSTS`), `stream: false`,
  `temperature: 0`, one request per block, in sequence. The only network call is
  to this machine — asserted in `tests/test_ollama.py` against a fake server.
- **Parse with `parse_summaries`.** It tolerates a chat model's bullets, bold
  and numbering. Do not write a second parser. Unmatched IDs are reported,
  never guessed.
- **Write the raw reply to disk before merging** (`--ollama-reply`).
- **Bounded.** `OLLAMA_CHUNK` 5 items per paste, `OLLAMA_MAX_BLOCKS` 12 pastes,
  `OLLAMA_TIMEOUT` 600 s per paste. A 50-item week takes about 20 minutes.
- **Fail loudly, never retry, never fall back to anything paid.** "Not
  running" and "slow" are told apart in the error.
- `scripts/weekly-run.sh` runs `--ollama` after the digest, as a separate step
  that is skipped (and logged) when `localhost:11434` does not answer, so a
  closed Ollama costs the summaries, never the digest.

What is left is judgement, not code: whether a local model is good enough to
trust for KNOW items. On the first run one summary of three added a word the
teaser did not contain.

---

## Telegram: the phone channel, and why not WhatsApp

**Decided 23 Sep 2026 by the owner:** the phone channel is Telegram, because
the Telegram Bot API is free for good — no trial, no balance, no per-message
charge — and every WhatsApp route (Twilio's sandbox, Meta's Business API) ends
up costing money. The bot is **@advicemonitor_bot** ("Advice-Monitor").

Built on both sides and tested on both (`tests/test_telegram.py`,
`web/lib/telegram.test.ts`): `python src/monitor.py --telegram [--from-digest]`,
and the dashboard's **Send this digest to Telegram** section
(`POST /api/telegram/send`). HTML parse mode; all publisher text escaped;
split between articles under 3900 characters, parts numbered "(1 of 3)";
summaries labelled through `summaryOrigin` / `summary_origin`. Keep the two
formatters in step — the WhatsApp pair drifted once (IMPROVEMENTS item 4).
With no credentials both sides return the exact messages instead of sending,
and `/api/status` reports `telegram.configured` false (a token with no chat ID
is reported as half-done, not live).

**The send endpoint keeps the 17 Sep 2026 decision (option A).** It sends only
to `TELEGRAM_CHAT_ID` from the server environment and ignores any recipient in
the request body; there is no recipient box. The alternatives weighed then —
B, command-line only; C, a shared-secret header (rejected: the secret would
live in the browser); D, real authentication (out of proportion, and it drags in the database
question IMPROVEMENTS item 7 settled the other way) — are recorded in full in
this file's git history before 23 Sep 2026. Do not reintroduce a body-supplied recipient without replacing
that protection. The route has no auth and no rate limit, which is why
`TELEGRAM_*` values must never be added to Vercel. The three web-route gaps the
WhatsApp route had are closed in the Telegram one: `perFlagLimit` is clamped to
1–50 (`clampPerFlag`), Telegram's error description is translated into plain
words (`explainTelegramError`, Telegram's own text kept on the end), and a
failure part-way says how many parts had already arrived.

Next.js reads `web/.env.local`, not the root `.env`, so the dashboard needs its
own copy of the two values. The chat ID is found by `find_chat_id(token)` from
`getUpdates` after the owner presses Start on the bot.

Rules: **no retry loop**; never log the token (it is in the request URL, so the
route logs only Telegram's description and scrubs the token from any error);
the Monday run sends to Telegram after the email (`scripts/weekly-run.sh`),
only to `TELEGRAM_CHAT_ID`, and logs a failure without retrying.

**WhatsApp is retired, not deleted.** `src/whatsapp_sender.py` and `--whatsapp`
still work and `tests/test_whatsapp_errors.py` still covers them, but the
dashboard's WhatsApp section, `/api/whatsapp/send`, `web/lib/whatsapp.ts` and
its tests were removed. Its setup page is
[archive/WHATSAPP_TWILIO_RETIRED.md](archive/WHATSAPP_TWILIO_RETIRED.md). If
anyone does use it: never buy a Twilio number, never upgrade the account,
no retry loop.

---

## The download bundle

Built (IMPROVEMENTS item 12). The dashboard builds its download in the browser
from the digest already loaded — no request, no publisher contacted. The zip and
the CLI's `--brief --group-by` folder both carry a `README.md` (which digest,
counts, the round trip, the boundary) and a `links.md` (every item once). A
newsletter item's link is a mailbox URL only its owner can open, so it is
labelled rather than offered as a link; the digest field to test is
`intake === 'email'`, not `email_newsletter` (the `sources.json` value, which
never reaches an item — that mistake has been made once).

Rules: the prompt stays SAFEGUARDS section D verbatim; IDs stay the refs the
monitor wrote, and an item with no ref is left out and counted, never given a
made-up one; no article body, ever; keep the zip dependency-free; keep the two
routes byte-identical and the parity test covering them.

---

## Things removed, so nobody rebuilds them by accident

- **Supabase** — deleted 17 Sep 2026. `web/lib/supabase.ts` and
  `@supabase/supabase-js` were imported by nothing. The dashboard reads
  `web/lib/digest.json`; read state lives in the browser's local storage, per
  browser. A hosted database starts from IMPROVEMENTS item 7, and the first
  question is privacy, since it moves teasers and links off this machine.
- **A paid AI mode** — never existed. There is no `USE_AI` switch, no `--ai`
  flag and no API key anywhere in `src/`. Any paid route must first pass
  IMPROVEMENTS item 2 and SAFEGUARDS section C.

---

## When you have finished something

Update [IMPROVEMENTS.md](IMPROVEMENTS.md) to say what was built and what is
still open, the way the existing items do, and correct any user-facing
sentence in README.md or SETUP.md that your change made untrue. A fix that
leaves the docs stale is half a fix.
