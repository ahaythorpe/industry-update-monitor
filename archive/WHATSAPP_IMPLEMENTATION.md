# WhatsApp — the implementation brief

For the developer taking stream A of [HANDOVER.md](../HANDOVER.md). The companion
to [OLLAMA_SETUP.md](OLLAMA_SETUP.md): that one is a feature with nothing built,
this one is a feature that mostly works and has one real hole in it.

Read [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) first. It is written for the person
using the tool, and it is also the specification: **a charge must remain
impossible**. Everything below is constrained by that.

---

## What is already built

| | |
|---|---|
| `src/whatsapp_sender.py` | Formats the digest, splits on item boundaries under WhatsApp's 1600-character cap, repeats a heading when a section continues, numbers the parts, and translates Twilio rejections into plain words (`explain_twilio_error`) |
| `web/lib/whatsapp.ts` | The same formatting in the browser, so the dashboard preview matches what the CLI sends |
| `web/app/api/whatsapp/send/route.ts` | The dashboard's send endpoint |
| `tests/test_whatsapp_errors.py` | The closed window, bad credentials, an unknown code, a non-JSON response |
| `web/lib/whatsapp.test.ts` | The browser-side formatting and splitting |

With no credentials anywhere, both sides return the exact message bodies
instead of sending. That is not a stub — it is the mode the project is designed
to be usable in, and it must keep working.

**You do not need a Twilio account to do most of this work.** Run
`python src/monitor.py --whatsapp --per-flag 2` and read what comes out.

---

## Job 1 — close the send endpoint

This is the reason the stream exists.

`POST /api/whatsapp/send` reads `phoneNumber` from the request body and sends to
it. There is no authentication and no rate limit. Today that is harmless:
no Twilio credentials exist in the deployment, so the route returns a preview.
It stops being harmless the moment credentials are added to Vercel — anyone who
finds the URL can aim your Twilio balance at their own phone.
[INTEGRATIONS.md](INTEGRATIONS.md#the-one-real-exposure--read-this-before-making-the-site-public)
has the current warning.

Four ways to fix it. Pick one and write down why.

**A. Send only to `WHATSAPP_TO`, ignore the body.** The smallest honest fix.
The endpoint stops being a "send to anyone" API and becomes "send me my own
digest". A stranger who finds it can, at worst, message your phone.
*Trade-off:* the dashboard's recipient field becomes decorative, so remove it
rather than leave a box that does nothing — the project's rule is that nothing
which does not work may look like it does.

**B. Keep sending on the command line only.** Leave the deployed route in
preview mode permanently and delete the send path from it. *Trade-off:* none
technically; the dashboard already previews, and `python src/monitor.py
--whatsapp` is the documented route. This is the honest choice if nobody
actually wants to send from a browser.

**C. A shared secret header.** The endpoint requires a header matching a value
in the server environment. *Trade-off:* real protection, but the secret has to
live in the browser for the dashboard button to work, which means it is not
secret. Only worth it for a server-to-server caller, which does not exist here.

**D. Real authentication.** Accounts, sessions, the lot. *Trade-off:* out of
proportion to a personal tool, and it drags in the database question that item 7
of [IMPROVEMENTS.md](../IMPROVEMENTS.md) has not answered.

**Recommended: A, or B if nobody wants browser sending.** Whichever you choose,
update both docs that currently describe the present behaviour —
[WHATSAPP_SETUP.md](WHATSAPP_SETUP.md)'s "never in Vercel" block and
INTEGRATIONS.md's exposure section. A fix that leaves the warnings stale is half
a fix.

### While you are in there: bound the cost

`perFlagLimit` is taken from the request body and only checked for being a
number. A large value means more items, more parts, and more messages against
trial credit. Clamp it to the same range the CLI allows.

---

## Job 2 — carry the summaries

`_format_item` in `src/whatsapp_sender.py` reads only `summary`, which is the
publisher's teaser. A summary you wrote by hand lands in `ai_summary` and never
reaches WhatsApp — the dashboard shows it, the message does not. Same cause and
same fix as the email digest; it is item 4 of IMPROVEMENTS.md, and doing both at
once is sensible.

Rules: label the origin the way the dashboard does ("Summarised by hand"), never
present it as something the tool generated, and keep the source link on the
item. `web/lib/whatsapp.ts` needs the same change or the preview stops matching.

---

## Job 3 — say what happened when a send fails

The Python sender translates every Twilio rejection into a sentence with a fix
in it. The web route does not: it logs the detail server-side and returns
`Twilio rejected the message (HTTP 502)`, which tells the person nothing.

- Port the translation, or expose `explain_twilio_error`'s table to both sides
  so there is one list rather than two that drift.
- **Report partial sends.** A digest can be three messages. If part 2 fails,
  part 1 has already arrived and been charged for. The route currently returns
  a bare error; it should say how many parts went and which one failed.
- **Never retry.** The agent rules ban retry loops, and a retry against a
  messaging API is how a free trial becomes a bill. A failure is reported, not
  worked around.

---

## Job 4 — the 24-hour window, if scheduling happens

A sandbox send is refused unless the recipient's phone messaged the sandbox in
the last 24 hours, and a join lapses after 72. That is WhatsApp's rule, not a
bug, and the paid way around it (an approved template, a Business sender, Meta
verification) is explicitly out of scope.

So if item 6 — a scheduled weekly run — is built, the WhatsApp step must expect
the refusal, report it plainly, and leave the digest written to disk so nothing
is lost. It must not silently swallow the failure and it must not retry.

---

## Rules that do not bend

- Never buy a Twilio number. Never upgrade the account. A trial account has no
  card on file, so a failed send cannot become a charge.
- Preview mode with no credentials keeps working, on both sides.
- The Python and TypeScript formatters stay in step. They are tested
  separately; if they drift, the dashboard preview stops being a preview.
- An unrecognised Twilio code still surfaces Twilio's own message. Nothing is
  hidden by not being on the translation list.
- Nothing that is not configured may look live. `/api/status` reports what the
  server can really do; anything you add follows that.

---

## Done looks like

- [ ] The send endpoint cannot be aimed at a stranger's phone, by whichever of
      A–D you chose, and the reason is written down.
- [ ] `WHATSAPP_SETUP.md` and `INTEGRATIONS.md` describe what the code now does.
- [ ] `perFlagLimit` is clamped.
- [ ] A hand-written summary reaches the WhatsApp message, labelled as one.
- [ ] A failed send says what to do about it, from either route.
- [ ] A partial send says how many parts arrived.
- [ ] No retry loop anywhere in the path.
- [ ] Preview mode still works with no credentials, on both sides.
- [ ] `python -m pytest -q` and `cd web && npm test` both green.
- [ ] Item 10 of IMPROVEMENTS.md updated to say what was built and what is open.
