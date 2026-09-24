# Setup — every setup in one place

Everything you might ever set up for this tool, one Part each. **Only Part 1 is
needed.** Everything after it is optional, and each Part says up front what it
costs and whether anything is already done.

The core tool needs **no account with anyone**: no API key, no signup, no card.
Work down the page and stop whenever you have enough.

| Part | What it gives you | Cost | Status (23 Sep 2026) |
|---|---|---|---|
| [Part 1 — Basic install](#part-1--basic-install) | The weekly digest, the dashboard, the Monday run | Free, no accounts | Installed on this laptop |
| [Part 2 — Ollama (local model)](#part-2--ollama-summaries-from-a-model-on-this-laptop) | Summaries written on this laptop | Free, no accounts | Running, in the Monday run |
| [Part 3 — Email digest](#part-3--the-email-digest) | The week's digest in your inbox | Free | Needs a Gmail app password |
| [Part 4 — Gmail newsletter intake](#part-4--the-gmail-newsletter-intake) | Four email-only sources join the digest | Free — decline the card | **Not connected** |
| [Part 5 — Telegram](#part-5--telegram--free) | The digest on your phone | Free, no accounts to pay | Set up on the command line; dashboard needs `web/.env.local` |

Also on this page: [what it all costs and how to stop it costing](#what-it-costs-and-how-to-stop-it-costing),
[the dashboard on a Vercel link](#the-dashboard-on-a-vercel-link),
[editor setup](#editor-setup), [when it goes wrong](#when-it-goes-wrong) and
[if you pass this on](#if-you-pass-this-on).

---

## What it costs, and how to stop it costing

**The rule this project runs on: nothing is on unless you configured it.** No
credentials means no sends, no API calls and no bill. Verify current prices
yourself before relying on any figure here — they change.

| Service | What it does here | Cost | How to keep it free |
|---|---|---|---|
| **Ollama** | Summaries on this laptop | Nothing — disk, memory and a warm laptop | Nothing to do; there is no account |
| **Gmail app password (SMTP)** | Emailed digest | Free | Nothing to do; revoke it any time |
| **Gmail API** | Reads newsletters from one label | Free | **Decline every offer of a free trial or card.** If a step insists on billing, stop |
| **Telegram** | The digest on your phone | Free — no trial, no per-message charge | Nothing to do; never put the token in Vercel |
| **Twilio** | Retired WhatsApp route (23 Sep 2026) — not recommended | Trial credit, then a few cents a message | Don't sign up. If you did: never upgrade, never buy a number |
| **An AI web tool** (Claude, ChatGPT) | Summaries pasted by hand | The subscription you already have | No API key, ever |
| **Vercel** | Hosts the dashboard on a link | Free Hobby tier | Deploy by hand only; no credentials in it |
| **Supabase** | Nothing — removed 17 Sep 2026 | — | — |

What to avoid:

| Tempting | Why not |
|---|---|
| WhatsApp (Twilio or Meta) for the phone digest | Every WhatsApp route costs money in the end; Telegram does the same job free ([Part 5](#part-5--telegram--free)) |
| Putting the Telegram token in Vercel | The send endpoint has no login and no rate limit; see [Part 5, the dashboard button](#the-dashboard-button) |
| An Anthropic/OpenAI API key | Not needed — Ollama or your existing subscription does the summarising for free |
| A paid news subscription | [paid_later/PAID_CONSIDER_LATER.md](paid_later/PAID_CONSIDER_LATER.md): pay for a gap you actually hit, not in advance |
| Anything that fetches article bodies | [SAFEGUARDS.md](SAFEGUARDS.md) section A — the paywall boundary is the one rule with no exceptions |

Check what your machine can actually do at any time — neither command sends or
charges anything:

```bash
curl -s localhost:3000/api/status   # what the dashboard server can do
```

`/api/status` reports what is really configured rather than showing switches
that do nothing. If it says "not configured", it cannot charge you.

---

## Before you start

| You need | Version | Where |
|---|---|---|
| **Python** | 3.11 or newer (`pyproject.toml` requires it) | [python.org/downloads](https://www.python.org/downloads/) |
| **Node.js** | 20.9 or newer (Next.js 16 requires it) | [nodejs.org](https://nodejs.org/) — take the LTS |
| **Git** | any current version | [git-scm.com](https://git-scm.com/downloads) |

Check what you have:

```bash
python3 --version    # want 3.11+
node --version       # want v20.9+
```

> **macOS gotcha:** the `python3` that ships with macOS is often 3.9, which is
> below what this needs. If `python3 --version` shows 3.9, install a current
> Python from the link above (or `brew install python@3.13`) before making the
> virtual environment — otherwise you build the environment on the wrong one and
> the failure shows up much later.

---

## Part 1 — Basic install

**Free, no accounts, about 20 minutes.** This is the whole tool. If you stop
after this Part you already have the thing the project is for.

### The monitor

```bash
git clone <your-repo-url> advice-monitor
cd advice-monitor

python3 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python src/monitor.py
```

That reads the public RSS feeds in [data/sources.json](data/sources.json),
flags every item 🔴 ACT / 🟠 KNOW / 🟢 NOTE with a confidence score, checks each
link resolves, and prints the digest.

Confirm the install is sound:

```bash
python -m pytest -q               # should be all green
python src/monitor.py --sources   # the feeds it is configured to read
```

**Nothing above touches an account, a key, or a card.**

### The dashboard

```bash
python src/monitor.py --json      # writes web/lib/digest.json

cd web
npm install
npm run dev
```

Open **http://localhost:3000**. What you can do there is in
[README.md](README.md#the-dashboard).

Refresh the digest any time with `python src/monitor.py --json` — the local
dashboard re-reads it on every request, so a browser refresh is enough.

**Running locally is the private setup.** The dev server listens on your own
machine only; nothing is reachable from the internet, so credentials on this
laptop are not exposed by having a dashboard. That is why the local dashboard
can be *more* capable than a deployed one — it can send to Telegram (Part 5), and
a deployed one deliberately cannot.

### Summaries by hand (optional, no setup)

No API key and no per-run cost. The tool writes a briefing, you paste it into
Claude or ChatGPT, and you paste the reply back:

```bash
python src/monitor.py --brief --group-by topic,flag
#   paste a file into your AI tool, save its reply as output/reply.md
python src/monitor.py --import-summaries output/reply.md
```

Or from the dashboard's **Download for summarising** panel — same files, byte
for byte. [HOW_IT_WORKS.md](HOW_IT_WORKS.md#summarising-with-no-api-cost)
explains the loop and why the files are split small; the prompt that travels
with every paste is [SAFEGUARDS.md](SAFEGUARDS.md) section D verbatim. Part 2
does the same thing with no pasting.

### The Monday run — check it, change it, stop it

Installed 17 September 2026: a `launchd` agent runs **Monday at 07:00**. It
refreshes the digest, the sweep sheet and the briefing, then — if Ollama is
running — writes the summaries (Part 2). Once the
summaries exist it emails the newsletter **to your own address only**
(`--email --from-digest`) and to your own Telegram chat (`--telegram
--from-digest`), chosen 23 Sep 2026. It never passes `--whatsapp` or `--gmail`,
and never sends to anyone else.

- **The file:** `~/Library/LaunchAgents/com.advice-monitor.weekly.plist`,
  copied from `scripts/com.advice-monitor.weekly.plist`. What it runs:
  `scripts/weekly-run.sh`.
- **`launchd`, not `cron`,** because it runs a missed job when the laptop next
  wakes. `cron` simply skips it, which on a machine that is closed overnight
  means the run silently never happens.
- **What it did:** dated lines in `output/weekly-run.log`. A run that fetches
  nothing is logged as a failure to check, *not* as a quiet week — an empty
  digest that looks like a successful quiet week is worse than an error.
- **It never overwrites your sweep sheet.** If today's sheet already exists it
  is left alone, ticks and all, and only the digest and briefing refresh.

Check on it, or turn it off:

```bash
cat output/weekly-run.log                                     # what it has done
launchctl print gui/$(id -u)/com.advice-monitor.weekly        # is it registered

launchctl bootout gui/$(id -u)/com.advice-monitor.weekly      # stop it
rm ~/Library/LaunchAgents/com.advice-monitor.weekly.plist     # and forget it
```

To change the time, edit the `StartCalendarInterval` block in the plist
(`Weekday` 1 is Monday), copy it to `~/Library/LaunchAgents/` again, then
`bootout` and `bootstrap` to reload it.

---

## Part 2 — Ollama: summaries from a model on this laptop

**Free, no accounts. Running since 17 Sep 2026, and in the Monday run since
23 Sep 2026.** A model on this laptop reads the briefing and writes the
summaries — no key, no account, no bill, and nothing leaves the machine.

### What it does not change

None of this is softened by the model being local:

- **The paywall boundary is unchanged.** The input stays the feed's own title
  and teaser, exactly as [SAFEGUARDS.md](SAFEGUARDS.md) section A requires. A
  local model is not a reason to fetch an article body — nothing in this
  codebase fetches one.
- **A summary is triage.** Every summary keeps its source link, and an ACT item
  is still read at the primary source. **A local model invents like any other**
  — see [what it did on its first run](#what-it-actually-did).
- **It is off unless asked for.** No `--ollama`, no model call.

### Install — about 20 minutes plus the download

```bash
brew install ollama          # or download the app from ollama.com
ollama serve                 # runs on 127.0.0.1:11434 until you stop it
```

(If you installed the Ollama app instead, opening the app does the same as
`ollama serve`.)

In a second terminal, pull the model this project uses and check it answers:

```bash
ollama pull qwen3:8b         # about 5 GB; check ollama.com/library for current names
ollama list
ollama run qwen3:8b "Reply with the single word: ready"
```

Then tell the tool which model to use, in `.env` at the repo root:

```bash
OLLAMA_MODEL=qwen3:8b        # must be a name `ollama list` shows
```

If `OLLAMA_MODEL` is not set, the tool falls back to `llama3.1:8b`, which you
may not have pulled. `--ollama <name>` overrides both for one run.

**On model choice.** An 8B-class model is enough for summarising a teaser,
which is all this task is. It is roughly a 5 GB download and wants about 8 GB of
free memory to run comfortably. A bigger model is slower for very little gain;
a much smaller one starts inventing detail, which is the one failure that
matters here. Model names and sizes change — confirm at ollama.com/library
rather than trusting this page.

Ollama listens on localhost only. It is not reachable from outside the machine
unless you deliberately expose it, and there is no reason to.

### Running it

```bash
python src/monitor.py --json          # this week's digest (the Monday run does this)
python src/monitor.py --ollama        # summarise it on this laptop
```

It reads the digest on disk, sends it to the model five items at a time, and
merges the replies straight back in. **Expect about 20 minutes for a 50-item
week**; the laptop will be warm and loud meanwhile. Limits built in:

- It refuses any host but this machine.
- At most 12 pastes of 5 items in one run (60 items). Past that it stops and
  says so; narrow the week with `--flags ACT,KNOW` or `--topic`.
- Each paste gets up to 10 minutes before it gives up (`--ollama-timeout`).
- It never retries, and never falls back to anything paid.

The model's raw reply is kept at `output/ollama-reply.md` — **read it.**
Summaries are labelled "Summarised by a local model (qwen3:8b)" everywhere they
appear — dashboard, email, Telegram — never as this tool's own work.

### In the Monday run

Since 23 September 2026, `scripts/weekly-run.sh` runs `--ollama` straight after
the 07:00 digest refresh, so summaries are waiting when you open the dashboard.
It is a separate step: if Ollama is not running, the digest is still written and
the log says `SUMMARIES SKIPPED — Ollama is not running; open the Ollama app`.
Nothing fails. **Leave Ollama running on Monday mornings** if you want the
summaries; otherwise run `python src/monitor.py --ollama` yourself later.

### What it actually did

First real run, three ACT items through `qwen3:8b`: three summaries back in the
right shape, merged, labelled `ollama:qwen3:8b`. About 90 seconds including
loading the model.

Two of the three were faithful. The third said an adviser was banned for
"incompetence" — a word that appears nowhere in the teaser it was given. That is
why the raw reply is written to disk before anything is merged, and why an ACT
item is read at its source no matter what any model says about it.

### What it costs

| | |
|---|---|
| Money | none — no key, no account, no per-call price |
| Disk | ~5 GB for an 8B model |
| Memory | ~8 GB while it runs |
| Time | about 20 minutes for a 50-item week |
| Electricity | a warm laptop for that time, once a week |

### Turning it off

Leave off `--ollama`, and quit Ollama before Monday 07:00 (the Monday run then
just skips the summaries). To reclaim the disk:

```bash
ollama rm qwen3:8b
```

Nothing else depends on it: with no model, the digest, the sweep sheet and the
by-hand summaries all work exactly as before.

---

## Part 3 — The email digest

**Free, about 10 minutes.** `python src/monitor.py --email` sends the week's
digest as an HTML email **to your own Gmail address, from your own Gmail
address**, through Gmail's mail server. No API, no per-message charge.

Each email has 🔴 ACT items first, 🟠 KNOW second, 🟢 NOTE last, and every item
keeps its source link. Proof-read it first without sending anything:
`python src/monitor.py --preview` writes `output/digest_preview.html`, or open
`/api/email/preview` on the dashboard.

**Email or Telegram?** Both are free. The Monday run sends both by itself;
Telegram (Part 5) is nicer to read on a phone.

### What it needs

Two things: your Gmail address in `.env`, and a **Gmail app password** — a
separate 16-character password Google makes for one program. It is not your
normal Gmail password, and the tool never asks for that.

### Step 1 — turn on 2-Step Verification

App passwords only exist on accounts with **2-Step Verification** on. Check at
[myaccount.google.com/security](https://myaccount.google.com/security).

> **If the App passwords page says the setting is not available:** accounts
> that sign in with passkeys only, use Advanced Protection, or are work/school
> accounts may not be offered app passwords at all. That is Google's choice, not
> a fault here. The way round is a different mail provider — see
> [Another mail provider](#another-mail-provider-instead-of-gmail) below.

### Step 2 — make the app password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
   You may be asked to sign in again.
2. Give it a name you will recognise, such as `advice-monitor`. (Older versions
   of this page asked you to pick "Mail" and a device instead — either is fine.)
3. Google shows a 16-character password **once**. Keep the page open for Step 3.

### Step 3 — store it where the tool can find it

**Simplest: `.env`.** Open the settings file (`open -e .env` opens it in
TextEdit), paste the password after `EMAIL_PASSWORD=` (spaces are fine, no
quotes), and save:

```bash
EMAIL_ADDRESS=you@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop
```

`.env` stays on this Mac: it is git-ignored, has never been committed, and is
not part of what goes to Vercel. It is plain text on disk — acceptable for an
app password, which can only reach this one mailbox and can be deleted in
Google at any time.

> **Never paste the password into a chat** — not to Claude, not to anyone.

**Optional: the macOS Keychain**, so it is never in a file. Run this in the
Mac's own **Terminal** app — *not* with `!` inside Claude Code, which cannot
show the hidden prompt and saves a blank password:

```bash
security add-generic-password -a advice-monitor -s advice-monitor-email -U -w
```

It asks twice and shows nothing as you type. Then leave `EMAIL_PASSWORD=` empty
in `.env` — any value there, including the `xxxx` placeholder, wins over the
Keychain. If the Keychain asks for a password you don't recognise, use `.env`
instead; the two can drift apart on a Mac and it is not worth the fight.

### Step 4 — send one

```bash
python src/monitor.py --email
```

You should see `✅ Digest emailed to you@gmail.com via smtp.gmail.com`. Check
your inbox.

**The Monday run emails you** once the local model has written the summaries —
to `EMAIL_ADDRESS` only, which is the same account it sends from. To send the
current digest yourself at any time: `python src/monitor.py --email --from-digest`.

### Want it filed under your "Advice Monitor" label?

That is a Gmail filter, not a tool setting. In Gmail, create a filter on the
subject **`Industry Update Monitor — weekly digest`** and have it apply your
**Advice Monitor** label. Note this is a different job from Part 4: Part 4's
label is where *incoming newsletters* are read from, and it must have a
different, exact name.

### Summaries in the emailed digest

**There is no `USE_AI` switch and no `--ai` flag** — earlier drafts described
both, and neither ever existed. If the week has summaries (from Part 2, or
pasted back by hand), the email carries them. Each item then shows:

- The summary, labelled with who wrote it — "Summarised by hand", or
  "Summarised by a local model (qwen3:8b)". Never presented as this tool's work.
- The publisher's teaser, still there beneath it rather than replaced by it.
- The source link, always. A summary is triage; it never replaces the source.

### If the email is refused

| Message | Fix |
|---|---|
| `Cannot email: EMAIL_ADDRESS not set in .env` | Add `EMAIL_ADDRESS=` to `.env` |
| `Gmail email not configured` | No password found in `.env` or the Keychain. Redo Step 3 |
| `Gmail authentication failed`, or `535 5.7.8` | Gmail refused the password. Check the address is right, make a new app password (Step 2) and store it again with `-U`. Make sure it is an **app password**, not your normal one |

Still stuck? Check you are online (sending needs it), that 2-Step Verification
is on, and that there are no stray quotes or spaces around a password in `.env`.

### Another mail provider instead of Gmail

The tool also speaks plain SMTP. Set these in `.env` instead and it uses them in
preference to Gmail: `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`,
`SMTP_PASSWORD` (or leave it empty and use the same Keychain entry),
`SMTP_FROM_EMAIL`, `SMTP_USE_TLS` (default true). The digest still goes to
`EMAIL_ADDRESS`.

### Privacy, and turning it off

- The password lives in your Keychain or your git-ignored `.env`; it never
  leaves this machine except to sign in to Gmail.
- Emails contain only publisher teasers, summaries and links — never locked
  article text.
- An app password can sign in to your mailbox, so treat it like a password.
  **Revoke it any time** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords);
  remove it from the Keychain with
  `security delete-generic-password -s advice-monitor-email`.

---

## Part 4 — The Gmail newsletter intake

**Free, about 10 minutes. Not connected as of 23 September 2026** — there is no
`credentials.json` on this laptop, and `--gmail` has never run.

Four of your sources publish no feed and arrive only as email: **ABS**, **FS
Industry Moves**, **Macquarie Technical Services** and **CFS FirstTech**. Two of
those are 🔴 ACT. Until this is switched on they reach no digest at all, so **a
quiet digest is not evidence of a quiet week** — see item 5 in
[IMPROVEMENTS.md](IMPROVEMENTS.md). Until then, check those four by hand in the
weekly sweep.

The code is built and tested. The only missing piece is a file called
`credentials.json`.

**This Part is yours to do.** It needs you signed into your own Google account,
on screens that deliberately refuse automation. Nobody else can do it for you,
and the tool never asks for your password.

### Cost: nothing. Do not give Google a card.

Creating the project, enabling the Gmail API and making the client are all free,
and reading ~25 newsletters a week is nowhere near the free quota. **The console
will repeatedly offer you a "free trial" and ask for a credit card. Decline
every time.** You never need the billing page. If any step insists on billing,
stop — you have taken a wrong turn, not hit a paywall.

### Step A — in Gmail (2 minutes)

1. Create a label called **exactly `industry-update-monitor`** — lower case,
   hyphens, nothing else.
2. Create a filter that applies that label to the newsletters you want read.

> **Your "Advice Monitor" label will not work for this.** The code reads one
> label and refuses every other name (`src/gmail_reader.py`), so a label called
> "Advice Monitor" is never looked at. Either rename it to
> `industry-update-monitor`, or keep it for the emailed digest (Part 3) and make
> a second label with the exact name for the newsletters.

Nothing outside that label is ever visible to the tool. This step is what sets
the boundary, so it is worth doing first and deliberately.

### Step B — in Google Cloud Console (8 minutes)

At [console.cloud.google.com](https://console.cloud.google.com/). Google renames
these screens often, so the wording below may drift; the order does not.

1. **Create a project.** Project picker in the top bar → *New Project*. Any
   name. No organisation.
2. **Enable the Gmail API.** *APIs & Services* → *Library* → search "Gmail API"
   → *Enable*.
3. **Set up the consent screen.** Look for *OAuth consent screen*, or *Google
   Auth Platform* in newer consoles. Choose **External**. Fill in app name, your
   email as support contact, your email as developer contact. Nothing else is
   required.
4. **Publish it.** On the consent screen, set publishing status to **In
   production**. *This matters:* left in **Testing**, Google expires your sign-in
   every 7 days and the tool stops until you sign in again. Production is still
   free — it just sounds more serious than it is. You will see an "unverified
   app" warning later, which is expected for something only you use.
5. **Create the client.** *Credentials* → *Create Credentials* → *OAuth client
   ID* → Application type: **Desktop app** → *Create* → **Download JSON**.
6. Rename the downloaded file to `credentials.json` and put it in the repo root,
   next to `README.md`. It is git-ignored.

### Step C — the first run

```bash
python src/monitor.py --json --gmail --gmail-max 10
```

Your browser opens for consent. You will see **"Google hasn't verified this
app"** — that is your own app, and the way through is *Advanced* → *Go to
(unsafe)*. Approving writes `token.json` beside the credentials. Both files are
your mailbox: never share either, and never commit them.

Start at `--gmail-max 10` rather than the full 25, and see what it does to the
length of a sweep before making it routine. Reading time is the real cost here,
not money. The Monday run does not pass `--gmail`, so newsletters join the
digest only when you run it yourself.

### What the tool can and cannot do with this

The scope is `gmail.readonly`, and `src/gmail_reader.py` refuses any label but
`industry-update-monitor`. It cannot read the rest of your mail, and it cannot
send, label, archive or delete anything. No attachments, no link-following.
Without `credentials.json` the run says so and stops; every other command works
without Gmail.

A newsletter item links to the message in your own mailbox, so it is never
link-checked, and the dashboard badges it **Newsletter** with an "Open in Gmail"
link rather than pretending it is a public article.

---

## Part 5 — Telegram — free

**Free, about 10 minutes. Set up on this laptop's command line 23 Sep 2026.**
The digest arrives on your phone as a Telegram message from your own bot,
**@advicemonitor_bot** ("Advice-Monitor"). Telegram's bot service costs nothing:
no trial, no balance, no per-message charge, no card.

**Why not WhatsApp?** Every WhatsApp route costs money in the end. Twilio gives
trial credit, then charges a few cents a message; Meta's own route needs
business verification and bills per conversation. WhatsApp also refuses a
message unless you have messaged it in the last 24 hours. Telegram has none of
that, so it replaced WhatsApp on 23 September 2026. The old WhatsApp setup is in
[archive/WHATSAPP_TWILIO_RETIRED.md](archive/WHATSAPP_TWILIO_RETIRED.md) — not
recommended.

### First: see it for free, before setting anything up

With nothing set up, the tool prints the exact messages it would send:

```bash
python src/monitor.py --telegram --from-digest
```

Nothing is sent. The dashboard's **Send this week to Telegram** button does
the same: it shows the message until it is set up.

**What arrives each week:** one message, with the headlines grouped Act now,
Worth knowing, Background, each with its first dot point, and the full
newsletter attached as a file you tap to open. Once the dashboard is online and
`DASHBOARD_URL` is set in `.env`, it becomes a short alert instead: the Act now
headlines, the week by topic in one line, and a link to the dashboard. The
email switches the same way.

### Setup

1. **Install Telegram** on your phone (App Store or Google Play) and sign up
   with your phone number. Free.
2. **Make your bot.** In Telegram, search for **@BotFather** (the official one,
   with the blue tick) and send it `/newbot`. When it asks for a name, type
   **Advice Monitor**. When it asks for a username, give one ending in `bot`
   (this one is `advicemonitor_bot`). BotFather replies with a **token** — a long
   line like `1234567890:AA…`. **Treat it as a password.**
3. **Paste the token into `.env`.** In Finder, open the project folder, press
   **Cmd+Shift+.** to show hidden files, and open `.env` with **TextEdit**. Add
   one line, with your token after the `=` and no spaces:

   ```bash
   TELEGRAM_BOT_TOKEN=••••••••••:•••••••••••••••••••••••••••••••••••
   ```

   Save and close. (`.env` is git-ignored — it never leaves this laptop.)
4. **Press Start on your bot.** In Telegram, search for your bot's username,
   open it and press **Start**. A bot cannot message you until you have
   messaged it first; this is how Telegram stops bots spamming people.
5. **Add your chat ID.** It is a number that says "this chat", and the tool
   finds it for you from the Start you just pressed. The easy way: **ask
   Claude** to "find my Telegram chat ID and add it to .env". Or run this short
   command yourself — it prints the number and sends nothing:

   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; from src.telegram_sender import find_chat_id; print(find_chat_id(os.environ['TELEGRAM_BOT_TOKEN']))"
   ```

   Add it to `.env` the same way as the token: `TELEGRAM_CHAT_ID=` then the
   number. If it prints `None`, press Start (or send the bot "hi") and run it
   again.
6. **Send one:**

   ```bash
   python src/monitor.py --telegram --from-digest
   ```

   `--from-digest` sends the digest you already have, summaries included,
   instead of fetching the news again.

**It sends to one chat only** — `TELEGRAM_CHAT_ID`, your own chat with your own
bot. Nothing in the code takes a recipient from anywhere else, so it cannot be
pointed at another person.

**If the token is ever pasted anywhere shared** — a chat, a screenshot, an
issue — send `/revoke` to BotFather to get a new one and put the new one in
`.env`. Anyone holding the old token could post as your bot (to chats that have
pressed Start on it) but could not charge you anything, because there is
nothing to charge.

### The dashboard button

The dashboard reads **`web/.env.local`**, not the root `.env` — a Next.js rule.
To make its button send rather than preview, put the same two lines there too:

```bash
cp web/.env.local.example web/.env.local   # then add the two TELEGRAM_ lines
```

**Never put these values in Vercel.** The send endpoint has no login; on your
own laptop that is fine, because the dev server is reachable from your machine
only. Without them the deployed dashboard shows the message instead of sending,
which is the intended state.

### What it costs

Nothing. Telegram does not charge for bots or bot messages. A digest is usually
one to three messages; Telegram's limit is 4,096 characters each, and the tool
splits between articles, never through one, numbering the parts "(1 of 3)".

### If Telegram refuses, in plain words

| What it says | What to do |
|---|---|
| The bot token was not recognised | Copy the token from BotFather again into `TELEGRAM_BOT_TOKEN` |
| Chat not found | Open the bot, press Start, find the chat ID again (Step 5) |
| The bot was blocked | Unblock it in Telegram and press Start |
| Too many requests | Wait a minute and try again |

### Turning it off

Delete the two `TELEGRAM_` lines from `.env` (and `web/.env.local` if you added
them). `--telegram` and the dashboard button go back to showing a preview. To
remove the bot entirely, send `/deletebot` to BotFather.

---

## The dashboard on a Vercel link

Optional, and free on Vercel's Hobby tier for a personal, non-commercial
project. Deploys are **previews, made by hand, from `web/`**:

```bash
cd web && npx vercel deploy
```

Nothing builds unless you run that. Two things to know:

- **The deployed digest is frozen at deploy time.** Locally the dashboard
  re-reads `web/lib/digest.json` on every request; on Vercel it does not.
  Redeploy to update it.
- **Deployments sit behind Vercel's login protection** by default, so the link
  only opens for you. Turning that off makes it public to anyone with the URL —
  read [Part 5, the dashboard button](#the-dashboard-button) before you do.

The deployed dashboard has no credentials, so it previews the Telegram message
and cannot send. That is intended.

---

## News sources to sign up to

[free_subscriptions/FREE_SIGNUPS.md](free_subscriptions/FREE_SIGNUPS.md) lists
the free newsletters and alerts worth having — ASIC media releases, AFCA
determinations, Treasury, the trade press. All free, most need only an email.
[paid_later/PAID_CONSIDER_LATER.md](paid_later/PAID_CONSIDER_LATER.md) covers
what a paid tier would add and why to wait.

---

## Editor setup

`.vscode/extensions.json` lists the extensions this project actually uses — VS
Code offers to install them when you open the folder. Nothing here depends on
your editor; this is convenience only.

| Extension | Why |
|---|---|
| [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) + [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) | `src/` is Python; Pylance does the type hints and completions |
| [ESLint](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint) | The web app is linted by `eslint-config-next` |
| [Tailwind CSS IntelliSense](https://marketplace.visualstudio.com/items?itemName=bradlc.vscode-tailwindcss) | The dashboard's styling is Tailwind v4 utility classes |
| [Vitest](https://marketplace.visualstudio.com/items?itemName=vitest.explorer) | Runs the `web/lib/*.test.ts` suites from the sidebar |

Point VS Code at the virtual environment so tests and imports resolve:
**Cmd/Ctrl+Shift+P → Python: Select Interpreter → `.venv/bin/python`**.

---

## When it goes wrong

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: feedparser` | The virtual environment is not active. `. .venv/bin/activate`, then re-install. |
| `❌ No items fetched from any configured feed` | No network, or every feed failed. Check with `python src/monitor.py --sources`. |
| Some feeds error on a run | Normal and survivable — the run reports each failure by name and continues with the rest. |
| Dashboard shows old items | Re-run `python src/monitor.py --json`, then refresh. On Vercel you must redeploy — the hosted copy is frozen at deploy time. |
| `npm run dev` fails on Node version | Next.js 16 needs Node 20.9+. Check `node --version`. |
| Links being dropped as dead | `--no-check-links` skips the check so you can see what is being dropped and why. |
| `Ollama is not answering` | Start it (`ollama serve`, or open the app). See Part 2. |
| `SUMMARIES SKIPPED` in the Monday log | Ollama was not running at 07:00. Run `python src/monitor.py --ollama` now. |
| Email refused | See [Part 3, If the email is refused](#if-the-email-is-refused). |
| `Gmail is not set up: no credentials.json` | Expected until Part 4 is done. Drop `--gmail`. |
| Telegram send refused | The message says what to do — usually press Start on the bot again. See [Part 5](#if-telegram-refuses-in-plain-words). |
| Dashboard Telegram button only previews | The two `TELEGRAM_` lines are missing from `web/.env.local` ([Part 5, the dashboard button](#the-dashboard-button)). |

---

## If you pass this on

[SAFEGUARDS.md](SAFEGUARDS.md) section E: the same rules bind anyone who runs
it. Free and legitimate sources only, never anything behind a paywall, and
🔴 ACT items get verified at the original source rather than trusted from a
summary.

Practically:

- **Never share a `.env` or `web/.env.local`.** They are git-ignored for a
  reason. Everyone brings their own credentials.
- The same goes for `credentials.json` and `token.json` from the Gmail setup —
  those are your mailbox.
- `output/` is git-ignored too, so briefings and previews stay local.
- Personal scale is very different from distribution. At any scale beyond
  yourself, you become responsible for how it handles the paywall boundary.
