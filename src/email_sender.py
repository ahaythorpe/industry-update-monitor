"""
Email digest sender for Industry Update Monitor.

Sends collated, prioritised items as an HTML email digest via Gmail SMTP.
Requires a Gmail app password (not the regular Gmail password), kept in the
macOS Keychain under advice-monitor-email, or in .env.

Safe: never includes full article text, only publisher teasers and links.
"""

import html
import os
import re
import smtplib
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# The macOS Keychain entry the password can live in instead of .env, so it is
# never written to a file. Stored once with:
#   security add-generic-password -a advice-monitor -s advice-monitor-email -w
KEYCHAIN_SERVICE = "advice-monitor-email"


def _keychain_password():
    """The email password from the macOS Keychain, or None if it is not there."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def _smtp_config() -> dict:
    """Resolve the SMTP configuration, preferring provider variables when present."""
    smtp_host = os.getenv("SMTP_HOST")
    if smtp_host:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER") or os.getenv("EMAIL_ADDRESS")
        smtp_password = (os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
                         or _keychain_password())
        from_email = os.getenv("SMTP_FROM_EMAIL") or os.getenv("EMAIL_ADDRESS") or smtp_user
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
        return {
            "host": smtp_host,
            "port": smtp_port,
            "user": smtp_user,
            "password": smtp_password,
            "from_email": from_email,
            "use_tls": use_tls,
        }

    return {
        "host": "smtp.gmail.com",
        "port": 465,
        "user": os.getenv("EMAIL_ADDRESS"),
        "password": os.getenv("EMAIL_PASSWORD") or _keychain_password(),
        "from_email": os.getenv("EMAIL_ADDRESS"),
        "use_tls": False,
    }


def send_digest_email(
    items: list,
    to_email: str,
    subject: str = "Advice Monitor: this week in Australian advice",
) -> bool:
    """
    Send a digest of items as an HTML email via SMTP.

    Supports Gmail or a generic SMTP provider such as Resend, Mailgun, or SendGrid.
    """
    cfg = _smtp_config()
    from_email = cfg["from_email"]
    app_password = cfg["password"]

    if not from_email or not app_password:
        provider = "SMTP" if os.getenv("SMTP_HOST") else "Gmail"
        print(f"❌ {provider} email not configured. Set the SMTP_* values or EMAIL_ADDRESS/EMAIL_PASSWORD in .env")
        return False

    try:
        # Group items by flag
        by_flag = {"ACT": [], "KNOW": [], "NOTE": []}
        for item in items:
            flag = item.get("flag", "NOTE")
            if flag in by_flag:
                by_flag[flag].append(item)

        # Build HTML body: the short alert when the dashboard is online,
        # otherwise the full newsletter.
        body_html = build_email(by_flag)

        # Create email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        # Attach HTML part
        msg.attach(MIMEText(body_html, "html"))

        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"]) as server:
                server.login(cfg["user"], app_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                if cfg["use_tls"]:
                    server.starttls()
                server.login(cfg["user"], app_password)
                server.send_message(msg)

        print(f"✅ Digest emailed to {to_email} via {cfg['host']}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP authentication failed. Check your provider credentials in .env")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ Email send failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


# Newsletter palette. Inline styles and tables throughout, because Gmail and
# Outlook strip <style> blocks and ignore most modern CSS.
_INK = "#0f172a"
_MUTED = "#64748b"
_RULE = "#e2e8f0"
_ACCENT = "#0369a1"
_FLAGS = {
    "ACT": ("act", "Act on these", "Changes what an adviser must do. Read each one at its source.", "#b91c1c", "#fef2f2"),
    "KNOW": ("know", "Worth knowing", "Useful context on policy, people and the market.", "#c2410c", "#fff7ed"),
    "NOTE": ("note", "In the background", "Data and reference material.", "#15803d", "#f0fdf4"),
}


# What a reader sees instead of ACT / KNOW / NOTE: plain words and a colour.
_LABELS = {"ACT": ("🔴", "Act now"), "KNOW": ("🟠", "Worth knowing"), "NOTE": ("🟢", "Background")}

# An icon per category, so a section is recognised before it is read. Emoji,
# because Gmail strips SVG and would need hosted images.
_ICONS = {
    "Regulation": "⚖️", "Compliance": "✅", "Super & tax": "💰", "Insurance": "🛡️",
    "Key personnel movements": "👥", "Business": "🏢", "Markets & investing": "📈",
    "Fees & pricing": "🏷️", "Practice & technology": "💻", "General": "📰",
}


def _icon(topic: str) -> str:
    return _ICONS.get(topic, "📌")


def _pill(flag: str, count: int | None = None) -> str:
    """A coloured label in plain words, optionally with a count."""
    _, _, _, colour, bg = _FLAGS.get(flag, _FLAGS["NOTE"])
    emoji, label = _LABELS.get(flag, _LABELS["NOTE"])
    text = f"{count} {label.lower()}" if count is not None else label
    return (f'<span style="display:inline-block;background:{bg};color:{colour};border-radius:999px;'
            f'padding:3px 10px;font-size:12px;font-weight:700;white-space:nowrap;">{emoji} {html.escape(text)}</span>')


def _bar(stories: list) -> str:
    """A stacked bar of the week's urgencies, as table cells so Gmail keeps it."""
    total = len(stories) or 1
    cells = "".join(
        f'<td width="{max(1, round(100 * n / total))}%" style="background:{_FLAGS[flag][3]};height:8px;'
        f'font-size:0;line-height:0;">&nbsp;</td>'
        for flag in _FLAGS if (n := sum(1 for i in stories if i.get("flag") == flag))
    )
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-radius:4px;overflow:hidden;"><tr>{cells}</tr></table>')


