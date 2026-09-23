#!/bin/bash
# Weekly unattended run, started by launchd. See IMPROVEMENTS.md item 6.
#
# It also runs --ollama afterwards, which stays on this machine, and then
# emails the summarised newsletter to EMAIL_ADDRESS and sends it to your own
# Telegram chat (TELEGRAM_CHAT_ID) — chosen 23 Sep 2026. It never passes
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

# --sweep refuses to overwrite an existing sheet, because that sheet may hold
# your ticks. That is the right behaviour, so the runner works around it rather
# than forcing it: if today's sheet is already there, it is left untouched and
# only the digest and briefing are refreshed.
SHEET="output/sweep-$(date '+%Y-%m-%d').md"
if [ -e "$SHEET" ]; then
  SWEEP_NOTE=" (sweep sheet for today already exists — left untouched)"
  OUT="$(.venv/bin/python src/monitor.py --json --brief 2>&1)"
else
  SWEEP_NOTE=""
  OUT="$(.venv/bin/python src/monitor.py --json --sweep --brief 2>&1)"
fi
STATUS=$?

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

# Then summarise on this Mac with the local model (about 20 minutes). A
# separate step, so Ollama being closed costs the summaries, never the digest.
if [ $STATUS -eq 0 ] && [ "$COUNT" != "0" ]; then
  if curl -s -m 5 http://localhost:11434/api/tags >/dev/null; then
    if OLL="$(.venv/bin/python src/monitor.py --ollama 2>&1)"; then
      echo "$STAMP  ok — $(echo "$OLL" | grep -o '[0-9]* of [0-9]* summaries merged' || echo 'summaries merged') by the local model" >>"$LOG"
      # Email the newsletter to yourself, summaries included. Only once the
      # summaries exist, so you never get a half-finished issue.
      if MAIL="$(.venv/bin/python src/monitor.py --email --from-digest 2>&1)" && echo "$MAIL" | grep -q "✅"; then
        echo "$STAMP  ok — newsletter emailed to you" >>"$LOG"
      else
        echo "$STAMP  EMAIL NOT SENT — last lines:" >>"$LOG"
        echo "$MAIL" | tail -3 | sed 's/^/    /' >>"$LOG"
      fi
      # And to your own Telegram chat (TELEGRAM_CHAT_ID only). Skipped
      # quietly in the log if Telegram is not set up.
      if TG="$(.venv/bin/python src/monitor.py --telegram --from-digest 2>&1)" && echo "$TG" | grep -q "✅"; then
        echo "$STAMP  ok — newsletter sent to Telegram" >>"$LOG"
      else
        echo "$STAMP  TELEGRAM NOT SENT — last lines:" >>"$LOG"
        echo "$TG" | tail -2 | sed 's/^/    /' >>"$LOG"
      fi
    else
      echo "$STAMP  SUMMARIES FAILED — digest is fine, summaries not written. Last lines:" >>"$LOG"
      echo "$OLL" | tail -3 | sed 's/^/    /' >>"$LOG"
    fi
  else
    echo "$STAMP  SUMMARIES SKIPPED — Ollama is not running; open the Ollama app" >>"$LOG"
  fi
fi

exit $STATUS
