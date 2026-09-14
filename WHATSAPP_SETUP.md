# WhatsApp digest — setting it up without ever being charged

The digest can arrive on your phone as a WhatsApp message. This page is written
to get you there on **free trial credit only**, and to keep it that way.

Before anything else: **email does the same job with none of these limits**, and
`.env` already has your SMTP host, port and user — only the password is missing.
See [EMAIL_SETUP.md](EMAIL_SETUP.md). WhatsApp is nicer to read on a phone. Email
is the one still working in six months without you thinking about it. Running
both is reasonable.

---

## First: see it for free, before signing up for anything

With no credentials at all, the tool prints the exact messages it would send:

```bash
python src/monitor.py --whatsapp --whatsapp-to +61400000000 --per-flag 2
```

Nothing is sent, nothing is charged, no account exists yet. Proof-read the
formatting. If you do not like it, you have lost nothing.

---

## The three rules that make charges impossible

Follow these and Twilio has no mechanism to bill you.

### 1. Stay on the trial account. Never click "Upgrade"

A trial account has **no card on file**. There is nothing to charge. When the
trial credit runs out, sends fail — they do not bill. Upgrading is the single
action that makes a charge possible, and nothing here needs it.

### 2. Never buy a phone number

This is how people get a surprise recurring bill: a number is rented monthly
whether you use it or not.

**The WhatsApp sandbox does not need one.** You use Twilio's shared sandbox
number. If you find yourself on a "Buy a number" screen, you have taken a wrong
turn — back out.

### 3. Keep the credentials on your own machine, never in Vercel

Put them in `.env` at the repo root, which is git-ignored, and send with
`python src/monitor.py --whatsapp`.

> **Do not add Twilio variables to the Vercel project.** The dashboard's send
> endpoint takes the recipient **from the request body** and has no
> authentication and no rate limit. On your own machine that is fine. On a public
> URL with credentials attached, anyone who found it could send messages on your
> account. Without those variables the deployed dashboard stays in preview mode:
> it composes the message and shows it instead of sending. Details in
> [INTEGRATIONS.md](INTEGRATIONS.md#the-one-real-exposure--read-this-before-making-the-site-public).

---

## Setup, about 15 minutes

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
5. **Add four lines to `.env`** in the repo root:

   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_WHATSAPP_NUMBER=+14155238886
   WHATSAPP_TO=+61...your mobile, international format
   ```

6. **Send one**:

   ```bash
   python src/monitor.py --whatsapp --per-flag 2
   ```

   `--per-flag 2` keeps the first real send to one message.

---

## The 72-hour catch — the thing that will actually annoy you

WhatsApp only allows a freeform message **within 24 hours of that phone
messaging you**, and a sandbox join lapses after **72 hours**. A weekly digest is
therefore refused unless you message the sandbox number again first.

So the weekly habit is: **WhatsApp anything to the sandbox number, then run the
digest.** One message, then the command.

If you forget, the run tells you exactly that rather than printing Twilio's raw
error:

```
❌ WhatsApp part 1 not sent. The 24-hour window has closed. WhatsApp only allows
   a freeform message within 24 hours of the recipient messaging you.
   Fix: send any message to the sandbox number from that phone, then re-run.
   On the sandbox you have to do this every 72 hours.
```

The paid way around it is an approved WhatsApp message template, which needs a
WhatsApp Business sender and Meta business verification. That is real setup and
real money for a personal project — **not recommended**.

---

## What a send actually costs

| | |
|---|---|
| Messages per run | 1–3 (`--per-flag 2` gives 1; the default 6 gives 3) |
| Cost each | a few cents — check Twilio's current WhatsApp pricing |
| Monthly, sending weekly | cents, against trial credit |
| Recurring fees | **none**, as long as you never buy a number |

When the trial credit runs out, sends stop. They do not bill.

---

## Other errors, in plain words

Every Twilio rejection is translated (`explain_twilio_error` in
`src/whatsapp_sender.py`):

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

---

## Turning it off

Delete the four lines from `.env`. That is the whole procedure: no account to
close, no subscription to cancel, nothing left running. `--whatsapp` goes back to
printing a preview.
