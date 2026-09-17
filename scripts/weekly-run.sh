#!/bin/bash
# Weekly unattended run, started by launchd. See IMPROVEMENTS.md item 6.
#
# Deliberately does NOT pass --email, --whatsapp or --gmail. The default is
# "write the digest, send nothing": a scheduled job must never be able to send
# on your behalf while you are not looking. Delivery stays something you
# trigger.

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

exit $STATUS
