"""
WhatsApp digest sender for Industry Update Monitor.

Formats the collated digest as a readable newsletter and sends it through the
Twilio WhatsApp API — the same provider the web app already uses. No SDK is
required; Twilio's REST endpoint is a plain form POST.

Without credentials this runs in preview mode: it formats and prints the exact
messages that would be sent, so the formatting can be checked for free.

Safe: sends only the publisher's own headline, a short extract of the public
teaser, and the link. Never full article text.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

# Same tolerant import as src/monitor.py uses: this runs both as `python
# src/monitor.py` from the repo root and as an installed package.
try:
    from src.email_sender import summary_origin
except ImportError:  # pragma: no cover - only when src/ is itself the path
    from email_sender import summary_origin
from datetime import datetime

TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

# WhatsApp bodies are capped at 1600 characters. Leave room for the part
# counter appended to each chunk.
MAX_BODY = 1500

FLAG_HEADINGS = {
    "ACT": "🔴 *ACT — action required*",
    "KNOW": "🟠 *KNOW — worth knowing*",
    "NOTE": "🟢 *NOTE — background*",
}
FLAG_SEQUENCE = ("ACT", "KNOW", "NOTE")


def _twilio_config() -> dict:
    return {
        "sid": os.getenv("TWILIO_ACCOUNT_SID"),
        "token": os.getenv("TWILIO_AUTH_TOKEN"),
        "from_number": os.getenv("TWILIO_WHATSAPP_NUMBER"),
    }


def _escape(text: str) -> str:
    """Neutralise WhatsApp markup characters inside publisher text."""
    return (text or "").replace("*", "･").replace("_", " ").replace("~", "-").replace("`", "'")


def _item_block(index: int, item: dict) -> str:
    """One article, as a reader wants it: what, who said so, how sure, where."""
    lines = [f"*{index}. {_escape(item.get('title', 'Untitled'))}*"]

    meta = []
    if item.get("source_name"):
        meta.append(_escape(item["source_name"]))
    # Confidence is shown only where it means "trust this flag". On a NOTE it
    # means "confidently background", which reads as importance if shown.
    if item.get("confidence") is not None and item.get("flag") in {"ACT", "KNOW"}:
        meta.append(f"{item['confidence']:.0%} confidence")
    if meta:
        lines.append("_" + " · ".join(meta) + "_")

    # The summary you had written reached the dashboard and stopped there
    # (IMPROVEMENTS.md item 4). It is labelled with who wrote it, in italics,
    # so it never reads as the publisher's own words.
    written = _escape(item.get("ai_summary") or "").strip()
    if written:
        lines.append(f"_{_escape(summary_origin(item.get('ai_source')))}:_ {written}")

    summary = _escape(item.get("summary", "")).strip()
    if summary:
        lines.append(summary)

    if item.get("link"):
        lines.append(item["link"])

    return "\n".join(lines)


def format_whatsapp_digest(items: list, per_flag_limit: int = 6, week_of: str = None) -> list:
    """
    Render the digest as a list of WhatsApp-ready message bodies.

    Long digests are split on item boundaries so an article is never cut in
    half, and each part is numbered.
    """
    by_flag = {flag: [] for flag in FLAG_SEQUENCE}
    for item in items:
        flag = item.get("flag", "NOTE")
        if flag in by_flag:
            by_flag[flag].append(item)

    week_of = week_of or datetime.now().strftime("%-d %B %Y")
    total = sum(len(by_flag[flag]) for flag in FLAG_SEQUENCE)
    header = (
        "📰 *Industry Update Monitor*\n"
        f"_Week of {week_of} · {total} items_"
    )

    # Each block remembers its section, so a section that spills into the next
    # message can reintroduce its heading instead of starting on a bare item.
    blocks = [{"text": header, "heading": None}]
    for flag in FLAG_SEQUENCE:
        group = by_flag[flag][:per_flag_limit]
        if not group:
            continue
        heading = FLAG_HEADINGS[flag]
        if len(by_flag[flag]) > len(group):
            heading += f" _(top {len(group)} of {len(by_flag[flag])})_"
        blocks.append({"text": heading, "heading": heading, "is_heading": True})
        for position, item in enumerate(group, start=1):
            blocks.append({"text": _item_block(position, item), "heading": heading})

    if total == 0:
        blocks.append({"text": "_Nothing cleared the filters this week._", "heading": None})

    # Pack blocks into messages without splitting a block.
    messages, current, emitted_heading = [], "", None
    for block in blocks:
        text = block["text"]
        candidate = f"{current}\n\n{text}" if current else text
        if len(candidate) > MAX_BODY and current:
            messages.append(current)
            # Carry the section heading over to the new message.
            if block["heading"] and not block.get("is_heading"):
                current = f"{block['heading']} _(cont.)_\n\n{text}"
            else:
                current = text
        else:
            current = candidate
        if block.get("is_heading"):
            emitted_heading = block["heading"]
    if current:
        messages.append(current)

    if len(messages) > 1:
        messages = [
            f"{body}\n\n_(part {number} of {len(messages)})_"
            for number, body in enumerate(messages, start=1)
        ]
    return messages


# What Twilio's rejection codes mean in practice, and what to do about each.
# Sending is freeform, so on the sandbox the 24-hour window is the one that
# will bite: it closes, the weekly digest is refused, and the raw API response
# says "63016" and a URL. Reading the code back as the fix keeps a failed
# Monday send from looking like a broken tool.
TWILIO_ERRORS = {
    63016: ("The 24-hour window has closed. WhatsApp only allows a freeform message "
            "within 24 hours of the recipient messaging you.\n"
            "   Fix: send any message to the sandbox number from that phone, then re-run. "
            "On the sandbox you have to do this every 72 hours."),
    63015: ("The recipient has not joined the sandbox, or their join has lapsed.\n"
            "   Fix: from that phone, message 'join <your-two-words>' to the sandbox number."),
    63003: ("Twilio could not reach that recipient on WhatsApp.\n"
            "   Fix: check WHATSAPP_TO is the number in full international form, e.g. +61412345678, "
            "and that it has joined the sandbox."),
    63007: ("No WhatsApp sender exists for TWILIO_WHATSAPP_NUMBER.\n"
            "   Fix: use the sandbox number from the Twilio console exactly, e.g. +14155238886."),
    21910: ("The From and To numbers are not both WhatsApp.\n"
            "   Fix: check TWILIO_WHATSAPP_NUMBER is your sandbox number, not an SMS number."),
    20003: ("Twilio refused the credentials.\n"
            "   Fix: re-copy TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN from the console. "
            "The SID starts with AC."),
}


def explain_twilio_error(status: int, body: str) -> str:
    """
    Turn a Twilio rejection into something that says what to do next.

    Falls back to Twilio's own message when the code is not one we know, and
    to the raw body when the response is not the JSON we expect — never
    swallowing a failure just because it is unfamiliar.
    """
    try:
        detail = json.loads(body)
    except (ValueError, TypeError):
        return f"Twilio rejected it ({status}): {body[:300]}"

    code = detail.get("code")
    known = TWILIO_ERRORS.get(code)
    if known:
        return f"{known}\n   (Twilio code {code}.)"
    return f"Twilio rejected it ({status}, code {code}): {detail.get('message', body[:300])}"


def _post(sid: str, token: str, payload: dict, timeout: int = 20) -> None:
    request = urllib.request.Request(
        TWILIO_API.format(sid=urllib.parse.quote(sid)),
        data=urllib.parse.urlencode(payload).encode(),
        headers={
            "Authorization": "Basic "
            + base64.b64encode(f"{sid}:{token}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout):
        return


def send_whatsapp_digest(items: list, to_number: str = None, per_flag_limit: int = 6) -> bool:
    """
    Send the digest to WhatsApp. Returns True when every part was accepted.

    With no Twilio credentials configured this prints the formatted messages
    instead of sending, so the newsletter can be proof-read at no cost.
    """
    cfg = _twilio_config()
    to_number = to_number or os.getenv("WHATSAPP_TO")
    messages = format_whatsapp_digest(items, per_flag_limit=per_flag_limit)

    if not to_number:
        print("❌ No WhatsApp recipient. Set WHATSAPP_TO in .env or pass --whatsapp-to.")
        return False

    if not all((cfg["sid"], cfg["token"], cfg["from_number"])):
        print("📱 WhatsApp preview (no Twilio credentials configured — nothing sent).")
        print("   Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_NUMBER to send.\n")
        for number, body in enumerate(messages, start=1):
            print(f"--- message {number}/{len(messages)} ({len(body)} chars) ---")
            print(body)
            print()
        return False

    for number, body in enumerate(messages, start=1):
        payload = {
            "From": f"whatsapp:{cfg['from_number']}",
            "To": f"whatsapp:{to_number}",
            "Body": body,
        }
        try:
            _post(cfg["sid"], cfg["token"], payload)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            print(f"❌ WhatsApp part {number} not sent. {explain_twilio_error(error.code, body)}")
            return False
        except Exception as error:
            print(f"❌ WhatsApp part {number} failed: {type(error).__name__}: {error}")
            return False

    print(f"✅ Digest sent to WhatsApp {to_number} in {len(messages)} message(s).")
    return True