_glossary_cache: list | None = None


def _glossary() -> list:
    """The hand-written glossary in data/glossary.json, read once."""
    global _glossary_cache
    if _glossary_cache is None:
        try:
            from src.monitor import load_glossary
        except ImportError:  # pragma: no cover - only when src/ is itself the path
            from monitor import load_glossary
        _glossary_cache = load_glossary()
    return _glossary_cache


def item_terms(item: dict) -> list:
    """Glossary terms a story uses, in its headline or its summary."""
    try:
        from src.monitor import terms_in
    except ImportError:  # pragma: no cover
        from monitor import terms_in
    text = f'{item.get("title") or ""} {item.get("ai_summary") or item.get("summary") or ""}'
    return terms_in(text, _glossary())


def _term_name(entry: dict) -> str:
    """"CSLR (Compensation Scheme of Last Resort)" for an acronym, else the term."""
    also = entry.get("also") or []
    if entry["term"].isupper() and also:
        return f'{entry["term"]} ({also[0]})'
    return entry["term"]


def _terms_box(item: dict) -> str:
    terms = item_terms(item)
    if not terms:
        return ""
    lines = "".join(
        f'<div style="margin:2px 0;"><b>{html.escape(_term_name(t))}</b>: {html.escape(t.get("means", ""))}</div>'
        for t in terms
    )
    return (f'<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:8px 12px;'
            f'margin-top:8px;font-size:14px;line-height:1.45;color:#0c4a6e;">📖 {lines}</div>')


def _jargon_buster(items: list) -> str:
    """Every term used this week, once, with why it matters, folded away."""
    seen: dict = {}
    for item in items:
        for entry in item_terms(item):
            seen.setdefault(entry["term"], entry)
    if not seen:
        return ""
    rows = "".join(
        f'<div style="padding:8px 0;border-bottom:1px solid {_RULE};font-size:15px;line-height:1.5;">'
        f'<b>{html.escape(_term_name(t))}</b>: {html.escape(t.get("means", ""))}'
        + (f' <span style="color:{_MUTED};">Why it matters: {html.escape(t["matters"])}</span>' if t.get("matters") else "")
        + '</div>'
        for t in sorted(seen.values(), key=lambda t: t["term"].lower())
    )
    return (f'<tr><td style="padding:22px 32px 0;"><details style="border-top:1px solid {_RULE};padding-top:14px;">'
            f'<summary><span class="chev" style="color:{_MUTED};">▸</span> '
            f'<span style="font-size:21px;font-weight:700;">📖 Jargon buster</span> '
            f'<span style="font-size:14px;color:{_MUTED};">· {len(seen)} terms this week</span></summary>'
            f'<div style="padding-top:6px;">{rows}</div></details></td></tr>')


