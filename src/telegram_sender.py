"""
Telegram digest sender for Industry Update Monitor.

Chosen 23 Sep 2026 over WhatsApp because the Telegram Bot API is free with no
trial to run out and no per-message charge. It sends only to TELEGRAM_CHAT_ID
— your own chat with your own bot — so it cannot be pointed at anyone else.

Without a token and chat ID it runs in preview mode and prints the messages.

Safe: the headline, the summary (labelled with who wrote it) or the public
teaser, and the link. Never full article text.
"""

import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

try:
    from src.email_sender import summary_origin
except ImportError:  # pragma: no cover - only when src/ is itself the path
    from email_sender import summary_origin

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Telegram caps a message at 4096 characters; leave room for the part counter.
MAX_BODY = 3900

FLAG_HEADINGS = {
    "ACT": "🔴 <b>ACT — act on these</b>",
    "KNOW": "🟠 <b>KNOW — worth knowing</b>",
    "NOTE": "🟢 <b>NOTE — background</b>",
}
FLAG_SEQUENCE = ("ACT", "KNOW", "NOTE")


def _item_block(index: int, item: dict) -> str:
    """One article: headline, who published it, the summary, the link."""
    title = html.escape(item.get("title", "Untitled"))
    link = item.get("link", "")
    lines = [f'<b>{index}. <a href="{html.escape(link, quote=True)}">{title}</a></b>' if link
             else f"<b>{index}. {title}</b>"]
    if item.get("source_name"):
        lines.append(f"<i>{html.escape(item['source_name'])}</i>")
    if item.get("ai_summary"):
        lines.append(html.escape(item["ai_summary"]))
        lines.append(f"<i>— {html.escape(summary_origin(item.get('ai_source')))}</i>")
    elif item.get("summary"):
        teaser = item["summary"]
        lines.append(html.escape(teaser[:280] + ("…" if len(teaser) > 280 else "")))
    return "\n".join(lines)


def format_telegram_digest(items: list, per_flag_limit: int | None = None) -> list[str]:
    """The digest as Telegram messages, split only between articles."""
    today = datetime.now().strftime("%-d %B %Y")
    counts = {flag: sum(1 for i in items if i.get("flag") == flag) for flag in FLAG_SEQUENCE}
    header = (f"📰 <b>Advice Monitor — {today}</b>\n"
              f"{counts['ACT']} ACT · {counts['KNOW']} KNOW · {counts['NOTE']} NOTE")

    blocks = [header]
    for flag in FLAG_SEQUENCE:
        flagged = [i for i in items if i.get("flag") == flag]
        if per_flag_limit:
            flagged = flagged[:per_flag_limit]
        if not flagged:
            continue
        blocks.append(FLAG_HEADINGS[flag])
        blocks.extend(_item_block(n, item) for n, item in enumerate(flagged, 1))
    blocks.append("<i>Summaries are triage. Read an ACT item at its source before acting on it.</i>")

    messages, current = [], ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > MAX_BODY and current:
            messages.append(current)
            current = block
        else:
            current = candidate
    if current:
        messages.append(current)
    if len(messages) > 1:
        messages = [f"{m}\n\n<i>({n} of {len(messages)})</i>" for n, m in enumerate(messages, 1)]
    return messages


def _call(token: str, method: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    request = urllib.request.Request(TELEGRAM_API.format(token=token, method=method), data=data)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            return json.loads(error.read())
        except ValueError:
            return {"ok": False, "description": f"HTTP {error.code}"}


def find_chat_id(token: str) -> str | None:
    """The chat ID of whoever last messaged the bot — you, after pressing Start."""
    reply = _call(token, "getUpdates", {})
    for update in reversed(reply.get("result", [])):
        chat = (update.get("message") or {}).get("chat")
        if chat and chat.get("type") == "private":
            return str(chat["id"])
    return None


def send_telegram_digest(items: list, per_flag_limit: int | None = None) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    messages = format_telegram_digest(items, per_flag_limit)

    if not token or not chat_id:
        print("ℹ️  Telegram is not set up (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env). "
              "Preview of what would be sent:\n")
        for message in messages:
            print(message, "\n" + "─" * 40)
        return False

    for n, message in enumerate(messages, 1):
        reply = _call(token, "sendMessage", {
            "chat_id": chat_id, "text": message, "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        })
        if not reply.get("ok"):
            print(f"❌ Telegram refused message {n} of {len(messages)}: {reply.get('description')}")
            return False
    print(f"✅ Digest sent to Telegram in {len(messages)} message(s).")
    return True
