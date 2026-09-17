# Handover — three streams of work

For developers picking up work on this repo who did not write it. Each stream
below says where it stands, what finished looks like, and the rules that do not
bend. The rules are not style preferences: this project's whole claim is that it
never touches a paywall and never pretends a feature works when it does not.

## Read before touching anything

1. `.github/copilot-instructions.md` — the binding agent rules: source
   boundary, Gmail boundary, allowed inputs, output and cost boundary.
2. [SAFEGUARDS.md](SAFEGUARDS.md) — the design constraints, including section A
   (what may be sent to a model) and section D (the summarising prompt,
   verbatim).
3. [IMPROVEMENTS.md](IMPROVEMENTS.md) — the staged backlog. An idea is not ready
   to build until its cost, privacy, source and reading-time impact are
   understood. Stage the plan there first; the git history shows the pattern.

Two rules run through all three streams:

- **Nothing that is not configured may look live.** `/api/status` reports what
  the server can really do rather than showing switches that flip React state.
  Anything new follows that.
- **Every summary carries its source link, and an ACT item is read at its
  primary source.** No exceptions for a cleverer model.

```bash
. .venv/bin/activate && python -m pytest -q     # 181 tests, offline, ~0.2s
cd web && npm test                              # vitest, the TypeScript side
```

Every test in this repo runs offline. Keep it that way: a test that needs the
network is a test that will be deleted by the next person.

---

## Stream A — WhatsApp delivery

### Where it stands

- `src/whatsapp_sender.py` — formats the digest, splits on item boundaries
  under WhatsApp's 1600-character cap, repeats a heading when a section
  continues, and translates every Twilio rejection into plain words
  (`explain_twilio_error`). Tested in `tests/test_whatsapp_errors.py`.
- `web/lib/whatsapp.ts` — the same formatting in the browser, so the dashboard
  preview matches what the CLI sends. Tested in `web/lib/whatsapp.test.ts`.
- `web/app/api/whatsapp/send/route.ts` — the dashboard's send endpoint.
- [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) — the user-facing setup, written to
  keep a Twilio account on free trial credit and make a charge impossible.

With no credentials, `--whatsapp` prints the exact messages instead of sending.
That is the default and it must stay usable with no account at all.

### What finished looks like

1. **Close the send-endpoint exposure.** `POST /api/whatsapp/send` takes
   `phoneNumber` from the request body and has no authentication and no rate
   limit. On a laptop that is fine. Deployed with Twilio credentials in the
   environment, anyone who finds the URL can send messages on the account.
   Pick one: take the recipient from `WHATSAPP_TO` on the server and ignore the
   body, require a shared secret, add a rate limit, or keep sending
   CLI-only and leave the deployed route in preview mode. Whichever it is,
   [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) and
   [INTEGRATIONS.md](INTEGRATIONS.md) both describe the current behaviour and
   must be corrected with it.
2. **Carry the summaries.** `_format_item` reads only `summary`, so a summary
   pasted back by hand never reaches WhatsApp. That is item 4 of
   IMPROVEMENTS.md and it applies to the email digest in the same way.
3. **Handle the window, do not fight it.** A sandbox send is refused unless the
   recipient's phone messaged the sandbox in the last 24 hours, and a join
   lapses after 72. Any scheduling must expect the refusal and report it. **No
   retry loop** — the agent rules ban them, and a retry against a messaging API
   is how a free trial becomes a bill.

### Rules

- Never buy a Twilio number and never upgrade the account. A trial account has
  no card on file, so a failed send cannot become a charge.
- Keep the Python and TypeScript formatters in step. They are tested
  separately; if they drift, the dashboard preview stops being a preview.
- An unrecognised Twilio code must still surface Twilio's own message. Nothing
  is hidden by not being on the translation list.

---

## Stream B — Ollama, a model on the machine

### Where it stands

Nothing is built. The design and the install are written up in
[OLLAMA_SETUP.md](OLLAMA_SETUP.md) — read that first; it is the brief for this
stream.

The short version: the manual round trip (`--brief` → paste → reply →
`--import-summaries`) already defines the prompt, the item blocks, the reply
format and the ID matching, and all of it is tested. A local model slots into
the middle of that, so the work is a transport, not a new feature.

### What finished looks like

- `--ollama` runs the existing briefing blocks through a local model and merges
  the replies through the existing importer.
- The origin is recorded as `ollama:<model>`, never `manual`, and the dashboard
  says "Summarised by a local model" rather than a bare "Summary".
- Ollama not running produces one clear sentence and a stop. No retry, no
  silent fallback to anything paid.
- The whole path is tested offline against a fake local server.

### Rules

- The input stays title and teaser. A local model is not a reason to fetch an
  article body.
- `BRIEF_PROMPT` is SAFEGUARDS section D verbatim. Do not reword it to make a
  small model behave; change the model or the block size instead.
- The only network call is to 127.0.0.1. Assert it.

---

## Stream C — make the downloaded briefing easy to feed to an AI tool

### Where it stands

The dashboard's **Download for summarising** builds the briefing in the browser
from the digest already loaded — no request, no publisher contacted.

- `web/lib/briefing.ts` — `buildBriefingFiles` writes one Markdown file per
  group, each holding the prompt and then `ID / TITLE / SOURCE / DATE / TEASER /
  LINK` blocks, chunked to a comfortable paste.
- `web/lib/zip.ts` — a small ZIP writer, entries STORED, no dependency added.
- The output is byte-identical to the CLI's `--brief --group-by`, checked
  against it over a real digest, so a reply imports the same way whichever
  route produced it.

So every item's link **is** in the download today, on its own `LINK:` line, and
the prompt tells the model to keep it unchanged. What is missing is everything
around them.

### What finished looks like

Unzipping gives a folder a person or a tool can use without being told how:

1. **`README.md` inside the zip** — what this is, which digest and date it came
   from, how many items and pastes, what to do with it (paste a file, get
   `ID | FLAG | summary | LINK` lines back, import them), and the one-line
   boundary: these are the publisher's own titles and teasers, no article text,
   so do not ask a tool to fetch the links.
2. **`links.md` inside the zip** — every item once: ID, flag, source, date,
   title, URL. This is the list to hand to a tool or to open by hand, and it is
   the thing a reader currently has to dig out of the blocks.
3. **Mailbox links marked as such.** A newsletter item's link is a
   `mail.google.com` URL that only the owner's browser can open. It must be
   labelled in `links.md`, so nobody — person or tool — treats it as a public
   article. The digest field to test is `intake === 'email'` (not
   `email_newsletter`, which is the sources.json value and never reaches an
   item; that exact mistake has already been made once and fixed).
4. **The CLI writes the same two files** for `--brief --group-by`, and the
   existing parity test is extended to cover them. Two routes, one output, or
   they drift.

### Rules

- The prompt stays SAFEGUARDS section D verbatim, and the IDs stay the refs the
  monitor wrote — `--import-summaries` matches on them, and an invented ID
  attaches a summary to the wrong article.
- An item with no ref is left out and counted, never given a made-up one. That
  behaviour exists; keep it.
- No article body, ever. The briefing carries the feed's own teaser and that is
  the whole input.
- Keep the zip dependency-free.

---

## When you have finished a stream

Update [IMPROVEMENTS.md](IMPROVEMENTS.md) to say what was built and what is
still open, the way items 1 and 3 do. A list that only ever grows is a list
nobody reads.
