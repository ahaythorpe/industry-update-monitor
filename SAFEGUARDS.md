# Safeguards — the rules that keep this legal, safe and cheap

Read this before building Phases 3-5 (the phases of the original plan,
[archive/PRD.md](archive/PRD.md)). These aren't nice-to-haves; they're the design
constraints that keep the tool on the right side of the line. If a feature can't be built
within these, don't build it.

---

## A. The paywall boundary (the most important one)

**Rule: the tool only ever reads content legitimately delivered to it. It never touches
locked text.**

Safe (do these):
- Read RSS feeds the publisher publishes on purpose, **including the article
  text they put in `content:encoded`**. That text is part of the feed the
  publisher generates and serves; reading it fetches nothing, visits no article
  page and passes no wall. A publisher who does not want it there does not put
  it there. (Amended 2026-09-15: the rule below used to say title and summary
  only, which threw away most of what the feed offered and made every summary a
  one-liner.)
- Read free newsletters that arrived in your inbox.
- Read the free headline/teaser a publisher shows above its paywall.
- Search free sources (ASIC, AFCA, FAAA, Treasury, ABS, free news) for the same story.

Forbidden (never build these):
- Logging into any publisher site.
- Fetching, rendering, caching or storing article text behind a paywall.
- "Reconstructing" locked content from fragments.
- Any browser-extension-style paywall stripping.

Why it's built this way: working only from feeds + free sources means the tool NEVER visits
the wall, so there's nothing to bypass. This is also simpler to build than the risky version.

How to enforce it in code:
- Input is what the feed hands over: `title`, `summary`, and `content:encoded`
  where the publisher supplies it. Never the article URL's body.
- Feed content is capped (`FEED_BODY_LIMIT`, 1,500 characters) and every item
  records `body_source` — `feed_content` or `feed_summary` — so it is always
  visible which one a summary was written from.
- No function in the codebase should fetch a publisher article page. If you're writing a
  `requests.get(article_url)` against a trade-press URL, stop — that's the line.

The distinction that matters: **what the publisher sends you is safe; what you
go and take is not.** A feed is delivered. An article page is fetched. Nothing
here fetches one.

## B. The "AI triages, source confirms" rule

**Rule: AI never decides a 🔴 ACT item for you, and never replaces reading the source on
anything you'd act on or repeat.**

- AI's job: draft the flag sort, compress 🟠/🟢 items, explain unfamiliar terms.
- Your job: read every 🔴 item at its original source; decide what actually changes.
- Every AI summary MUST carry the source link, so verification is always one click away.
- The summary prompt must forbid invention (see D).

Why: a summary can silently drop a qualifier, and a subtly-wrong rule is worse than none.
The link is the safety net.

## C. Cost safeguards (so there's never a scary bill)

- **Prepaid + spend cap.** Load a small amount of API credit (e.g. $5) and set a spend limit.
  Prepaid means it physically cannot bill beyond what's loaded. This is your hard ceiling.
- **Batch weekly, not live.** One call over the week's items, not one per item as they arrive.
- **Teaser text only.** Summarise the feed's short summary, never full articles (fewer tokens).
- **Store summaries, not the firehose.** Phase 5 queries compressed summaries, so questions
  stay tiny.
- **Right-size the model.** Cheap model (Haiku) for routine summarising; capable model only
  for the chat answers, and only when needed.
- **Short output.** Output tokens cost ~5x input, so force one-line summaries.
- **No agentic loops.** No feature should re-read or re-call in a loop dozens of times per run.

Order-of-magnitude at personal scale: a few dollars a YEAR. Verify current pricing before you
turn AI on.

## D. The anti-hallucination prompt (use verbatim for Phase 3)

> You are helping a trainee financial adviser triage this week's Australian advice-industry
> news. You will be given items, each with a TITLE, a public TEASER, and a LINK. For each item
> output one line: `FLAG | one-sentence summary | LINK`. FLAG is ACT (changes what an adviser
> must do), KNOW (useful context), or NOTE (background/data). Rules: summarise ONLY from the
> teaser given; never invent detail or add facts not present; if the teaser is too thin,
> write "thin — open source"; always keep the LINK unchanged; do not attempt to access anything
> beyond the text provided.

Why each clause matters:
- "only from the teaser" → stops it inventing content it can't see.
- "never invent / too thin → open source" → makes it admit uncertainty instead of guessing.
- "keep the LINK" → preserves your verification path.
- "do not access beyond the text" → reinforces the paywall boundary at the prompt level.

## E. Sharing safeguards (if you ever give this to others)

- The same rules bind anyone who runs it: free/legit sources only, no bypassing, verify ACT
  items at source.
- Personal scale is very different from distribution — at any scale beyond yourself, YOU become
  responsible for how it handles the paywall boundary. Keep it personal until you're sure.
- Don't ship it with your API key in it. Each user brings their own prepaid-capped key.

## F. Source-integrity safeguards

- Product-provider sources (Macquarie, CFS) are excellent technical explainers but come from
  product providers — confirm any RULE against ASIC/the legislation.
- Keep "what happened" (regulator) separate from "what people think" (trade press/FAAA).
- Sources marked "verify" in [FREE_SIGNUPS.md](free_subscriptions/FREE_SIGNUPS.md) aren't confirmed for a free tier — check before
  relying, and re-check every few months since free tiers change.

## G. Focus and source hierarchy

The colour flags are the reading-priority system:

- **RED / ACT** — highest priority. A regulator action, legal or policy change, deadline,
  determination, or other item that could change what an adviser does. Read the original
  primary source; never rely on an automated summary alone.
- **ORANGE / KNOW** — useful industry understanding. Trade press, FAAA commentary, provider
  explainers, and professional discussion belong here unless they point to a confirmed ACT
  source. Summarise selectively and follow important links.
- **GREEN / NOTE** — background, data, appointments, and market context. Skim, retain only if
  it supports a current focus area, and do not let it displace ACT or KNOW reading.

LinkedIn posts are discovery signals, not automatically authoritative evidence. They may reveal
a topic, event, person, or useful source, but the post itself is normally KNOW at most. When a
post points to a regulator, legislation, Treasury consultation, AFCA determination, ABS release,
or other primary source, record and assess that linked source separately. Do not scrape LinkedIn;
use only a post the user has intentionally provided or a public link the user opens themselves.

When deciding whether a topic deserves focus, rank it in this order:

1. Could it change an adviser's obligations, client communication, or deadline? Make it ACT and
   find the primary source.
2. Does it explain a current reform, dispute, industry development, or technical issue? Make it
   KNOW and connect it to the relevant primary source where possible.
3. Is it background or context only? Make it NOTE and include it only when it supports a chosen
   focus area.

This keeps the monitor focused on important areas identified in industry discussion while
preventing social posts or commentary from becoming the source of truth.

---

## Build checklist (safeguard gates before each phase)
- [ ] Phase 3: prompt from section D in place? Batching weekly? Prepaid cap set? Teaser-only?
- [ ] Phase 4: input is feed title+teaser only? No function fetches a publisher article body?
- [ ] Phase 5: querying stored summaries, not full text? Small model for routine Qs?
- [ ] Any phase: does every AI output carry the source link?
