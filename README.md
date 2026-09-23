# Industry Update Monitor

A free, private tool for keeping up with the Australian financial advice
industry without drowning in it.

Every week it reads the public news feeds of the advice trade press and the
regulators, sorts each article into 🔴 **ACT** (could change what an adviser
must do), 🟠 **KNOW** (useful context) or 🟢 **NOTE** (background), checks every
link still works, and puts the result on a dashboard in your browser. A model
on this laptop can write a short summary of each item. No API key, no bill, and
nothing behind a paywall — ever.

**The one rule:** feeds in, free sources out. The tool never logs in anywhere,
never fetches a paywalled article, and never pretends a feature works when it
has not been set up. A summary is for sorting; a 🔴 ACT item is always read at
its original source.

---

## Your week

1. **Monday 07:00 — it runs by itself.** The laptop fetches the week's news,
   writes the dashboard's digest, a sweep sheet and a briefing, and — if Ollama
   is open — writes a summary of every item (about 20 minutes). It **never sends
   anything** on its own. If the laptop was closed at 07:00, it runs when it
   next wakes. What happened is in `output/weekly-run.log`.
2. **Open the dashboard.** In a terminal: `cd web && npm run dev`, then go to
   **http://localhost:3000**.
3. **Read, ACT first.** Work down the 🔴 items and open each at its source;
   then the 🟠 items that matter to you; skim 🟢 if there is time. Mark items
   read as you go.
4. **Take what you need away** with the Download panel — for example the
   finished summaries as a file to read on the train.
5. **Optional: send it to yourself** — `python src/monitor.py --email` or
   `--whatsapp`. Only once set up (see [SETUP.md](SETUP.md) Parts 3 and 5).

Commands you might type (from the repo folder, after `. .venv/bin/activate`):

```bash
python src/monitor.py --json       # refresh the digest now instead of waiting for Monday
python src/monitor.py --ollama     # write the summaries now (Ollama must be open)
python src/monitor.py --sweep      # a tickable reading sheet for the week, in output/
python src/monitor.py --email      # email the digest to yourself
python src/monitor.py --preview    # see the email first, as output/digest_preview.html
```

**Not yet connected:** four sources arrive only as email newsletters (ABS, FS
Industry Moves, Macquarie Technical Services, CFS FirstTech) and reach no digest
until the Gmail intake is set up — [SETUP.md Part 4](SETUP.md#part-4--the-gmail-newsletter-intake).
Until then a quiet week in the digest is not proof of a quiet week; check those
four by hand.

---

## The dashboard

- **Search and filters** — by source, date, flag, category and link kind, plus
  "hide read". A **timeline** shows which days carried items; click one to
  filter to it.
- **Read state** — tick items off and the Unread count is real. It is kept in
  this browser only; there are no accounts.
- **☀ / ☾** — switch between light and dark. Remembered in this browser.
- **⚙ Settings** — what counts as an eligible source, and how email and
  WhatsApp are set up. Close it with ✕, a click outside, or Escape.
- **Download for summarising** — takes exactly what the filters show:
  - **Detail**: *Triage — one line each*, *Detailed — a short paragraph each*,
    or **Finished summaries — ready to read**: the summaries already written,
    each labelled with who wrote it and next to its link. An item not summarised
    yet says so and shows the publisher's teaser instead.
  - **Split files by** Category, Urgency, both, or neither; **Download as** a
    zip (one file per group) or a single file.
  - Two rows of chips, **Urgency** and **Category**, narrow the download without
    changing what you are reading. Each chip shows how many items it would add.
  - **Copy** puts it straight on the clipboard — the easiest way into Claude or
    ChatGPT, neither of which accepts a `.zip` upload.
  - **ⓘ Never scrapes paid sources** explains where the text comes from.
- **Bibliography** — every publisher this week's digest drew on, with its home
  page and **each of its articles listed and linked**.
- **WhatsApp** — shows the exact messages. It sends only once Twilio is set up
  on this laptop; otherwise it is a preview.
- **Email** — *Preview the email body* in Settings shows what `--email` sends.
  The dashboard itself never sends mail.

Summaries appear labelled "Summarised by a local model (qwen3:8b)" or
"Summarised by hand", never as the tool's own work, with the publisher's teaser
kept beneath.

A copy of the dashboard can be put on a private Vercel link — see
[SETUP.md](SETUP.md#the-dashboard-on-a-vercel-link). That copy is frozen at the
time it was made and can never send.

---

## The other documents

| Document | Read it when |
|---|---|
| [SETUP.md](SETUP.md) | Installing, or turning on Ollama, email, Gmail intake or WhatsApp. Also: what each costs and how to keep it free, and how to stop the Monday run |
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | You want to know where the text comes from, why a paywall cannot be reached, and how summarising works with no API |
| [SAFEGUARDS.md](SAFEGUARDS.md) | The rules the tool is built to — paywall, cost, the summarising prompt |
| [IMPROVEMENTS.md](IMPROVEMENTS.md) | The numbered list of what has been built and what is still open |
| [HANDOVER.md](HANDOVER.md) | A developer is picking this up: code layout, command reference, open work |
| [archive/](archive/README.md) | Old plans and setup pages, kept for history. Superseded — do not follow them |

Sources and their notes: [data/sources.json](data/sources.json). Free newsletters
worth signing up to: [free_subscriptions/FREE_SIGNUPS.md](free_subscriptions/FREE_SIGNUPS.md).
