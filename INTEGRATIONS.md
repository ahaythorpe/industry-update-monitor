# External services — what plugs in, what it costs, how to stop it costing

Every outside service this project can use, whether it is free, and how to make
sure it stays that way. Verify current prices yourself before relying on any
figure here — they change, and I have not confirmed them.

**The rule this project runs on:** nothing is on unless you configured it. No
credentials means no sends, no API calls, and no bill. Check what your machine
can actually do at any time:

```bash
python src/monitor.py --whatsapp --whatsapp-to +61400000000   # prints, does not send
curl -s localhost:3000/api/status                             # what the server can do
```

`/api/status` reports what is really configured rather than showing switches
that only flip a piece of React state. If it says "not configured", it cannot
charge you.

---

## The whole list

| Service | What it does here | Cost | Needed? |
|---|---|---|---|
| **Twilio** | WhatsApp digest | Free trial credit, then a few cents a message | Optional |
| **SMTP (Gmail or Hostinger)** | Emailed digest | Free | Optional |
| **Gmail API** | Reads newsletters from one label | Free | Optional |
| **An AI web tool** (Claude, ChatGPT) | Summarises the briefing | Your existing subscription | Optional |
| **Vercel** | Hosts the dashboard | Free Hobby tier | Optional |
| **Supabase** | Nothing — removed 17 Sep 2026 | — | No |

Nothing in the table is required. The monitor, the classifier, the dashboard,
the briefing and the zip download all work with no account anywhere.

---

## Twilio — WhatsApp

**What it is.** The only way to send WhatsApp programmatically without being a
business with Meta verification. You use its *sandbox*: a shared number you
join from your own phone.

**What it costs.** A free trial account comes with credit (Twilio has offered
around US$15–25; check what you actually get). A WhatsApp message costs a few
cents. A full digest run is **1–3 messages** depending on `--per-flag`, so a
weekly send is cents a month against the trial credit.

### How to make sure Twilio never charges you

In order of how much they matter:

1. **Stay on the trial account. Do not "upgrade".** A trial account has no card
   on file, so there is nothing to charge. When the credit runs out, sends
   fail — they do not bill. Upgrading is the single action that makes charges
   possible, and nothing here needs it.
2. **Never buy a phone number.** This is how people get surprise recurring
   bills: a number is rented monthly whether you use it or not. **The WhatsApp
   sandbox does not need one** — you use Twilio's shared sandbox number. If you
   find yourself on a "Buy a number" screen, you have taken a wrong turn.
3. **If you ever do upgrade, turn auto-recharge OFF.** Console → Billing. Auto
   recharge tops your balance up from a card automatically; off means the
   balance simply runs out.
4. **Set a balance alert.** Console → Billing → Alerts. Tells you before the
   credit is gone rather than after.
5. **Nothing here runs on a schedule.** There are no GitHub Actions in this
   repo, no cron, no scheduler. A message is sent only when you type
   `python src/monitor.py --whatsapp` yourself.

### The one real exposure — read this before making the site public

`web/app/api/whatsapp/send/route.ts` takes a phone number **from the request
body** and sends to it. It has **no authentication and no rate limit**. That is
harmless today, because no Twilio credentials exist anywhere and the Vercel
deployment sits behind Vercel Authentication.

It stops being harmless if **both** of these become true:

- Twilio credentials are added to the Vercel project's environment variables, **and**
- Deployment Protection is turned off to make the dashboard public.

Then anyone who finds the URL can post any phone number to that endpoint and
spend your Twilio balance. So:

> **Keep Twilio credentials in your local `.env` only. Do not add them to
> Vercel.** Send WhatsApp from your own machine with
> `python src/monitor.py --whatsapp`. The deployed dashboard then stays in
> preview mode, which composes the message and shows it instead of sending.

If you ever do want the deployed dashboard to send, the endpoint needs fixing
first — the smallest honest fix is to ignore the posted number and only ever
send to `WHATSAPP_TO`, so a stranger cannot aim it at their own phone.

### The 72-hour catch

