"""
Telegram digest sender for Industry Update Monitor.

Chosen 23 Sep 2026 over WhatsApp because the Telegram Bot API is free with no
trial to run out and no per-message charge. It sends only to TELEGRAM_CHAT_ID
— your own chat with your own bot — so it cannot be pointed at anyone else.

Without a token and chat ID it runs in preview mode and prints the messages.

Each week, since 1 Oct 2026: one short briefing, not the full newsletter
(that is the email). The top stories with what happened and the key fact, a
word of the week explained from the glossary, the rest counted by topic, and
a link to the public dashboard. Extras can be focused on an urgency or a
category. Never full article text.
"""

import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

try:
    from src.email_sender import _by_category, _icon, _term_name, bold_html, dashboard_url, item_terms, summary_points
except ImportError:  # pragma: no cover - only when src/ is itself the path
    from email_sender import _by_category, _icon, _term_name, bold_html, dashboard_url, item_terms, summary_points

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Telegram caps a message at 4096 characters.
MAX_BODY = 3900

FLAG_SEQUENCE = ("ACT", "KNOW", "NOTE")


# Plain words, the same as the newsletter and the dashboard.
FLAG_HEADINGS = {"ACT": "🔴 <b>Act now</b>", "KNOW": "🟠 <b>Worth knowing</b>", "NOTE": "🟢 <b>Background</b>"}
FLAG_WORDS = {"ACT": "act now", "KNOW": "worth knowing", "NOTE": "background"}


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


# Where the full week can be read. The public dashboard (item 18) unless
# DASHBOARD_URL names another address.
PUBLIC_DASHBOARD = "https://advice-monitor.vercel.app"

# The briefing names this many stories at most, Act now first; the rest are
# counted, with the Act now ones counted separately so none goes unnoticed.
TOP_STORIES = 5


def _rank(items: list) -> list:
    """Act now first, then Worth knowing, then Background; within each, a
    summarised story before one the model could not read, then the most
    confidently flagged."""
    order = {flag: n for n, flag in enumerate(FLAG_SEQUENCE)}
    return sorted(items, key=lambda i: (order.get(i.get("flag"), 3), not i.get("ai_summary"),
                                        -(i.get("confidence") or 0)))


def _story(n: int, item: dict) -> str:
    """One story: its headline, what happened, and the key fact."""
    title = html.escape(item.get("title", "Untitled"))
    link = item.get("link", "")
    head = f'<a href="{html.escape(link, quote=True)}">{title}</a>' if link else title
    emoji = FLAG_HEADINGS.get(item.get("flag"), FLAG_HEADINGS["NOTE"]).split(" ")[0]
    lines = [f"{n}. {emoji} {head}"]
    points = summary_points(item.get("ai_summary") or "")
    for label, point in zip(("What happened", "Key fact"), points[:2]):
        lines.append(f"    <i>{label}:</i> {bold_html(html.escape(point))}")
    if not points:
        lines.append("    <i>Not summarised: open the source.</i>")
    if item.get("source_name"):
        lines.append(f"    — {html.escape(item['source_name'])}")
    return "\n".join(lines)


def _word_of_the_week(items: list) -> list:
    """One glossary term from the stories named, explained. Which one turns
    with the week, so the same everyday term (ASIC) is not taught every time."""
    found: dict = {}
    for item in items:
        for entry in item_terms(item):
            found.setdefault(entry["term"], entry)
    if not found:
        return []
    terms = list(found.values())
    entry = terms[datetime.now().isocalendar()[1] % len(terms)]
    lines = ["", f"📖 <b>Word of the week: {html.escape(_term_name(entry))}</b>",
             html.escape(entry.get("means", ""))]
    if entry.get("matters"):
        lines.append(f"<i>Why it matters:</i> {html.escape(entry['matters'])}")
    return lines


def format_telegram_digest(items: list, flags: str | None = None,
                           topics: str | None = None, dashboard: str | None = None) -> tuple[str, list]:
    """A short briefing in one message, never split: the week's top stories
    (Act now first), each with what happened and its key fact; one
    jargon term explained; the rest of the week counted by topic; and a link
    to the dashboard, which carries everything else."""
    chosen = tailor(items, flags, topics)
    dashboard = dashboard or PUBLIC_DASHBOARD
    today = datetime.now().strftime("%-d %B %Y")
    focus = " · ".join(label for label in (flags, topics) if _wanted(label))
    lines = [f"📰 <b>Advice Monitor{': extra update' if focus else ''}</b> · {today}"]
    if focus:
        lines.append(f"<i>Only: {html.escape(focus)}</i>")
    if not chosen:
        lines += ["", "Nothing matched this week."]
        return "\n".join(lines), chosen
    counts = " · ".join(f"{sum(1 for i in chosen if i.get('flag') == f)} {FLAG_WORDS[f]}"
                        for f in FLAG_SEQUENCE if any(i.get("flag") == f for i in chosen))
    lines.append(f"{len(chosen)} stor{'y' if len(chosen) == 1 else 'ies'}: {counts}")
    if not focus and not any(i.get("flag") == "ACT" for i in chosen):
        lines.append("Nothing this week changes what you must do.")

    wanted = _rank(chosen)[:TOP_STORIES]
    footer = ("\n\n<i>Summaries are a quick guide. Read an Act now story at its source "
              "before acting on it.</i>")

    def tail(picked: list) -> list:
        rest = [i for i in chosen if i not in picked]
        out = _word_of_the_week(picked)
        if rest:
            by_topic = " · ".join(f"{_icon(topic)} {html.escape(topic)} {len(stories)}"
                                  for topic, stories in _by_category(rest))
            acts = sum(1 for i in rest if i.get("flag") == "ACT")
            out += ["", f"<b>Also this week ({len(rest)}):</b> {by_topic}"]
            if acts:
                out.append(f"🔴 {acts} more act now among them.")
        out += ["", f'👉 <a href="{html.escape(dashboard, quote=True)}">Read every story on the dashboard</a>']
        return out

    picked, stories = [], ["", "<b>The ones to read</b>"]
    for item in wanted:
        trial = stories + ["", _story(len(picked) + 1, item)]
        if len("\n".join(lines + trial + tail(picked + [item])) + footer) > MAX_BODY:
            break
        picked.append(item)
        stories = trial
    return "\n".join(lines + stories + tail(picked)) + footer, chosen


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


def send_telegram_digest(items: list, flags: str | None = None, topics: str | None = None) -> bool:
    """One short briefing, to your own chat only. The full newsletter is the
    email; every story is on the dashboard."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    dashboard = dashboard_url()
    message, chosen = format_telegram_digest(items, flags, topics, dashboard)

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
    print(f"✅ Briefing sent to Telegram ({len(chosen)} stories this week).")
    return True
