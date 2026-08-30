# Advice Industry Monitor

A small, safe, free-first tool to keep across the financial advice industry.

## The one rule that keeps this legitimate
**Feeds in, free sources out. Never fetch, store, or reconstruct anything behind a paywall.**
The tool reads only what publishers serve to the public (RSS feeds, free teasers) and,
when it hits a paywall, searches your *free* sources for the same story. It never logs in
or reads locked text. This is baked into the code comments — keep it there.

## Folder
- `free_subscriptions/FREE_SIGNUPS.md` — what to sign up to (all free) and how.
- `paid_later/PAID_CONSIDER_LATER.md` — paid options for when there's budget. Not needed now.
- `IMPROVEMENTS.md` — staged ideas for newcomer explanations, cost controls, and review habits.
- `data/sources.json` — your flagged source list. Add RSS feed URLs as you confirm them.
- `src/monitor.py` — parts 1–3. Runs offline; AI parts need an API key.
- `src/gmail_reader.py` — read-only Gmail adapter for the `advice-monitor` label.
- `src/gmail_dry_run.py` — local Gmail assessment command; never writes to Gmail.

The **Gmail Postmaster Tools API is not used here**. It reports sending-domain reputation and
traffic statistics; it does not read inbox messages. Do not use the Postmaster scope or
Postmaster quickstart for this project. The inbox reader requires the Gmail API and the single
read-only scope `https://www.googleapis.com/auth/gmail.readonly`.

## Setup (in VS Code)
1. `pip install feedparser anthropic`
2. Run `python src/monitor.py` — you'll see your sources + a demo digest. (Confirmed working.)
3. Add real RSS feed URLs to `data/sources.json` (find them on each site — RSS icon, or
   try /feed or /rss, or view page source). Start with 2–3 sources.
4. For AI parts, set your key: `export ANTHROPIC_API_KEY=sk-...` then call with `use_ai=True`.

## Email digest (optional)
Add `--email` flag to send a weekly digest to your inbox instead of printing:
```bash
python src/monitor.py --email
```
Requires a Gmail app password (free, 5-minute setup). See [EMAIL_SETUP.md](EMAIL_SETUP.md) for details.

## AI summaries (optional)
By default, digests show publisher teasers (free, no API cost). To add AI one-sentence summaries:
```bash
python src/monitor.py --ai --email
```
Requires an Anthropic API key with prepaid balance (costs cents per week, only when you run).
See [BUILD_STEPS.md](BUILD_STEPS.md) for the two-mode philosophy.

## Local Gmail dry run

Gmail access is optional and uses Google's Gmail API quota, not a Claude API call. For this
local read-only test, create a normal Google Cloud project and enable Gmail API; do **not** start
the general Google Cloud free trial, activate a paid account, add a billing account, or enter a
card. Create an OAuth **Desktop app** credential and download the JSON file as
`credentials.json` into the project folder. Do not commit it. Install the optional dependencies
with `pip install -r requirements-gmail.txt`.

Google may show an unverified-app warning while the OAuth app is in testing. That is expected for
a personal test app: add your own Gmail address as a test user and continue only if the requested
scope is Gmail read-only. If the console requires billing before enabling Gmail API, stop rather
than adding payment details and we will use the manual no-API workflow instead.

Run a small first test:

```bash
python src/gmail_dry_run.py --max-messages 2 --newer-than-days 14
```

The first run opens Google's consent page. Select the account containing the `advice-monitor`
label and grant read-only access. The token is stored locally in `token.json`, which is ignored
by Git. The command reads only that label, ignores attachments, does not follow links, and does
not modify Gmail. Delete `token.json` to remove the local credential and repeat consent; revoke
Google's permission separately from your Google Account security settings.

## Cost (order of magnitude, verify current pricing)
- Parts 1 & 2 offline: $0.
- AI summary (weekly, small model, batched): cents per week.
- Part 3 lookups: ~a cent or two each.
- Personal scale total: a few dollars a month, not hundreds.
Keep it cheap: batch weekly, store summaries not full text, use the small model for
routine work and a capable model only for chat answers (Part 4, not built yet).

## Part 4 (the chatbot over your filed content) — next step, not built
Once Parts 1–3 are running and you've filed a few weeks of summaries, Part 4 answers
questions like "what's happening in super, any client impact?" over your stored summaries
(not the whole firehose — that's what keeps it cheap). Build it after the intake loop works.

## Risks (short)
- AI can drop a qualifier → summaries triage; read the source for anything you'd act on.
- Product-provider sources (Macquarie/CFS) → great technical detail; confirm rules vs ASIC/law.
- Free tiers change → re-check "Verify" sources every few months.
- Sharing this tool → the same rule binds anyone who uses it. No bypassing, ever.
