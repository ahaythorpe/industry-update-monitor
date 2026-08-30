# Advice Monitor Agent Rules

These rules are mandatory for every agent working in this repository.

## Source boundary

- Use only sources explicitly listed in `data/sources.json`.
- Only `free` and `free_signup` sources may be processed by automation.
- Never log in to a publisher, follow a subscription flow, or use a user's session.
- Never fetch, render, cache, store, or reconstruct paywalled article text.
- Never scrape Spotify or download or transcribe protected podcast audio.
- For a paywalled story, use only its public title and teaser to search approved free sources.
- Stop and ask when the access method, licence, or source status is unclear.

## Gmail boundary

- Gmail access is read-only and limited to the `advice-monitor` label.
- Use the smallest practical date and message limits during local testing.
- Never read the whole mailbox, follow links, download attachments, or perform Gmail writes.
- Keep dry-run mode enabled until the user has reviewed multiple reports.
- Do not activate Google Cloud billing or a free trial for Gmail access; stop if billing is required.

## Allowed inputs

Automation may process only public RSS fields, newsletters the user legitimately received,
public teasers, official show notes, or transcripts the user is authorised to process.
Article-page bodies and protected media are never valid inputs.

## Output and cost boundary

- Preserve the original source link in every digest or summary.
- Treat AI output as triage. The user verifies every `ACT` item at the primary source.
- Prefer no-AI processing. If AI is enabled, batch weekly, process selected items only, and
  enforce item, token, and prepaid-budget limits.
- Store short summaries and metadata, not a content firehose. Do not add agentic retry loops.

When a request conflicts with these rules, refuse that part and offer a compliant free-source
alternative. Read `SAFEGUARDS.md` for the full design constraints before expanding the system.