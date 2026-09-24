"""Keep a copy of this week's digest for the dashboard's Past weeks page.

Writes web/lib/archive/<Monday>.json, named for the Monday (Sydney time) of
the week the digest was made for, so re-running within a week replaces that
week's copy rather than adding another. The article text the local model
read (brief_text) is left out: the archive is headlines, dot points and
links only, the same as the public dashboard shows.

    python scripts/archive_week.py                 # archive web/lib/digest.json
    python scripts/archive_week.py some-digest.json
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
ARCHIVE = REPO / "web" / "lib" / "archive"


def week_of(generated_at: str) -> str:
    # The run is on Sunday evening, for the week ahead, so a Sunday belongs to
    # the Monday after it rather than the one before.
    day = datetime.fromisoformat(generated_at).astimezone(ZoneInfo("Australia/Sydney")).date() + timedelta(days=1)
    return (day - timedelta(days=day.weekday())).isoformat()


def archive(raw: dict) -> Path:
    for item in raw.get("items", []):
        item.pop("brief_text", None)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    out = ARCHIVE / f"{week_of(raw['generated_at'])}.json"
    out.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "web" / "lib" / "digest.json"
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not raw.get("items"):
        sys.exit(f"❌ {source} has no stories; nothing archived")
    print(f"✅ archived {len(raw['items'])} stories to {archive(raw).relative_to(REPO)}")
