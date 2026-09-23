# How articles are collected, filtered and summarised

Two questions this answers: **where does the text come from** (and how do you
know nothing behind a paywall got in), and **how do you summarise it without
paying for an API**.

- [Summarising with no API cost](#summarising-with-no-api-cost) — the recommended way
- [The collection pipeline](#the-collection-pipeline) — seven stages, and the guard at each
- [Why a paywall cannot be reached](#why-a-paywall-cannot-be-reached)
- [Checking any of this yourself](#checking-any-of-this-yourself)

---

## Summarising with no API cost

**You do not need an API key, and this project recommends you never buy one.**

An API key means a balance to watch, a bill to cap and a key to keep out of
version control. If you already pay for Claude or ChatGPT, you are paying for
the same model twice. So the tool does the part a subscription cannot — collect,
classify, deduplicate, group — and hands you a file to paste. **You are the
transport.**

Or let a model on this laptop be the transport: `--ollama` sends the same files,
with the same prompt, to Ollama on this machine and merges the replies the same
way. It runs in the Monday job, needs no key and no account, and nothing leaves
the laptop — setup is [SETUP.md Part 2](SETUP.md#part-2--ollama-summaries-from-a-model-on-this-laptop).

### The loop

```bash
python src/monitor.py --json                        # fetch this week's digest
python src/monitor.py --brief --group-by topic,flag # one file per group
#   paste a file into Claude or ChatGPT, save the reply as output/reply.md
python src/monitor.py --import-summaries output/reply.md
```

Or from the dashboard: filter, scope the download with the **Urgency** and
**Category** chips, and press **Download**. Same files, same result.

### Why it is split into small files

A week is ~50 items. Pasted as one wall, an AI tool gives 50 shallow lines. Cut
into "the KNOW items on tax" — 8 items on one subject — you get summaries worth
reading, and you can skip the groups you do not care about this week. That is
the entire reason the grouping exists.

### Getting a file into an AI tool

| Route | Notes |
|---|---|
| **Copy** button on the dashboard | Straight onto the clipboard, paste into the chat. Nothing to upload, nothing to be refused. |
| Single Markdown file | `.md` uploads fine to Claude and ChatGPT. |
| **Zip** | **Unzip first.** Neither Claude nor ChatGPT accepts a `.zip` upload — but the `.md` files inside are fine. |

### Two passes: triage, then detail

One prompt cannot do both jobs. *"One line each, only from the teaser"* is right
for sorting fifty items, and it **guarantees** one-liners — the opposite of what
you want on the handful that matter.

So run the quick pass over everything, then a deep pass over what survived:

```bash
python src/monitor.py --brief --flags ACT,KNOW --deep
```

`--deep` swaps in a prompt that asks for two to four sentences, leading with
figures, dates and names rather than framing; tells the model to say so when the
DATE means a poll or a quarterly figure may already have been overtaken; and
keeps "thin — open source" for anything under about eighty words. Pastes drop
from 15 items to 6, because each item now carries far more text. On the
dashboard it is the **Detail** dropdown.

### What comes back

Each reply line is `ID | FLAG | one-sentence summary | LINK`. The ID is a hash
of the article link, so `--import-summaries` puts each summary against the right
item and **reports any ID it does not recognise rather than guessing**. Summaries
are stored as `"ai_source": "manual"` and shown under **Summarised by hand** (or
`ollama:<model>`, shown as **Summarised by a local model**), so they never read as
something this tool produced. They survive next week's fetch.

### The prompt does the safety work

Every block carries [SAFEGUARDS.md](SAFEGUARDS.md) section D verbatim:

> summarise ONLY from the teaser given; never invent detail or add facts not
> present; if the teaser is too thin, write "thin — open source"; always keep the
> ID and the LINK unchanged; do not attempt to access anything beyond the text
> provided.

Every clause earns its place. *"Only from the teaser"* stops invention.
*"Thin — open source"* gives it a way to admit it cannot tell, instead of
guessing. *"Keep the LINK"* preserves your route to the original. *"Do not access
anything beyond the text"* restates the paywall boundary to the AI itself.

**A summary is triage, never evidence.** Read every 🔴 ACT item at its source
before acting on it.

---

## The collection pipeline

Seven stages. The guard at each is the point.

### 1. The source list — a gate before any network request

Sources live in [data/sources.json](data/sources.json). Before a single request
is made, `validate_feed_source` refuses a source unless **all** of these hold:

| Check | Why |
|---|---|
| `access` is `free` or `free_signup` | A source marked paid is never fetched at all |
| `intake` is `rss`, `email_alert` or `email_newsletter` | No other intake method exists |
| `rss` is a valid http(s) URL | No file paths, no other schemes |
| The feed host **equals** the home host | A feed URL cannot quietly point somewhere else |
| The path looks like a feed | `/feed`, `/rss`, `/atom`, or ends `.xml` `.rss` `.atom` `.json` |

Fail any one and it raises `UnsafeSourceError` — the run reports it and
continues with the rest. The paid/free decision is made **before** the network,
not after.

### 2. Fetch — the feed, and only the feed

The RSS file is fetched. That is a document the publisher generates and serves
on purpose, for exactly this.

### 3. Take what the feed hands over

From each entry: the **title**, the **summary** (the teaser), and
**`content:encoded`** — the article text the publisher chose to put in their own
feed — where they supply it. In practice most do: 44 of 50 items in a recent
digest came with it.

That is still the feed, not the article page. Nothing is fetched, no wall is
approached, and a publisher who does not want the text there does not put it
there. It is capped at **1,500 characters** (`FEED_BODY_LIMIT`), trimmed back to
a sentence boundary, because a briefing is pasted into a chat window and 9,000
characters an item would blow the paste long before fifteen items.

Every item records **`body_source`** — `feed_content` or `feed_summary` — so it
is always visible which a summary was written from. The article URL is stored so
you can click it; it is never fetched for its text.

> This changed on 2026-09-15. Before it, only the title and a shortened teaser
> were used, a briefing carried a median of 37 words an item, and every summary
> that came back was a one-liner — because one-liners were all the input
> supported. It is now 216. [SAFEGUARDS.md](SAFEGUARDS.md) section A was amended
> to permit feed content explicitly.

### 4. Clean the teaser

Publisher furniture is stripped: photo credits, `The post … appeared first on
…`, "Read more", "Continue reading", "Share this". These carry no meaning, and
before they were removed they were being *scored* as if they were part of the
story.

### 5. Classify — weighted keywords, no AI

Each item is scored for ACT / KNOW / NOTE and given a category. A term in the
headline counts **double**, because the headline is what the story is about. A
source's own `flag` in `sources.json` is a **prior that nudges the score, not a
verdict** — the item's own words decide.

Confidence reflects how far the winner cleared its threshold and how far clear
it stayed of the runner-up, so a borderline call reads as borderline. No AI is
involved at any point here.

### 6. Check the links

Each URL is asked whether it resolves — `HEAD`, falling back to `GET` where a
site refuses `HEAD`. **The response body is never read.** The check keeps the
status and the redirect target, nothing else. Dead links are dropped so the
digest never ships one.

*This is the only place the code touches an article URL, and it is worth being
precise about: asking "does this resolve?" and reading a page are different
operations. This one never calls `.read()`.*

### 7. Deduplicate, filter, rank

- The same wire story from two outlets collapses to one, matched on the link
  with tracking parameters stripped, or on a loose title key.
- When two copies collide, **the ACT-worded copy wins** — never the calmer one,
  even if the calmer one scores a higher confidence.
- Items older than 14 days are dropped (`--days`), as are items below
  `--min-confidence` or outside `--flags`.
- What is left is sorted ACT first, then confidence, then recency, and capped at
  50 (`--limit`).

---

## Why a paywall cannot be reached

Not a policy the tool follows — **a capability it does not have.**

**0. The distinction that does the work: what a publisher *sends* you is safe;
what you *go and take* is not.** A feed is delivered. An article page is fetched.
Nothing here fetches one.

**1. Only a handful of places in the Python code touch the network, and none
reads an article page.** Fetching a feed. Checking a link resolves. Sending your
own digest to your email or Telegram (or the retired WhatsApp sender). And two opt-in ones: `--gmail` reading your
own mailbox label, and `--ollama` talking to the model on this laptop
(localhost only — nothing leaves the machine).

**2. There are no credentials to log in with.** No publisher account, password,
cookie or session exists anywhere in the project. A paywall cannot be passed by
something that never signs in.

**3. A paid source cannot even be configured.** `access: "paid"` is refused by
the gate in stage 1, before any request.

**4. No document is ever downloaded.** No function fetches a PDF, a DOCX or an
article page. Regulator documents — ASIC reports, Treasury consultations, AFCA
determinations, ABS releases — are free public documents and you may upload them
to an AI tool whole, but **you** save them during your weekly sweep. Keeping "the
tool never downloads a document" literally true is worth more than the
convenience.

**5. The AI is told the same thing**, in the prompt, every time.

### The honest caveat

The link check in stage 6 does send a request to article URLs. It reads no
content, but it is the nearest thing in the codebase to the line
[SAFEGUARDS.md](SAFEGUARDS.md) section A draws, so it is written down here
rather than left for you to find. If you would rather not make even that
request, `--no-check-links` skips it — at the cost of dead links reaching the
digest.

---

## Checking any of this yourself

Do not take the above on trust:

```bash
# Every web request in the Python code: feed, link check, Ollama (localhost),
# Telegram, and the retired WhatsApp sender.
# Email goes out through smtplib in src/email_sender.py; Gmail through src/gmail_reader.py.
grep -rn "urlopen\|requests\." src/

# Every source, and whether it is free
python src/monitor.py --sources

# What actually goes into a briefing: title, teaser, link. Nothing else.
python src/monitor.py --brief && head -30 output/briefing.md
```

The dashboard's **ⓘ Never scrapes paid sources** button says the same in short
form, for showing someone else.
