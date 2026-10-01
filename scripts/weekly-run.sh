#!/bin/bash
# Weekly unattended run, started by launchd. See IMPROVEMENTS.md item 6.
#
# It fetches, runs --ollama (which stays on this machine), publishes the
# dashboard, emails the summarised newsletter to EMAIL_ADDRESS and sends a
# short briefing to your own Telegram chat (TELEGRAM_CHAT_ID). It never passes
# --whatsapp or --gmail, and never emails
# anyone else: the recipient is always the account it sends from.

set -uo pipefail

REPO="/Users/bella/Projects/advice-monitor"
LOG="$REPO/output/weekly-run.log"
STAMP="$(date '+%Y-%m-%d %H:%M')"

cd "$REPO" || { echo "$STAMP  FAILED — repo not found at $REPO" >>"$LOG"; exit 1; }
mkdir -p output

if [ ! -x .venv/bin/python ]; then
  echo "$STAMP  FAILED — .venv/bin/python missing; run the Part 1 setup" >>"$LOG"
  exit 1
fi

# Fetch this week's news first, on its own. Until 1 Oct 2026 this step also
# asked for --sweep and --brief, which made monitor.py skip the fetch and
# reuse the old digest while the log said "ok" (IMPROVEMENTS.md item 19).
OUT="$(.venv/bin/python src/monitor.py --json 2>&1)"
STATUS=$?

# Then the sweep sheet and briefing, from the digest just written. --sweep
# refuses to overwrite an existing sheet, because that sheet may hold your
# ticks, so if today's sheet is already there only the briefing is refreshed.
SHEET="output/sweep-$(date '+%Y-%m-%d').md"
if [ $STATUS -eq 0 ]; then
  if [ -e "$SHEET" ]; then
    SWEEP_NOTE=" (sweep sheet for today already exists — left untouched)"
    .venv/bin/python src/monitor.py --brief >/dev/null 2>&1
  else
    SWEEP_NOTE=""
    .venv/bin/python src/monitor.py --sweep --brief >/dev/null 2>&1
  fi
fi

# A digest older than today is last week's news, whatever the exit code says.
FRESH="$(.venv/bin/python -c "
import json, datetime
d = datetime.datetime.fromisoformat(json.load(open('web/lib/digest.json'))['generated_at'])
print('yes' if d.astimezone().date() == datetime.date.today() else d.astimezone().strftime('%-d %b'))
" 2>/dev/null || echo "?")"
if [ $STATUS -eq 0 ] && [ "$FRESH" != "yes" ]; then
  echo "$STAMP  STALE — the digest is from $FRESH, not today; nothing new was fetched" >>"$LOG"
  STATUS=1
fi

# An empty digest that reads as a quiet week is the failure this must not
# produce, so "fetched nothing" is logged differently from "ran fine".
COUNT="$(.venv/bin/python -c "import json;print(len(json.load(open('web/lib/digest.json'))['items']))" 2>/dev/null || echo "?")"

if [ $STATUS -ne 0 ]; then
  echo "$STAMP  ERROR (exit $STATUS) — nothing was written. Last lines:" >>"$LOG"
  echo "$OUT" | tail -5 | sed 's/^/    /' >>"$LOG"
elif [ "$COUNT" = "0" ]; then
  echo "$STAMP  RAN, BUT FETCHED 0 ITEMS — treat as a failure to check, not a quiet week" >>"$LOG"
else
  echo "$STAMP  ok — $COUNT items in the digest; briefing written to output/$SWEEP_NOTE" >>"$LOG"
fi

