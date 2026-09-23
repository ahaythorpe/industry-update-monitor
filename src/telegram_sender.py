"""
Telegram digest sender for Industry Update Monitor.

Chosen 23 Sep 2026 over WhatsApp because the Telegram Bot API is free with no
trial to run out and no per-message charge. It sends only to TELEGRAM_CHAT_ID
— your own chat with your own bot — so it cannot be pointed at anyone else.

Without a token and chat ID it runs in preview mode and prints the messages.

Each week: one message with the headlines and summaries, and the full
newsletter (the same one the email carries) attached as a file. Extras can be
focused on an urgency or a category. Never full article text.
"""

import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

try:
    from src.email_sender import _build_html_digest
except ImportError:  # pragma: no cover - only when src/ is itself the path
    from email_sender import _build_html_digest

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Telegram caps a message at 4096 characters.
MAX_BODY = 3900

FLAG_SEQUENCE = ("ACT", "KNOW", "NOTE")


FLAG_HEADINGS = {"ACT": "🔴 <b>ACT — act on these</b>", "KNOW": "🟠 <b>KNOW — worth knowing</b>",
                 "NOTE": "🟢 <b>NOTE — background</b>"}


def _wanted(setting: str | None) -> set[str]:
    """A comma list from .env or the command line; empty means everything."""
    return {part.strip().lower() for part in (setting or "").split(",") if part.strip()}


def tailor(items: list, flags: str | None = None, topics: str | None = None) -> list:
    """Keep only the urgencies and categories asked for. Nothing set means the
    whole digest — the weekly newsletter; set, it is an extra, focused send."""
    want_flags, want_topics = _wanted(flags), _wanted(topics)
    return [
        item for item in items
        if (not want_flags or (item.get("flag") or "").lower() in want_flags)
        and (not want_topics or (item.get("topic") or "General").lower() in want_topics)
    ]


def _line(item: dict) -> str:
    title = html.escape(item.get("title", "Untitled"))
    link = item.get("link", "")
    head = f'<a href="{html.escape(link, quote=True)}">{title}</a>' if link else title
    summary = (item.get("ai_summary") or "").strip()
    return f"• {head}" + (f" — {html.escape(summary)}" if summary else "")


def format_telegram_digest(items: list, flags: str | None = None,
                           topics: str | None = None) -> tuple[str, list]:
    """One message: the headlines, ACT first, with each summary in a line.
    Whatever does not fit Telegram's cap is counted and left to the attached
    newsletter, never split into a second message."""
    chosen = tailor(items, flags, topics)
    today = datetime.now().strftime("%-d %B %Y")
    focus = " · ".join(label for label in (flags, topics) if _wanted(label))
    title = "extra update" if focus else "weekly newsletter"
    counts = " · ".join(f"{sum(1 for i in chosen if i.get('flag') == f)} {f}"
                        for f in FLAG_SEQUENCE if any(i.get("flag") == f for i in chosen))
    lines = [f"📰 <b>Advice Monitor — {title}</b>", today]
    if focus:
        lines.append(f"<i>Only: {html.escape(focus)}</i>")
    lines.append("")
    if not chosen:
        lines.append("Nothing matched this week.")
        return "\n".join(lines), chosen
    lines.append(f"{len(chosen)} stor{'y' if len(chosen) == 1 else 'ies'}: {counts}")

    footer = "\n<i>Summaries by a local model are triage — read an ACT story at its source.</i>"
    left_out = 0
    for flag in FLAG_SEQUENCE:
        flagged = [i for i in chosen if i.get("flag") == flag]
        if not flagged:
            continue
        section = ["", FLAG_HEADINGS[flag]]
        for item in flagged:
            candidate = "\n".join(lines + section + [_line(item)]) + footer
            if len(candidate) > MAX_BODY - 120:
                left_out += 1
            else:
                section.append(_line(item))
        if len(section) > 2:
            lines += section
    if left_out:
        lines += ["", f"<b>+ {left_out} more in the attached newsletter 📎</b>"]
    else:
        lines += ["", "📎 The full newsletter is attached."]
    return "\n".join(lines) + footer, chosen


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


def _send_document(token: str, chat_id: str, filename: str, content: bytes, caption: str) -> dict:
    """sendDocument needs a multipart upload; built by hand to stay dependency-free."""
    boundary = "----advice-monitor-" + datetime.now().strftime("%H%M%S%f")
    parts = []
    for name, value in (("chat_id", chat_id), ("caption", caption), ("parse_mode", "HTML")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\n'
        f"Content-Type: text/html; charset=utf-8\r\n\r\n".encode() + content + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(
        TELEGRAM_API.format(token=token, method="sendDocument"), data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            return json.loads(error.read())
        except ValueError:
            return {"ok": False, "description": f"HTTP {error.code}"}


def newsletter_file(items: list) -> bytes:
    """The same newsletter the email carries, as a file that opens on a phone."""
    grouped = {flag: [i for i in items if i.get("flag") == flag] for flag in FLAG_SEQUENCE}
    return _build_html_digest(grouped).encode("utf-8")


def send_telegram_digest(items: list, flags: str | None = None, topics: str | None = None) -> bool:
    """One message and one attachment, to your own chat only."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    message, chosen = format_telegram_digest(items, flags, topics)

    if not token or not chat_id:
        print("ℹ️  Telegram is not set up (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env). "
              "Preview of the message:\n")
        print(message)
        return False

    reply = _call(token, "sendMessage", {
        "chat_id": chat_id, "text": message, "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    })
    if not reply.get("ok"):
        print(f"❌ Telegram refused the message: {reply.get('description')}")
        return False
    if chosen:
        name = f"advice-monitor-{datetime.now():%Y-%m-%d}.html"
        reply = _send_document(token, chat_id, name, newsletter_file(chosen),
                               "The full newsletter — tap to open.")
        if not reply.get("ok"):
            print(f"❌ The message went, but Telegram refused the newsletter file: {reply.get('description')}")
            return False
    print(f"✅ Newsletter sent to Telegram ({len(chosen)} stories).")
    return True
