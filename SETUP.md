# Setup — from nothing to a working digest

For anyone picking this up, including future you on a new machine. The core
tool needs **no account with anyone**: no API key, no signup, no card. Work
down the page and stop whenever you have enough.

- [Before you start](#before-you-start)
- [Part 1 — the monitor](#part-1--the-monitor-15-minutes-no-accounts) · free, no accounts
- [Part 2 — the dashboard](#part-2--the-dashboard-5-minutes-no-accounts) · free, no accounts
- [Part 3 — summaries](#part-3--summaries-with-your-own-ai-subscription) · uses a subscription you already have
- [Optional add-ons](#optional-add-ons)
- [Editor setup](#editor-setup)
- [When it goes wrong](#when-it-goes-wrong)
- [If you pass this on](#if-you-pass-this-on)

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

## Part 1 — the monitor (15 minutes, no accounts)

```bash
git clone <your-repo-url> advice-monitor
cd advice-monitor

python3 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python src/monitor.py
```

That reads seven public RSS feeds, flags every item 🔴 ACT / 🟠 KNOW / 🟢 NOTE
with a confidence score, checks each link resolves, and prints the digest.

Confirm the install is sound:

```bash
python -m pytest -q               # should be all green
python src/monitor.py --sources   # the feeds it is configured to read
```

**Nothing above touches an account, a key, or a card.** If you stop here you
already have the thing the project is for.

---

## Part 2 — the dashboard (5 minutes, no accounts)

```bash
python src/monitor.py --json      # writes web/lib/digest.json

cd web
npm install
npm run dev
```

Open **http://localhost:3000**. Search, filter by category, flag, source and
date, group and download a briefing, mark items read.

Refresh the digest any time with `python src/monitor.py --json` — the local
dashboard re-reads it on every request, so a browser refresh is enough.

---

## Part 3 — summaries with your own AI subscription

No API key and no per-run cost. The tool writes a briefing, you paste it into
Claude or ChatGPT, you paste the reply back.

**From the dashboard:** filter to what you want → **Download for summarising** →
tick **Split files by** (Category, Urgency, or both), scope it with the Urgency
and Category chips, and press **Download** for a zip of Markdown files, one per
group.

**Or from the command line:**

```bash
python src/monitor.py --brief --group-by topic,flag
python src/monitor.py --brief --topic Compliance --flags ACT,KNOW
```

Paste a file's contents into your AI tool, save its reply as `output/reply.md`,
then:

```bash
python src/monitor.py --import-summaries output/reply.md
```

Both routes produce byte-identical files, so it makes no difference which you
use. The prompt that travels with every paste is
[SAFEGUARDS.md](SAFEGUARDS.md) section D verbatim — it forbids inventing detail
and forbids the AI going and fetching the article.

**Why no API key?** One would mean a balance to watch, a bill to cap and a key
to keep out of git — to pay a second time for a model you already subscribe to.
[HOW_IT_WORKS.md](HOW_IT_WORKS.md#summarising-with-no-api-cost) explains the loop
and why the files are split small.

---

## Part 4 — the Gmail newsletter intake (10 minutes, free, do it when you have the patience)

Four of your sources publish no feed and arrive only as email: **ABS**, **FS Industry Moves**,
**Macquarie Technical Services** and **CFS FirstTech**. Two of those are 🔴 ACT. Until this is
switched on they reach no digest at all, so a quiet week in the digest is not evidence of a quiet
week — see item 5 in [IMPROVEMENTS.md](IMPROVEMENTS.md).

The code is built and tested. The only missing piece is a file called `credentials.json`.

**This part is yours to do.** It needs you signed into your own Google account, on screens that
deliberately refuse automation. Nobody else can do it for you, and the tool never asks for your
password.

### Cost: nothing. Do not give Google a card.

Creating the project, enabling the Gmail API and making the client are all free, and reading
~25 newsletters a week is nowhere near the free quota. **The console will repeatedly offer you a
"free trial" and ask for a credit card. Decline every time.** You never need the billing page. If
any step insists on billing, stop — you have taken a wrong turn, not hit a paywall.

### Step A — in Gmail (2 minutes)

1. Create a label called exactly `industry-update-monitor`.
2. Create a filter that applies that label to the newsletters you want read.

Nothing outside that label is ever visible to the tool. This step is what sets the boundary, so
it is worth doing first and deliberately.

### Step B — in Google Cloud Console (8 minutes)

At [console.cloud.google.com](https://console.cloud.google.com/). Google renames these screens
often, so the wording below may drift; the order does not.

1. **Create a project.** Project picker in the top bar → *New Project*. Any name. No organisation.
2. **Enable the Gmail API.** *APIs & Services* → *Library* → search "Gmail API" → *Enable*.
3. **Set up the consent screen.** Look for *OAuth consent screen*, or *Google Auth Platform* in
   newer consoles. Choose **External**. Fill in app name, your email as support contact, your
   email as developer contact. Nothing else is required.
4. **Publish it.** On the consent screen, set publishing status to **In production**.
   *This matters:* left in **Testing**, Google expires your sign-in every 7 days and the tool
   stops until you sign in again. Production is still free — it just sounds more serious than it
   is. You will see an "unverified app" warning later, which is expected for something only you
   use.
5. **Create the client.** *Credentials* → *Create Credentials* → *OAuth client ID* →
   Application type: **Desktop app** → *Create* → **Download JSON**.
6. Rename the downloaded file to `credentials.json` and put it in the repo root, next to
   `README.md`. It is git-ignored.

### Step C — the first run

```bash
python src/monitor.py --gmail --gmail-max 10
```

Your browser opens for consent. You will see **"Google hasn't verified this app"** — that is your
own app, and the way through is *Advanced* → *Go to (unsafe)*. Approving writes `token.json`
beside the credentials. Both files are your mailbox: never share either, and never commit them.

Start at `--gmail-max 10` rather than the full 25, and see what it does to the length of a sweep
before making it routine. Reading time is the real cost here, not money.

### What the tool can and cannot do with this

The scope is `gmail.readonly`, and `src/gmail_reader.py` refuses any label but the configured one.
It cannot read the rest of your mail, and it cannot send, label, archive or delete anything. No
attachments, no link-following. Without `credentials.json` the run says so and stops; every other
command works without Gmail.

## Optional add-ons

None of these are needed. Read
**[INTEGRATIONS.md](INTEGRATIONS.md)** before signing up for any of them — it
has the costs, and how to keep each one free.

| Add-on | What it gives you | Cost | Instructions |
|---|---|---|---|
| **[Gmail app password](https://myaccount.google.com/apppasswords)** | Weekly digest by email | Free | [EMAIL_SETUP.md](EMAIL_SETUP.md) |
| **[Gmail API](https://console.cloud.google.com/)** | Reads newsletters from one label into the digest | Free — decline the card | [Part 4](#part-4--the-gmail-newsletter-intake-10-minutes-free-do-it-when-you-have-the-patience) |
| **[Twilio](https://www.twilio.com/try-twilio)** | Digest to WhatsApp | Free trial credit, then cents | [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) · **read the cautions below** |
| **[Vercel](https://vercel.com/signup)** | Dashboard hosted on a URL | Free Hobby tier | `cd web && npx vercel deploy` |

### News sources to sign up to

[free_subscriptions/FREE_SIGNUPS.md](free_subscriptions/FREE_SIGNUPS.md) lists
the free newsletters and alerts worth having — ASIC media releases, AFCA
determinations, Treasury, the trade press. All free, most need only an email.
[paid_later/PAID_CONSIDER_LATER.md](paid_later/PAID_CONSIDER_LATER.md) covers
what a paid tier would add and why to wait.

### Twilio — tread carefully

Three rules, and you cannot be charged:

1. **Stay on the trial account — never click "upgrade".** No card on file means
   nothing to charge. When the credit runs out, sends fail rather than bill.
2. **Never buy a phone number.** The WhatsApp sandbox uses Twilio's shared
   number. A bought number is rented monthly whether you use it or not, and is
   the usual source of a surprise bill.
3. **Keep the credentials in your local `.env`, never in Vercel.** The dashboard's
   send endpoint takes the recipient from the request body with no
   authentication — fine on your own machine, not fine on a public URL. Full
   explanation in [INTEGRATIONS.md](INTEGRATIONS.md#the-one-real-exposure--read-this-before-making-the-site-public).

Also know the sandbox lapses: WhatsApp only allows a freeform message within 24
hours of that phone messaging the sandbox, and the join expires after 72 hours.
A failed send now tells you this in plain words. **Email has none of these
limits** and is the better default for a weekly digest.

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
| WhatsApp send refused | The message now says which Twilio code and what to do. Usually: message the sandbox number from your phone again. |

---

## If you pass this on

[SAFEGUARDS.md](SAFEGUARDS.md) section E: the same rules bind anyone who runs
it. Free and legitimate sources only, never anything behind a paywall, and
🔴 ACT items get verified at the original source rather than trusted from a
summary.

Practically:

- **Never share a `.env`.** It is git-ignored for a reason. Everyone brings
  their own credentials.
- The same goes for `credentials.json` and `token.json` from the Gmail setup —
  those are your mailbox.
- `output/` is git-ignored too, so briefings and previews stay local.
- Personal scale is very different from distribution. At any scale beyond
  yourself, you become responsible for how it handles the paywall boundary.
