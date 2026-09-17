# Ollama — summaries from a model running on this laptop

Phase 3 of [PRD.md](PRD.md) is a weekly AI summary. There are three ways to get
one, and this is the third:

1. **By hand** — `--brief`, paste into a web AI tool, `--import-summaries`.
   Built, free, and what the project uses today. See [README.md](README.md).
2. **A paid API** — not built. Gated on item 2 of [IMPROVEMENTS.md](IMPROVEMENTS.md),
   which is the cost-control work that must exist before a key does.
3. **A local model through Ollama** — this page. No key, no bill, no account,
   and nothing leaves the machine.

Option 3 is attractive here because the cost gate that blocks option 2 does not
apply: there is no per-call price and no bill to cap. What it costs instead is
disk, memory and a warm laptop.

---

## What it does not change

Read this before writing any code. None of it is softened by the model being
local.

- **The paywall boundary is unchanged.** The input stays the feed's own title
  and teaser, exactly as [SAFEGUARDS.md](SAFEGUARDS.md) section A requires. A
  local model is not a reason to fetch an article body — nothing in this
  codebase fetches one, and that stays literally true.
- **Regulator PDFs are still fine, trade-press articles are still not.** Same
  rule as the manual route.
- **AI output is triage.** Every summary keeps its source link, and an ACT item
  is still read at the primary source. A local model hallucinates like any
  other.
- **It is off unless asked for.** No flag, no model call. `.github/copilot-instructions.md`
  is the binding version of all of this.

---

## Install, about 20 minutes plus the download

```bash
brew install ollama          # or download from ollama.com
ollama serve                 # runs on 127.0.0.1:11434 until you stop it
```

In a second terminal, pull a model and check it answers:

```bash
ollama pull llama3.1:8b      # ~5 GB; check ollama.com/library for current names
ollama list
ollama run llama3.1:8b "Reply with the single word: ready"
```

**On model choice.** An 8B-class instruct model is enough for one-sentence
triage of a teaser, which is all this task is. Quantised it is roughly a 5 GB
download and wants about 8 GB of free memory to run comfortably. A bigger model
is slower for very little gain on a job this small; a much smaller one starts
inventing detail, which is the one failure that matters here. Model names and
sizes change — confirm at ollama.com/library rather than trusting this page.

Ollama listens on localhost only. It is not reachable from outside the machine
unless you deliberately expose it, and there is no reason to.

---

## Prove it works before writing any code

Take one block out of a briefing and send it by hand. This is the whole
integration in one command:

```bash
python src/monitor.py --brief                    # writes output/briefing.md
```

Copy the first block (prompt plus a few items) into a file, then:

```bash
curl -s http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "<paste one briefing block here>",
  "stream": false,
  "options": {"temperature": 0}
}' | python3 -c "import json,sys; print(json.load(sys.stdin)['response'])"
```

What you want back is one line per item in the shape the round trip already
speaks:

```text
a1b2c3 | ACT | ASIC banned the adviser for ten years. | https://...
```

If the reply comes back in that shape, save it as `output/reply.md` and run the
existing importer — no new code at all:

```bash
python src/monitor.py --import-summaries output/reply.md
```

If it does not, the model is the problem, not the plumbing. Lower the
temperature, cut the block size, and only then consider a different model.

---

## Wiring it into the repo

For whoever implements this. The point of the design below is that almost
nothing new is needed: the briefing format, the reply format, the ID matching
and the import already exist and are tested.

- **Opt-in flag**, `--ollama`, defaulting off. Nothing implicit.
- **Reuse `format_briefing`.** The blocks it writes are the prompt — `BRIEF_PROMPT`
  is SAFEGUARDS section D verbatim and must not be rewritten for the model's
  convenience. `--deep` and `DEEP_PROMPT` are the second pass, same rule.
- **POST to `http://localhost:11434/api/generate`** with `stream: false` and
  `temperature: 0`. One request per block, in sequence. No concurrency: this is
  a weekly batch on a laptop, not a service.
- **Parse with `parse_summaries`.** It already tolerates a chat model's
  bullets, bold and numbering. Do not write a second parser.
- **Stamp the origin honestly.** `import_summaries` hardcodes
  `ai_source = "manual"`. A model-written summary must not claim that: give the
  importer an origin argument and pass `ollama:<model>`, e.g.
  `ollama:llama3.1:8b`.
- **Label it in the dashboard.** `web/app/dashboard.tsx` currently prints
  "Summarised by hand" for `manual` and a bare "Summary" for anything else. A
  local-model summary must say so — "Summarised by a local model (llama3.1:8b)"
  — or the honesty rule in [README.md](README.md) is broken by omission.
- **Fail loudly.** If Ollama is not running, say exactly that and stop. No retry
  loop: `.github/copilot-instructions.md` bans them, and a silent fallback to a
  paid API would be the worst possible bug in this project.
- **Cap the run.** A maximum item count and a per-request timeout, so a stuck
  model cannot hold the weekly run open indefinitely.
- **Nothing leaves the machine.** The only network call is to 127.0.0.1. Assert
  that in a test rather than trusting it.

### Tests worth having

- A fake HTTP server standing in for Ollama, so the path is tested without a
  model installed. Every other test in this repo runs offline and this must
  too.
- Ollama not running → one clear message, no traceback, no retry.
- A reply the model mangled → `parse_summaries` reports the unmatched IDs,
  nothing is guessed at, and no summary attaches to the wrong item.
- The origin recorded is `ollama:<model>`, never `manual`.

---

## What it costs

| | |
|---|---|
| Money | none — no key, no account, no per-call price |
| Disk | ~5 GB for an 8B model |
| Memory | ~8 GB while it runs |
| Time | seconds to a minute per block on a recent laptop |
| Electricity | a warm laptop for a few minutes a week |

The laptop will be slow and loud while a batch runs. That is the whole running
cost, and it is why this is a weekly batch rather than something live.

---

## Turning it off

Leave off `--ollama`. To reclaim the disk:

```bash
ollama rm llama3.1:8b
```

Nothing else in the tool depends on it: with no model and no flag, the digest,
the sweep sheet and the manual round trip all work exactly as before.