WhatsApp only allows a freeform message within 24 hours of the recipient
messaging you, and the sandbox join lapses after 72 hours. So a weekly digest
will be refused unless you message the sandbox number again first. The send now
says so in plain words rather than printing Twilio's raw error. The paid way
round it is an approved message template, which needs Meta business
verification — not worth it for a personal project.

**Setup:** free trial at twilio.com/try-twilio → Messaging → Try it out → Send a
WhatsApp message → WhatsApp the join phrase from your own phone → copy the
Account SID and Auth Token into `.env`.

---

## SMTP — the emailed digest

**What it costs.** Nothing. No API, no per-message charge, no account beyond
the mailbox you already have.

Gmail needs an *app password*, not your real password —
[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
Full steps in [EMAIL_SETUP.md](EMAIL_SETUP.md).

`.env` already has `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` and `SMTP_FROM_EMAIL`
filled in; only the password is missing. Then:

```bash
python src/monitor.py --email
```

**Why this is the better default than WhatsApp for a weekly digest:** no
window to keep open, no 72-hour re-join, no balance to run down, no trial to
expire. WhatsApp is nicer to read on a phone; email is the one that will still
be working in six months without you thinking about it.

---

## Gmail API — reading newsletters

**What it costs.** Nothing. Personal Gmail API use is free.

Four configured sources have no feed and arrive as newsletters instead. `--gmail`
reads them from **one label you create**, read-only. The scope is
`gmail.readonly` and `gmail_reader.py` refuses any label but the configured one,
so it cannot read the rest of your mail and cannot send, label, archive or
delete anything. Setup is in the README.

---

## An AI web tool — the summaries

**What it costs.** Whatever you already pay for Claude or ChatGPT. **No API key,
no per-run cost, and no account this project holds.** You are the transport: the
tool writes a briefing, you paste it in, you paste the reply back.

This is deliberate. An API key would mean a balance to watch and a bill to cap.
See [BUILD_STEPS.md](BUILD_STEPS.md) for what an API-key version would involve
if it is ever worth it, and [SAFEGUARDS.md](SAFEGUARDS.md) section C for the cost
rules it would have to follow.

---

## Vercel — hosting the dashboard

**What it costs.** Nothing on the Hobby tier for a personal, non-commercial
project. Deployments are manual (`vercel deploy`), so nothing builds unless you
ask it to.

Two things to know:

- The deployed digest is **frozen at deploy time**. Locally the dashboard
  re-reads `web/lib/digest.json` on every request, so `--json` shows up on a
  refresh; on Vercel it does not. Redeploy to update it.
- Deployments are behind **Vercel Authentication** by default, so the link only
  opens for you. Turning that off makes it public to anyone with the URL — see
  the Twilio exposure note above before you do.

---

## Supabase — removed

Deleted on 17 September 2026. `web/lib/supabase.ts` and the `@supabase/supabase-js` dependency
were both present and **imported by nothing**, which is exactly the state this project's rules
forbid: something that looks like a live integration but is not one.

The dashboard reads `web/lib/digest.json`, written by the Python side. Read state lives in the
browser's local storage, so it is per-browser and does not follow you to another machine. That is
the honest trade of keeping everything on one laptop, and it is the current design rather than a
gap waiting to be filled.

If a hosted database is ever wanted, it starts from item 7 of
[IMPROVEMENTS.md](IMPROVEMENTS.md) — and the first question is the privacy one, since it moves
teasers and links off this machine.

---

## What to avoid

| Tempting | Why not |
|---|---|
| Upgrading Twilio "to be safe" | It is the opposite of safe — upgrading is what makes charges possible |
| Buying a phone number | Recurring monthly cost, and the sandbox does not need one |
| Putting Twilio credentials in Vercel | The send endpoint has no auth; see the exposure note |
| An Anthropic/OpenAI API key | Not needed — your existing subscription does the summarising for free |
| A paid news subscription | [PAID_CONSIDER_LATER.md](paid_later/PAID_CONSIDER_LATER.md): pay for a gap you actually hit, not in advance |
| Anything that fetches article bodies | [SAFEGUARDS.md](SAFEGUARDS.md) section A — the paywall boundary is the one rule with no exceptions |