def summary_points(summary: str) -> list[str]:
    """A summary's dot points. The local model writes them on one line, each
    starting "• "; an older one-sentence summary is a single point."""
    points = [p.strip() for p in re.split(r"\s*•\s*", summary or "") if p.strip()]
    return points or ([summary.strip()] if (summary or "").strip() else [])


def bold_html(escaped: str) -> str:
    """**key fact** → <b>key fact</b>, on text that is already HTML-escaped."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def _day(item: dict) -> str:
    raw = (item.get("created_at") or item.get("published") or "")[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%-d %b")
    except ValueError:
        return ""


def dashboard_url() -> str | None:
    """Where the dashboard is online (DASHBOARD_URL in .env), or None."""
    return (os.getenv("DASHBOARD_URL") or "").strip() or None


def build_email(by_flag: dict) -> str:
    """What the weekly email carries: a short alert pointing at the dashboard
    once it is online, the full newsletter until then."""
    url = dashboard_url()
    return _build_alert_email(by_flag, url) if url else _build_html_digest(by_flag)


def _build_alert_email(by_flag: dict, url: str) -> str:
    """The one-minute email: Act now stories with their first point, the week
    by topic in one line, and a button to the dashboard for everything else."""
    today = datetime.now().strftime("%-d %B %Y")
    items = [i for flag in _FLAGS for i in by_flag.get(flag, [])]
    acts = by_flag.get("ACT", [])
    out = _opening(by_flag, today, len(items), len(acts))

    rows = ""
    for item in acts:
        title = html.escape(item.get("title", "Untitled"))
        link = item.get("link", "")
        head = (f'<a href="{html.escape(link, quote=True)}" target="_blank" style="color:{_INK};'
                f'text-decoration:none;">{title}</a>') if link else title
        points = summary_points(item.get("ai_summary") or "")
        point = (f'<div style="font-size:15px;color:#334155;line-height:1.5;margin-top:3px;">'
                 f'{bold_html(html.escape(points[0]))}</div>') if points else ""
        meta = " · ".join(p for p in (html.escape(item.get("source_name", "")), _day(item)) if p)
        rows += (f'<div style="padding:10px 0;border-bottom:1px solid #fecaca;">'
                 f'<div style="font-size:17px;font-weight:700;line-height:1.4;">{head}</div>{point}'
                 f'<div style="font-size:13px;color:{_MUTED};margin-top:3px;">{meta}</div></div>')
    if rows:
        out.append(f'<tr><td style="padding:22px 32px 4px;"><div style="background:#fef2f2;border-radius:10px;'
                   f'padding:16px 20px;"><div style="font-size:19px;font-weight:700;color:{_FLAGS["ACT"][3]};">'
                   f'🔴 Act now</div>{rows}</div></td></tr>')

    topics = " · ".join(f"{_icon(topic)} {html.escape(topic)} {len(stories)}"
                        for topic, stories in _by_category(items))
    out.append(f'<tr><td style="padding:20px 32px 4px;font-size:15px;line-height:1.7;">'
               f'<div style="font-size:17px;font-weight:700;margin-bottom:4px;">By topic</div>{topics}</td></tr>')
    out.append(f'<tr><td align="center" style="padding:24px 32px 8px;">'
               f'<a href="{html.escape(url, quote=True)}" target="_blank" style="display:inline-block;padding:14px 26px;'
               f'border-radius:8px;background:{_ACCENT};color:#ffffff;font-size:17px;font-weight:700;'
               f'text-decoration:none;">Open this week on the dashboard →</a></td></tr>')
    out.append(_footer())
    return "".join(out)


def _footer() -> str:
    return (f'<tr><td style="padding:26px 32px 30px;border-top:1px solid {_RULE};font-size:14px;line-height:1.6;color:{_MUTED};">'
            'Summaries are a quick guide, not advice. Each says who wrote it, and an 🔴 Act now story is read '
            'at its source before anyone acts on it. Every story comes from a free public feed. Nothing here is '
            'behind a paywall.'
            '</td></tr>'
            '</table></td></tr></table></body></html>')


def _build_html_digest(by_flag: dict, interactive: bool = False) -> str:
    """The weekly newsletter, organised by category.

    The Act now headlines, an overview by category, then each category as a
    drop-down with every story's dot points and its terms explained, so it
    reads without opening a single article. Then the stories to read by hand,
    a jargon buster and the sources. `interactive=True` is the same page for
    a browser (the file Telegram carries), with the quieter categories folded.
    """
    today = datetime.now().strftime("%-d %B %Y")
    items = [i for flag in _FLAGS for i in by_flag.get(flag, [])]
    total = len(items)
    act = len(by_flag.get("ACT", []))

    out = _opening(by_flag, today, total, act)

    categories = _by_category(items)
    if by_flag.get("ACT"):
        out.append(_act_list(by_flag["ACT"]))
    out.append(_category_overview(categories))

    for topic, stories in categories:
        counts = _counts(stories)
        heading = (f'<span style="font-size:23px;font-weight:700;">{_icon(topic)} {html.escape(topic)}</span> '
                   f'<span style="white-space:nowrap;">{counts}</span>')
        # Every story carries its dot points, so the newsletter reads on its
        # own; the article is there for when you want more, not a chore.
        body = "".join(_item_html(i, _FLAGS.get(i.get("flag"), _FLAGS["NOTE"])[0]) for i in stories)
        anchor = _anchor(topic)
        # Every category is a drop-down. The email opens them all, so a mail
        # app that ignores drop-downs (Gmail) loses nothing; the Telegram file
        # opens only those with an Act now story, for a short first screen.
        opened = " open" if not interactive or any(i.get("flag") == "ACT" for i in stories) else ""
        out.append(
            f'<tr><td style="padding:14px 32px 0;"><details id="{anchor}"{opened} style="border-top:1px solid {_RULE};padding-top:14px;">'
            f'<summary><span class="chev" style="color:{_MUTED};">▸</span> {heading}</summary>'
            f'<div style="padding-top:6px;">{body}</div></details></td></tr>'
        )

    out.append(_read_yourself(items))
    out.append(_jargon_buster(items))
    # Sources always fold, under each publisher: a mail app that ignores
    # drop-downs (Gmail) simply shows the list open, so nothing is lost.
    out.append(_sources_html(items, interactive=True))
    out.append(_footer())
    return "".join(out)


def _opening(by_flag: dict, today: str, total: int, act: int) -> list:
    """The page head, the masthead and the three urgency tiles."""
    out = [
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Advice Monitor</title>'
        '<style>summary{cursor:pointer;list-style:none}summary::-webkit-details-marker{display:none}'
        'details[open] .chev{transform:rotate(90deg)}.chev{display:inline-block;transition:transform .15s}</style>'
        '</head>',
        f'<body style="margin:0;padding:0;background:#f1f5f9;font-family:Helvetica,Arial,sans-serif;color:{_INK};">',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;">'
        '<tr><td align="center" style="padding:24px 10px;">',
        '<table role="presentation" width="640" cellpadding="0" cellspacing="0" '
        'style="width:100%;max-width:640px;background:#ffffff;border-radius:12px;overflow:hidden;">',
        f'<tr><td style="background:{_INK};padding:30px 32px;">'
        '<div style="font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#7dd3fc;font-weight:700;">Advice Monitor</div>'
        '<div style="font-size:28px;line-height:1.25;font-weight:700;color:#ffffff;margin-top:8px;">This week in Australian advice</div>'
        f'<div style="font-size:16px;color:#cbd5e1;margin-top:8px;">{today} · {total} stories from the public trade press</div>'
        '</td></tr>',
    ]

    tiles = "".join(
        f'<td width="33%" style="padding:0 5px;"><div style="background:{bg};border-radius:10px;padding:14px;text-align:center;">'
        f'<div style="font-size:28px;font-weight:700;color:{colour};">{len(by_flag.get(flag, []))}</div>'
        f'<div style="font-size:14px;color:{colour};font-weight:700;">{_LABELS[flag][0]} {_LABELS[flag][1]}</div></div></td>'
        for flag, (_, _, _, colour, bg) in _FLAGS.items()
    )
    lead = (f"Start with the <b>{act}</b> stor{'ies' if act != 1 else 'y'} marked 🔴 Act now. They change what you must do."
            if act else "Nothing this week changes what you must do.")
    out.append(
        '<tr><td style="padding:26px 27px 6px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{tiles}</tr></table>'
        f'<p style="font-size:17px;line-height:1.55;margin:18px 5px 0;">{lead}</p>'
        '</td></tr>'
    )
    return out


def _by_category(items: list) -> list:
    """Categories with ACT stories first, then by size; ACT first inside each."""
    groups: dict = {}
    for item in items:
        groups.setdefault(item.get("topic") or "General", []).append(item)
    rank = {flag: n for n, flag in enumerate(_FLAGS)}
    for stories in groups.values():
        stories.sort(key=lambda i: rank.get(i.get("flag"), 9))
    return sorted(groups.items(), key=lambda kv: (
        -sum(1 for i in kv[1] if i.get("flag") == "ACT"), -len(kv[1]), kv[0] == "General", kv[0]))


def _counts(stories: list) -> str:
    return " ".join(_pill(flag, n) for flag in _FLAGS
                    if (n := sum(1 for i in stories if i.get("flag") == flag)))


def _anchor(topic: str) -> str:
    return "cat-" + re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")


def _category_overview(categories: list) -> str:
    # Each row jumps to its category. A browser (the Telegram file) follows
    # it; a mail app that ignores in-page links just shows the table.
    rows = "".join(
        f'<tr><td style="padding:9px 0;border-bottom:1px solid {_RULE};">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="font-size:16px;"><a href="#{_anchor(topic)}" style="color:{_INK};text-decoration:none;">'
        f'{_icon(topic)} {html.escape(topic)} ›</a></td>'
        f'<td align="right" style="font-size:14px;color:{_MUTED};white-space:nowrap;">{len(stories)} '
        f'stor{"ies" if len(stories) != 1 else "y"}</td></tr>'
        f'<tr><td colspan="2" style="padding-top:6px;">{_bar(stories)}</td></tr></table></td></tr>'
        for topic, stories in categories
    )
    legend = " ".join(_pill(flag) for flag in _FLAGS)
    return (f'<tr><td style="padding:24px 32px 4px;"><div style="font-size:19px;font-weight:700;margin-bottom:4px;">'
            f'This week by category</div><div style="margin-bottom:6px;">{legend}</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>')

def unread_reason(item: dict) -> str | None:
    """Why the model could not summarise a story properly, or None if it could."""
    summary = (item.get("ai_summary") or "").lower()
    if item.get("body_source") == "feed_summary":
        return "The publisher only shares a teaser, so the article could not be read."
    if "thin" in summary and "open" in summary:
        return "Too little text to summarise."
    if not summary.strip():
        return "Not summarised yet."
    return None


def _read_yourself(items: list) -> str:
    """The stories the model could not read, listed apart so a person can."""
    missed = [(i, reason) for i in items if (reason := unread_reason(i))]
    if not missed:
        return ""
    rows = "".join(
        f'<div style="padding:8px 0;border-bottom:1px solid {_RULE};">'
        + (f'<a href="{html.escape(i["link"], quote=True)}" target="_blank" style="font-size:16px;font-weight:700;'
           f'color:{_INK};text-decoration:none;">{html.escape(i.get("title", "Untitled"))} →</a>'
           if i.get("link") else f'<b>{html.escape(i.get("title", "Untitled"))}</b>')
        + f'<div style="font-size:13px;color:{_MUTED};margin-top:2px;">'
          f'{_LABELS.get(i.get("flag"), ("", ""))[1]} · {html.escape(i.get("source_name", ""))} · {html.escape(reason)}</div></div>'
        for i, reason in missed
    )
    return (f'<tr><td style="padding:18px 32px 4px;"><div style="background:#f8fafc;border:1px solid {_RULE};'
            f'border-radius:10px;padding:16px 20px;">'
            f'<div style="font-size:19px;font-weight:700;">👀 Read these yourself ({len(missed)})</div>'
            f'<div style="font-size:14px;color:{_MUTED};margin:2px 0 4px;">The summariser could not read these, '
            f'so they have no dot points. Tap to open.</div>{rows}</div></td></tr>')


def _act_list(stories: list) -> str:
    colour = _FLAGS["ACT"][3]
    rows = "".join(
        f'<div style="font-size:16px;line-height:1.45;padding:6px 0;border-bottom:1px solid #fecaca;">'
        + (f'<a href="{html.escape(i["link"], quote=True)}" target="_blank" style="color:{_INK};text-decoration:none;">'
           f'{html.escape(i.get("title", "Untitled"))}</a>' if i.get("link") else html.escape(i.get("title", "Untitled")))
        + '</div>'
        for i in stories
    )
    return (f'<tr><td style="padding:22px 32px 4px;"><div style="background:#fef2f2;border-radius:10px;padding:16px 20px;">'
            f'<div style="font-size:19px;font-weight:700;color:{colour};margin-bottom:4px;">🔴 Act on these first</div>'
            f'{rows}</div></td></tr>')


def _sources_html(items: list, interactive: bool = False) -> str:
    """Every publisher this week, each of its articles listed with its own link."""
    by_source: dict = {}
    for item in items:
        by_source.setdefault(item.get("source_name") or "Other", []).append(item)
    if not by_source:
        return ""
    rows = [
        f'<tr><td style="padding:32px 32px 4px;"><div style="border-top:4px solid {_INK};padding-top:14px;'
        'font-size:24px;font-weight:700;">Sources this week</div>'
        f'<div style="font-size:15px;color:{_MUTED};margin-top:4px;">Every article, by publisher, to open yourself.</div></td></tr>'
    ]
    for name in sorted(by_source, key=str.lower):
        articles = by_source[name]
        label = (f'{html.escape(name)} <span style="font-weight:400;color:{_MUTED};font-size:15px;">· '
                 f'{len(articles)} article{"s" if len(articles) != 1 else ""}</span>')
        if interactive:
            rows.append(f'<tr><td style="padding:12px 32px 0;"><details><summary style="font-size:17px;font-weight:700;">'
                        f'<span class="chev" style="color:{_MUTED};">▸</span> {label}</summary>'
                        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">')
        else:
            rows.append(f'<tr><td style="padding:18px 32px 4px;font-size:17px;font-weight:700;">{label}</td></tr>')
        for item in articles:
            link = item.get("link", "")
            visit = (f'<a href="{html.escape(link, quote=True)}" target="_blank" style="color:{_ACCENT};'
                     'font-weight:700;text-decoration:none;white-space:nowrap;">Visit →</a>') if link else ""
            row = (f'<tr><td style="font-size:15px;line-height:1.45;color:{_INK};padding:8px 0;border-bottom:1px solid {_RULE};">'
                   f'{html.escape(item.get("title", "Untitled"))}</td>'
                   f'<td align="right" width="76" style="font-size:15px;padding:8px 0 8px 12px;border-bottom:1px solid {_RULE};">{visit}</td></tr>')
            rows.append(row if interactive else
                        f'<tr><td style="padding:2px 32px;"><table role="presentation" width="100%" cellpadding="0" '
                        f'cellspacing="0">{row}</table></td></tr>')
        if interactive:
            rows.append('</table></details></td></tr>')
    return "".join(rows)


def summary_origin(source: str | None) -> str:
    """
    Who wrote this summary, in words a reader can weigh.

    Never a bare "Summary": a summary with no origin reads as the tool's own
    work, and this tool does not write summaries.
    """
    if source == "manual":
        return "Summarised by hand"
    if source and source.startswith("ollama:"):
        return f"Summarised by a local model ({source.split(':', 1)[1]})"
    if source:
        return f"Summarised by {source}"
    return "Summary, origin not recorded"


def _item_html(item: dict, flag_class: str) -> str:
    """One story: headline, source and date, the summary as dot points with
    the key facts bolded, and a small link to the article."""
    colour = next((c for key, (css, _, _, c, _) in _FLAGS.items() if css == flag_class), _ACCENT)
    flag = item.get("flag", "NOTE")
    title = html.escape(item.get("title", "Untitled"))
    teaser = html.escape(item.get("summary", ""))
    link = item.get("link", "")
    meta = " · ".join(part for part in (html.escape(item.get("source_name", "")), _day(item)) if part)
    confidence = item.get("confidence")

    body = (f'<div style="border-left:4px solid {colour};padding:4px 0 4px 14px;margin:14px 0 18px;">'
            f'<div style="margin-bottom:5px;">{_pill(flag)}</div>')
    if link:
        body += (f'<a href="{html.escape(link, quote=True)}" target="_blank" style="font-size:18px;font-weight:700;'
                 f'color:{_INK};text-decoration:none;line-height:1.35;">{title}</a>')
    else:
        body += f'<div style="font-size:18px;font-weight:700;line-height:1.35;">{title}</div>'
    if meta or confidence is not None:
        badge = ""
        if confidence is not None and flag in {"ACT", "KNOW"} and confidence < 0.6:
            badge = f' · <span style="color:#b45309;">flag uncertain ({confidence:.0%})</span>'
        body += f'<div style="font-size:13px;color:{_MUTED};margin-top:3px;">{meta}{badge}</div>'

    # A summary you had written stayed on the dashboard and never reached the
    # email, which is the copy actually read each week (IMPROVEMENTS.md item 4).
    points = summary_points(item.get("ai_summary") or "")
    if points:
        origin = html.escape(summary_origin(item.get("ai_source")))
        bullets = "".join(
            f'<li style="margin:0 0 4px;">{bold_html(html.escape(point))}</li>' for point in points
        )
        body += (f'<ul style="font-size:16px;line-height:1.5;color:#1e293b;margin:8px 0 0;padding-left:20px;">{bullets}</ul>'
                 f'<div style="font-size:12px;color:{_MUTED};margin-top:2px;font-style:italic;">{origin}</div>')
    elif teaser:
        # No summary yet: the publisher's own public words, so there is
        # something to read, clearly not presented as a summary.
        body += f'<div style="font-size:16px;color:#334155;line-height:1.5;margin-top:8px;">{teaser}</div>'

    body += _terms_box(item)

    if link:
        check = (f'<span style="color:{colour};font-weight:600;">Check the source before acting. </span>'
                 if flag == "ACT" else "")
        body += (f'<div style="font-size:14px;margin-top:8px;">{check}<a href="{html.escape(link, quote=True)}" '
                 f'target="_blank" style="color:{_ACCENT};font-weight:700;text-decoration:none;">Source →</a></div>')
        if item.get("link_ok") is False:
            body += '<div style="font-size:14px;color:#b91c1c;margin-top:4px;">⚠️ This link did not resolve when checked.</div>'

    body += '</div>'
    return body
