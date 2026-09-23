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
| [Part 5 — WhatsApp (Twilio trial)](#part-5--whatsapp-via-a-twilio-trial) | The digest on your phone | Free trial credit only | Not set up |

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
| **Twilio** | WhatsApp digest | Free trial credit, then a few cents a message | **Never upgrade, never buy a number, never put the credentials in Vercel** |
| **An AI web tool** (Claude, ChatGPT) | Summaries pasted by hand | The subscription you already have | No API key, ever |
| **Vercel** | Hosts the dashboard on a link | Free Hobby tier | Deploy by hand only; no Twilio values in it |
| **Supabase** | Nothing — removed 17 Sep 2026 | — | — |

What to avoid:

| Tempting | Why not |
|---|---|
| Upgrading Twilio "to be safe" | It is the opposite of safe — upgrading is what makes charges possible |
| Buying a Twilio phone number | Recurring monthly cost, and the sandbox does not need one |
| Putting Twilio credentials in Vercel | The send endpoint has no login and no rate limit; see [Part 5](#3-keep-the-credentials-on-your-own-machine-never-in-vercel) |
| An Anthropic/OpenAI API key | Not needed — Ollama or your existing subscription does the summarising for free |
| A paid news subscription | [paid_later/PAID_CONSIDER_LATER.md](paid_later/PAID_CONSIDER_LATER.md): pay for a gap you actually hit, not in advance |
| Anything that fetches article bodies | [SAFEGUARDS.md](SAFEGUARDS.md) section A — the paywall boundary is the one rule with no exceptions |

Check what your machine can actually do at any time — neither command sends or
charges anything:

```bash
python src/monitor.py --whatsapp --whatsapp-to +61400000000   # prints, does not send
curl -s localhost:3000/api/status                             # what the dashboard server can do
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
can be *more* capable than a deployed one — it can send WhatsApp (Part 5), and
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
running — writes the summaries (Part 2). It deliberately passes no `--email`,
`--whatsapp` or `--gmail`: **a scheduled job must never send on your behalf
while you are not looking.** Delivery stays something you trigger.

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
appear — dashboard, email, WhatsApp — never as this tool's own work.

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

**Why email is the better default than WhatsApp for a weekly digest:** no
24-hour window, no 72-hour re-join, no balance to run down, no trial to expire.
WhatsApp is nicer to read on a phone; email is the one still working in six
months without you thinking about it. Running both is reasonable.

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

**The Monday run never emails.** Sending stays a command you type, for the same
reason it never sends WhatsApp.

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

## Part 5 — WhatsApp via a Twilio trial

**Free trial credit only, about 15 minutes. Not set up.** The digest can arrive
on your phone as a WhatsApp message. This Part gets you there on free trial
credit only, and keeps it that way.

Before anything else: **email (Part 3) does the same job with none of these
limits.** WhatsApp is nicer to read on a phone.

### First: see it for free, before signing up for anything

With no credentials at all, the tool prints the exact messages it would send:

```bash
python src/monitor.py --whatsapp --whatsapp-to +61400000000 --per-flag 2
```

Nothing is sent, nothing is charged, no account exists yet. Proof-read the
formatting. If you do not like it, you have lost nothing. The dashboard's
WhatsApp button does the same — it shows a preview until Twilio is configured.

### The three rules that make charges impossible

Follow these and Twilio has no mechanism to bill you.

#### 1. Stay on the trial account. Never click "Upgrade"

A trial account has **no card on file**. There is nothing to charge. When the
trial credit runs out, sends fail — they do not bill. Upgrading is the single
action that makes a charge possible, and nothing here needs it.

#### 2. Never buy a phone number

This is how people get a surprise recurring bill: a number is rented monthly
whether you use it or not.

**The WhatsApp sandbox does not need one.** You use Twilio's shared sandbox
number. If you find yourself on a "Buy a number" screen, you have taken a wrong
turn — back out.

#### 3. Keep the credentials on your own machine, never in Vercel

They go in two git-ignored files on this laptop (see Step 5 below), never in
Vercel, never in a commit, never in a message.

> **Do not add Twilio variables to the Vercel project.** Since 17 September 2026
> the dashboard's send endpoint reads the recipient from `WHATSAPP_TO` and
> **ignores any recipient in the request**, so it cannot be aimed at a stranger's
> phone. It still has **no login and no rate limit**, though, so with
> credentials attached to a public link anyone who found it could trigger
> repeated sends — to your phone, on your balance. Locally that is fine: the dev
> server listens on your machine only. Without those variables the deployed
> dashboard stays in preview mode: it composes the message and shows it instead
> of sending. That is the intended state, not a fault to fix.

It becomes a real problem only if **both** happen: Twilio values are added to
Vercel, **and** Vercel's login protection is turned off to make the dashboard
public.

**Checked on 17 September 2026: the Vercel project has no environment variables
at all**, so the deployed dashboard is in preview mode and cannot send. The
public repo's whole history was also scanned — no `.env`, no credentials file,
no hardcoded token; every Twilio reference in the code is `process.env.NAME`, a
name and never a value. Nothing was exposed. This section is about keeping it
that way.

Note that `github.com/ahaythorpe/advice-monitor` **is public**, and the send
endpoint (`app/api/whatsapp/send/route.ts`) is in it. The code being public is
not the problem — the credentials would be.

**Checking it yourself** — two commands, neither of which prints a secret:

```bash
cd web && vercel env ls          # expect: "No Environment Variables found"
grep -rn "TWILIO" .env.example   # placeholders only, never real values
```

If `vercel env ls` ever lists `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` or
`TWILIO_WHATSAPP_NUMBER`, remove them with `vercel env rm <NAME>` **before**
doing anything else, then treat the token as compromised and rotate it in the
Twilio console. An auth token that has sat on a public send endpoint is not made
safe by deleting it afterwards.

### Two more safety nets

- **Set a balance alert.** Twilio Console → Billing → Alerts. It tells you
  before the credit is gone rather than after.
- **If you ever do upgrade, turn auto-recharge OFF.** Console → Billing. Auto
  recharge tops your balance up from a card automatically; off means the balance
  simply runs out. (Better: don't upgrade.)

Nothing sends on a schedule: the Monday run never passes `--whatsapp`. A message
goes only when you type `python src/monitor.py --whatsapp` or press **Send** on
your local dashboard.

### Setup, about 15 minutes

1. **Sign up** at [twilio.com/try-twilio](https://www.twilio.com/try-twilio).
   Free, comes with trial credit, no card needed. **Do not upgrade.**
2. **Open the sandbox**: Console → Messaging → Try it out → Send a WhatsApp
   message. It shows a sandbox number (often `+1 415 523 8886`) and a join
   phrase like `join russet-panther`.
3. **Join from your own phone**: WhatsApp that exact phrase to that number. You
   will get a confirmation back. *Your phone must be the one you want the digest
   on.*
4. **Copy two values** from the Console home page: the **Account SID** (starts
   `AC`) and the **Auth Token**.
5. **Put the same four values in BOTH files** — this is the part that catches
   people:

   ```bash
   cp .env.example .env                        # the Python side (repo root)
   cp web/.env.local.example web/.env.local    # the dashboard side
   ```

   The command line reads `.env`. The dashboard reads **`web/.env.local`** and
   does **not** read the root `.env`. Fill in only `.env` and the command line
   sends while the dashboard button stays on "Preview message" with nothing
   telling you why. Both files are git-ignored. The shape, every value masked:

   ```bash
   TWILIO_ACCOUNT_SID=AC••••••••••••••••••••••••••••••••   # 34 chars, starts AC
   TWILIO_AUTH_TOKEN=••••••••••••••••••••••••••••••••      # 32 chars — treat as a password
   TWILIO_WHATSAPP_NUMBER=+1415•••••••                     # the shared sandbox number
   WHATSAPP_TO=+614••••••••                                # your own phone, +61 form
   ```

   (If you already have a `.env`, don't copy over it — add the four lines.)

6. **Send one**:

   ```bash
   python src/monitor.py --whatsapp --per-flag 2
   ```

   `--per-flag 2` keeps the first real send to one message.

**The auth token is a password in every sense:** it is shown once, it grants
spending on your account, and anyone holding it can send as you. If it is ever
pasted anywhere shared — a chat, a screenshot, an issue — rotate it in the
Twilio console rather than hoping.

**The dashboard sends to one number only** — `WHATSAPP_TO`, your own phone. The
endpoint ignores any recipient in the request, and there is deliberately no
recipient box on the page.

### The 72-hour catch — the thing that will actually annoy you

WhatsApp only allows a freeform message **within 24 hours of that phone
messaging you**, and a sandbox join lapses after **72 hours**. A weekly digest
is therefore refused unless you message the sandbox number again first.

So the weekly habit is: **WhatsApp anything to the sandbox number, then run the
digest.** One message, then the command.

If you forget, the command line tells you exactly that rather than printing
Twilio's raw error:

```
❌ WhatsApp part 1 not sent. The 24-hour window has closed. WhatsApp only allows
   a freeform message within 24 hours of the recipient messaging you.
   Fix: send any message to the sandbox number from that phone, then re-run.
   On the sandbox you have to do this every 72 hours.
```

(The dashboard button is less helpful — it says only `Twilio rejected the
message (HTTP …)`. Assume the window closed and message the sandbox first.)

The paid way around it is an approved WhatsApp message template, which needs a
WhatsApp Business sender and Meta business verification. That is real setup and
real money for a personal project — **not recommended**.

### What a send actually costs

| | |
|---|---|
| Messages per run | 1–3 (`--per-flag 2` gives 1; the default 6 gives 3) |
| Cost each | a few cents — check Twilio's current WhatsApp pricing |
| Trial credit | Twilio has offered around US$15–25; check what you actually get |
| Monthly, sending weekly | cents, against trial credit |
| Recurring fees | **none**, as long as you never buy a number |

When the trial credit runs out, sends stop. They do not bill.

### Other errors, in plain words

Every Twilio rejection on the command line is translated
(`explain_twilio_error` in `src/whatsapp_sender.py`):

| What happened | What to do |
|---|---|
| The 24-hour window closed | Message the sandbox from your phone, re-run |
| The recipient has not joined, or the join lapsed | Re-send `join <your-phrase>` from that phone |
| Twilio could not reach the recipient | Check `WHATSAPP_TO` is full international form, `+61412345678` |
| No WhatsApp sender for that number | `TWILIO_WHATSAPP_NUMBER` must be the sandbox number exactly |
| From and To are not both WhatsApp | You have used an SMS number by mistake |
| Credentials refused | Re-copy the SID (starts `AC`) and Auth Token |

An unrecognised code still reports Twilio's own message — nothing is hidden by
not being on this list.

### Turning it off

Delete the four lines from `.env` **and** `web/.env.local`. That is the whole
procedure: no account to close, no subscription to cancel, nothing left
running. `--whatsapp` and the dashboard button go back to showing a preview.

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
  read [Part 5, rule 3](#3-keep-the-credentials-on-your-own-machine-never-in-vercel)
  before you do.

The deployed dashboard has no credentials, so it previews WhatsApp and cannot
send. That is intended.

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
| WhatsApp send refused | The command line says which Twilio code and what to do. Usually: message the sandbox number from your phone again. |
| Dashboard WhatsApp button only previews | The Twilio values are missing from `web/.env.local` (Part 5, Step 5). |

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
