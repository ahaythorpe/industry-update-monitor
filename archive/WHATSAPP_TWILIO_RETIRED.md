# Retired: WhatsApp via Twilio

**Retired 23 September 2026. Do not set this up.** The phone channel is now
Telegram — free, with no trial to run out and no per-message charge. See
[SETUP.md Part 5](../SETUP.md#part-5--telegram--free).

Why it was retired: every WhatsApp route ends up costing money. Twilio's trial
credit runs out and then each message is a few cents; Meta's own WhatsApp
Business route needs business verification and bills per conversation. A
free weekly digest to yourself should not depend on a balance.

The command-line sender still works (`python src/monitor.py --whatsapp`,
`src/whatsapp_sender.py`) and is kept, but it is **optional and not
recommended**. The dashboard's WhatsApp button, its `/api/whatsapp/send` route
and `web/lib/whatsapp.ts` were removed on 23 September 2026, so everything below
about the dashboard button is history. The rules about never upgrading Twilio,
never buying a number and never putting its credentials in Vercel still hold if
anyone ever does use it.

This is the setup page as it stood before the switch, unchanged below this line.

---

## WhatsApp via a Twilio trial (was SETUP.md Part 5)

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
