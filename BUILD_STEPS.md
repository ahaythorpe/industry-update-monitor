# Build steps and mode guide

After Phase 1 is running, the next stage adds AI summaries. This doc explains how the two modes work, when to use each, and the honest guardrails around costs.

---

## The two modes: free collation vs. AI summarising

The tool has two distinct layers that answer different questions. You run the first forever for free; you add the second deliberately, cheaply, and reversibly.

### Mode 1: Free (switch OFF, no API key, no cost)

**What it does:**
- Collates your RSS feeds and newsletters.
- Prioritises each item into 🔴 **ACT** / 🟠 **KNOW** / 🟢 **NOTE** using keyword rules.
- Surfaces the item's *existing teaser* — the summary the publisher already wrote and put in the RSS feed or newsletter.
- Preserves the source link.

**What it doesn't do:**
- It does not rewrite or condense text.
- It does not decode jargon.
- It does not cost anything.

**The honest use case:**
This mode solves the *organisation* and *prioritisation* problem. You get the feeds sorted, the highest-risk items flagged 🔴, and the publisher's own summary right there. It's genuinely useful — no tool has solved this without a paywall or ads — but if the source writes dense prose or uses unexplained jargon, you'll still read it as the publisher wrote it.

This mode runs indefinitely. Keep the switch `OFF` for as long as the publisher teasers are enough.

**Requirements:**
- None. No API key, no cost control, no .env setup.

---

### Mode 2: AI (switch ON, API key, costs cents, optional)

**What it does:**
- Batches your filtered items once a week (you pick which ones).
- Sends them to Claude Haiku (small, cheap model).
- Returns plain-English summaries, decodes jargon, explains why it matters.
- Still preserves the source link; still uses keyword priorities to skip low-value items.

**What it doesn't do:**
- It doesn't read the full article. It summarises the teaser you already decided was worth looking at.
- It doesn't cost anything unless you turn it on.
- It doesn't decide what you should do. It's triage; you verify everything at source.

**The honest use case:**
Once you've built the habit and accumulated volume, reading a hundred teaser headlines a week gets slow. AI summaries cut that — "explain this in plain English for a learner" — and cost a fraction of a cent each when batched. That's the "decode and compress" layer on top of the free collation.

**Cost and control:**
- Batched weekly: ~cents per week on personal scale.
- Prepaid cap: set a $10 prepaid balance (auto-reload OFF) before you ever need the key.
- Switch-based: `USE_AI = True` in code, but it does nothing without the key.
- Reversible: delete the API key from `.env` or flip the switch back to False, and you're instantly back to free mode. Nothing is locked in.

**Requirements:**
1. An Anthropic API key with a prepaid-capped balance ($10, auto-reload off).
2. The key stored in your `.env` (Git-ignored, never committed).
3. The switch `USE_AI = True` in the code.

---

## When to turn Mode 2 ON — the honest sequence

**Don't switch it on yet.** Run Mode 1 (free) for a good while first. Here's the honest discipline:

1. **Run free, accumulate, build the habit** (weeks 1–6).
   - Switch stays OFF.
   - Weekly digest shows collation, priorities, and publisher teasers.
   - You're getting comfortable with the tool and seeing what comes in.
   - Cost: $0.

2. **When teasers aren't cutting it** (usually week 6+):
   - You've got enough volume that reading headlines is getting slow.
   - Publisher summaries are too jargony or too short for some items.
   - You want plain-English explainers for the ones you've flagged 🔴 or 🟠.
   - **Only then**, consider the next step.

3. **Set up the prepaid cap** (before touching the key):
   - Create an Anthropic account.
   - Add a $10 prepaid balance (no auto-reload, no card linked for overages).
   - Store the balance detail somewhere safe — you'll check it quarterly.
   - This cap is the guarantee: you cannot spend more than $10 without deliberately reloading.

4. **Add the API key to `.env`**:
   - Get your Anthropic API key.
   - Add it to `.env`: `ANTHROPIC_API_KEY=sk-...`.
   - Commit `.env` to `.gitignore` (it already is).
   - Never commit the key itself.

5. **Flip the switch**:
   - Set `USE_AI = True` in `src/monitor.py` (or wherever the flag lives).
   - Run the tool. AI summaries start appearing alongside the teaser.

6. **Use it, watch the spend, decide**:
   - Run weekly, batch your items, get summaries.
   - Check your prepaid balance monthly.
   - If it's working and costs are as expected, keep it on.
   - If you want to stop: flip the switch back to False or delete the `.env` key. Instant. No lockout, no surprise charges.

---

## The mental model to hold

Think of the two modes as **two tiers doing two different jobs**:

- **Free tier** answers: "*What came in and what matters most?*" (collate, prioritise, show publisher teasers).
- **AI tier** answers: "*What does this actually mean in plain English?*" (summarise, decode jargon, plain-language explanation).

You get the first forever. You add the second only when:
- You have enough volume that teasers aren't enough.
- You've capped a prepaid balance.
- You've put the key in `.env`.
- You've flipped the switch.

And it's reversible any time. Flip the switch back or delete the key, and you're back to free mode with zero cost.

---

## Implementation note for Phase 3

When building Phase 3 (AI summaries), make sure:
1. The `USE_AI` flag defaults to `False`. Summarising never happens unless the user explicitly asks for it.
2. The code checks for the key in `.env` before calling the API. If the key is missing, log a clear message: "AI mode is on but no API key found. Set `ANTHROPIC_API_KEY` in `.env` to enable summaries."
3. Summaries preserve the original source link in every item.
4. Summaries use the teaser text only — never fetch or reconstruct the full article.
5. Weekly batching is the design; batch only your filtered picks, not the whole firehose.

See `SAFEGUARDS.md` for the full cost and output rules.
