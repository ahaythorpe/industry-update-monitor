# Industry Update Monitor

A free, private tool for keeping up with the Australian financial advice
industry without drowning in it.

Every week it reads the public news feeds of the advice trade press and the
regulators, sorts each article by urgency, 🔴 **Act now** (could change what an
adviser must do), 🟠 **Worth knowing** (useful context) or 🟢 **Background**, and
by topic (Regulation, Super & tax, Insurance and so on), checks every link still
works, and puts the result on a dashboard in your browser. A model on this laptop
writes three or four plain-English dot points for each story, from the article
text the publisher puts in their own feed. No API key, no bill, and nothing
behind a paywall, ever.

In the code and on the command line the urgencies are still called `ACT`,
`KNOW` and `NOTE`; everything you read says Act now, Worth knowing and
Background.

**The one rule:** feeds in, free sources out. The tool never logs in anywhere,
never fetches a paywalled article, and never pretends a feature works when it
has not been set up. A summary is for sorting; a 🔴 ACT item is always read at
its original source.

---

## Do it yourself — this week's newsletter

No Claude needed. About 25 minutes, most of it waiting. First time? Set up the
local model once with [SETUP.md Part 2](SETUP.md#part-2--ollama-summaries-from-a-model-on-this-laptop)
and Telegram once with [SETUP.md Part 5](SETUP.md#part-5--telegram--free).

1. **Open the Ollama app.** Check the little llama icon is in the menu bar at
   the top of the screen. That is the model that writes the summaries.
2. **Open Terminal** and go to the project folder, then switch on its Python:

   ```bash
   cd ~/Projects/advice-monitor
   source .venv/bin/activate
   ```

   (On someone else's Mac, `cd` to wherever their copy of the project folder is.)
3. **Fetch this week's news** — about a minute:

   ```bash
   python src/monitor.py --json
   ```

4. **Have the model summarise every item** — on this Mac, free, about 20
   minutes. Leave it running; don't close the window:

   ```bash
   python src/monitor.py --ollama
   ```

5. **Sanity-check the summaries.** Skim `output/ollama-reply.md`, or open the
   dashboard (below). A summary is for sorting — a 🔴 ACT item is still read at
   its source.
6. **Send it to yourself:**

   ```bash
   python src/monitor.py --email --from-digest
   python src/monitor.py --telegram --from-digest
   ```

   Success looks like `✅ Digest emailed to …` and
   `✅ Newsletter sent to Telegram (50 stories).` What arrives depends on
   whether the dashboard is online yet (`DASHBOARD_URL` in `.env`):

   | | Dashboard not online yet (now) | Dashboard online |
   |---|---|---|
   | **Email** | The full newsletter: Act now first, then each topic with every story's dot points, a 👀 Read these yourself list, a 📖 Jargon buster and the sources | A one-minute alert: the Act now stories with their first dot point, the week by topic in one line, and a button to the dashboard |
   | **Telegram** | One message with the headlines, Act now first, and the full newsletter attached as a file you tap to open | One short message: the Act now headlines, the week by topic, and a link to the dashboard |

   If Telegram is not set up yet, it prints the message instead. Nothing is lost.

The Sunday 21:00 run does steps 3, 4 and 6 by itself — one newsletter a week,
by email and Telegram.

### Sending an extra, focused update

Any time after step 4, send just the part you care about — by urgency, by
category, or both. Add `--email` or `--telegram` (or run it twice for both):

```bash
python src/monitor.py --telegram --from-digest --only-urgency KNOW --only-category "Super & tax"
python src/monitor.py --email    --from-digest --only-urgency ACT
python src/monitor.py --telegram --from-digest --only-category "Regulation,Compliance"
```

Urgencies: `ACT`, `KNOW`, `NOTE`. Categories: Compliance, Regulation, Super & tax,
Insurance, Key personnel movements, Business, Markets & investing, Fees &
pricing, Practice & technology, General. A misspelt one is refused with the
list, rather than sending an empty update. Or just ask Claude: "send me the
KNOW stories on Super".

---

## Your week

1. **Sunday 21:00 — it runs by itself.** The laptop fetches the week's news,
   writes the dashboard's digest, a sweep sheet and a briefing, and — if Ollama
   is open — writes a summary of every item (about 2.5 hours), so it is ready by Monday morning. Once the
   summaries are written it **emails the newsletter to you**, your own
   address only. It also sends it to your Telegram chat. It never sends to anyone else. If the laptop was closed at 21:00, it runs when it
   next wakes. What happened is in `output/weekly-run.log`.
2. **Open the dashboard.** In a terminal: `cd web && npm run dev`, then go to
   **http://localhost:3000**.
3. **Read, Act now first.** Open the 🔴 Act now box and read each story, then
   check each at its source before acting on it. Then open the topic boxes that
   matter to you. Tick **Read** as you go.
4. **Take what you need away** with the small ⬇ on any box: that group's
   headlines, dot points and links as a file to send a friend or give an AI
   tool for an overview.
5. **Optional: send it to your phone** — `python src/monitor.py --telegram --from-digest`,
   free. Only once set up (see [SETUP.md](SETUP.md) Part 5).

Commands you might type (from the repo folder, after `. .venv/bin/activate`):

```bash
python src/monitor.py --json       # refresh the digest now instead of waiting for Monday
python src/monitor.py --ollama     # write the summaries now (Ollama must be open)
python src/monitor.py --sweep      # a tickable reading sheet for the week, in output/
python src/monitor.py --email      # email the digest to yourself
python src/monitor.py --telegram --from-digest   # send the saved digest to your Telegram
python src/monitor.py --preview    # see the email first, as output/digest_preview.html
```

**Not yet connected:** four sources arrive only as email newsletters (ABS, FS
Industry Moves, Macquarie Technical Services, CFS FirstTech) and reach no digest
until the Gmail intake is set up — [SETUP.md Part 4](SETUP.md#part-4--the-gmail-newsletter-intake).
Until then a quiet week in the digest is not proof of a quiet week; check those
four by hand.

---

## The dashboard

**Public copy:** https://advice-monitor.vercel.app, for anyone, updated by the
Sunday run. **📚 Past weeks** at the top lists every earlier week.

- **By urgency**: four boxes, 🔴 Act now, 🟠 Worth knowing, 🟢 Background and
  👀 Read these yourself (stories the summariser could not read, because the
  publisher only shares a teaser). **By topic** below: one box per topic, with
  an icon, a count and a bar showing its mix of urgencies.
- **Tap a box** and it opens as a pop-up with every story: its dot points, who
  wrote them, a **Source →** link and a **Read** tick box. Esc or ✕ closes it.
- **Dotted words** are terms from the glossary (`data/glossary.json`). Hover
  or tap one to see what it means, for example CSLR (Compensation Scheme of
  Last Resort).
- **⬇ Download**: the small ⬇ on each box and pop-up, and **⬇ Download the
  whole week** at the top, save a Markdown file of those stories: headline,
  dot points, source and link, with the terms explained at the end. Made to
  send a friend or paste into an AI tool. It never includes the article text.
- **All stories**: the full list, with search and filters (source, category,
  date, urgency, link kind) and **Hide stories I've read**. A **timeline**
  shows which days carried stories; click one to filter to it.
- **Read state**: kept in this browser only; there are no accounts.
- **☀ / ☾** switches light and dark. **⚙ Settings** explains sources, email and
  Telegram.
- **Advanced: export stories to paste into an AI chat** (folded away): the
  older copy-and-paste route, for summarising in a chat tool by hand. With the
  local model writing the summaries you should not need it.
- **Send this week to Telegram**: the same message the Monday run sends, to
  your own chat only, once the bot is set up in `web/.env.local`. Otherwise it
  shows the message instead.
- **Bibliography**: every publisher this week drew on, with each article
  linked, and **Download all links**.

Summaries appear labelled "Summarised by a local model (qwen3:8b)" or
"Summarised by hand", never as the tool's own work.

A copy of the dashboard can be put on a private Vercel link — see
[SETUP.md](SETUP.md#the-dashboard-on-a-vercel-link). That copy is frozen at the
time it was made and can never send.

---

## The other documents

| Document | Read it when |
|---|---|
| [SETUP.md](SETUP.md) | Installing, or turning on Ollama, email, Gmail intake or Telegram. Also: what each costs and how to keep it free, and how to stop the Monday run |
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | You want to know where the text comes from, why a paywall cannot be reached, and how summarising works with no API |
| [SAFEGUARDS.md](SAFEGUARDS.md) | The rules the tool is built to — paywall, cost, the summarising prompt |
| [IMPROVEMENTS.md](IMPROVEMENTS.md) | The numbered list of what has been built and what is still open |
| [HANDOVER.md](HANDOVER.md) | A developer is picking this up: code layout, command reference, open work |
| [archive/](archive/README.md) | Old plans and setup pages, kept for history. Superseded — do not follow them |

Sources and their notes: [data/sources.json](data/sources.json). Free newsletters
worth signing up to: [free_subscriptions/FREE_SIGNUPS.md](free_subscriptions/FREE_SIGNUPS.md).
