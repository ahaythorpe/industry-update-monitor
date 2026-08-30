# Improvement list

These are deliberately staged ideas. An improvement is not ready to build until its cost,
privacy, source, and reading-time impact are understood.

## 1. Newcomer explanations

Help explain unfamiliar industry terms and why an item matters, while keeping the evidence
boundary clear.

Requirements:

- Separate **what the email says**, **what is inferred**, and **what still needs checking**.
- Mark inference explicitly with language such as `Possible meaning` or `Needs confirmation`.
- Never present an inference as a legal, compliance, or client-advice conclusion.
- Link to the original email and, where available, the relevant primary source.
- Treat explanations as learning aids, not advice.
- Prefer a local glossary and rule-based explanations before using an AI model.
- ACT items still require reading the primary source.

Example format:

```text
KNOW
What it says: The email mentions a proposed superannuation reform.
Possible meaning: This may affect future policy settings.
Check: Read the Treasury or legislation source before drawing conclusions.
Source: original email link
```

## 2. API cost management

If an AI API is added later, the system must make cost a controlled resource rather than an
unknown bill.

Requirements:

- AI is off by default.
- Use local rules and extractive summaries first.
- Process only user-selected items, not every email.
- Batch one review rather than making live calls.
- Set maximum items, input characters, output tokens, and calls per week.
- Estimate and display cost before a batch runs where pricing allows it.
- Require explicit approval before the first paid batch and after a budget change.
- Use a separate prepaid API balance and provider spending limit; a Claude app subscription
  must not be assumed to cover API use.
- Record date, model, item count, token limits, and estimated/actual cost without storing a
  content firehose.
- Stop when any budget or usage limit is reached. No automatic retry loops.

Suggested initial controls:

```text
AI default: off
Review frequency: weekly
Maximum items: 10
Maximum calls: 1 per week
Budget: user chooses a hard weekly and monthly limit
Fallback: local extractive summary or manual Claude review
```

## 3. Weekly industry review

Support a sustainable learning habit rather than maximising the number of summaries.

- Track total review time and useful items.
- Review ACT items first, then selected KNOW items, then NOTE items if time remains.
- Reassess source value and API spending after several weekly reviews.
- Keep paid subscriptions as a future decision based on a recurring unmet need.