# Then summarise on this Mac with the local model (about 2.5 hours). A
# separate step, so Ollama being closed costs the summaries, never the digest.
# gpt-oss:20b since 24 Sep 2026 (qwen3:8b misread figures in tables), but it
# is about 13 GB and on 27 Sep 2026 the Mac ran out of memory and nothing was
# sent. Since 1 Oct 2026 a failure is retried with qwen3:8b, which fits.
SUMMARISED=no
if [ $STATUS -eq 0 ] && [ "$COUNT" != "0" ]; then
  if curl -s -m 5 http://localhost:11434/api/tags >/dev/null; then
    for MODEL in gpt-oss:20b qwen3:8b; do
      if OLL="$(.venv/bin/python src/monitor.py --ollama "$MODEL" --ollama-timeout 1800 2>&1)"; then
        echo "$STAMP  ok — $(echo "$OLL" | grep -o '[0-9]* of [0-9]* summaries merged' || echo 'summaries merged') by $MODEL" >>"$LOG"
        SUMMARISED=yes
        break
      fi
      echo "$STAMP  SUMMARIES FAILED with $MODEL. Last lines:" >>"$LOG"
      echo "$OLL" | tail -2 | sed 's/^/    /' >>"$LOG"
    done
  else
    echo "$STAMP  SUMMARIES SKIPPED — Ollama is not running; open the Ollama app" >>"$LOG"
  fi
fi

# Publish the week to the public dashboard, https://advice-monitor.vercel.app
# (since 24 Sep 2026), before anything is sent, so the Telegram link opens on
# this week. Runs even without summaries, so the site never shows last week's
# news. Only web/ is uploaded, and web/.vercelignore keeps .env files out of
# it. launchd does not load nvm, so node and vercel are found by full path.
if [ $STATUS -eq 0 ] && [ "$COUNT" != "0" ]; then
  # Keep this week for the Past weeks page (web/lib/archive/, since 24 Sep 2026).
  .venv/bin/python scripts/archive_week.py >/dev/null 2>&1 \
    || echo "$STAMP  WEEK NOT ARCHIVED — run python scripts/archive_week.py" >>"$LOG"
  NODE_BIN="/Users/bella/.nvm/versions/node/v20.20.0/bin"
  if DEP="$(cd web && PATH="$NODE_BIN:$PATH" vercel deploy --prod --yes 2>&1)"; then
    echo "$STAMP  ok — public dashboard updated at https://advice-monitor.vercel.app" >>"$LOG"
  else
    echo "$STAMP  PUBLIC DASHBOARD NOT UPDATED — it still shows last week. Last lines:" >>"$LOG"
    echo "$DEP" | tail -3 | sed 's/^/    /' >>"$LOG"
  fi
fi

# Email the full newsletter to yourself, only once the summaries exist, so
# you never get a half-finished issue.
if [ "$SUMMARISED" = "yes" ]; then
  # Write the email as it will be sent, for the dashboard's "Preview the
  # email" link. A failure here never stops the sends below.
  .venv/bin/python src/monitor.py --from-digest --preview >/dev/null 2>&1 || true
  if MAIL="$(.venv/bin/python src/monitor.py --email --from-digest 2>&1)" && echo "$MAIL" | grep -q "✅"; then
    echo "$STAMP  ok — newsletter emailed to you" >>"$LOG"
  else
    echo "$STAMP  EMAIL NOT SENT — last lines:" >>"$LOG"
    echo "$MAIL" | tail -3 | sed 's/^/    /' >>"$LOG"
  fi
fi

# The short Telegram briefing goes out whenever there is a fresh week, with
# or without summaries: a story the model could not read says so, and a
# silent Sunday is how 27 Sep 2026 went unnoticed. Your own chat only.
if [ $STATUS -eq 0 ] && [ "$COUNT" != "0" ]; then
  if TG="$(.venv/bin/python src/monitor.py --telegram --from-digest 2>&1)" && echo "$TG" | grep -q "✅"; then
    echo "$STAMP  ok — briefing sent to Telegram" >>"$LOG"
  else
    echo "$STAMP  TELEGRAM NOT SENT — last lines:" >>"$LOG"
    echo "$TG" | tail -2 | sed 's/^/    /' >>"$LOG"
  fi
fi

exit $STATUS
