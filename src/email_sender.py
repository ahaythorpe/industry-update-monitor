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
    subject: str = "Industry Update Monitor — weekly digest",
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

        # Build HTML body
        body_html = _build_html_digest(by_flag)

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


def summary_points(summary: str) -> list[str]:
    """A summary's dot points. The local model writes them on one line, each
    starting "• "; an older one-sentence summary is a single point."""
    points = [p.strip() for p in re.split(r"\s*•\s*", summary or "") if p.strip()]
    return points or ([summary.strip()] if (summary or "").strip() else [])


def bold_html(escaped: str) -> str:
    """**key fact** → <b>key fact</b>, on text that is already HTML-escaped."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def _button(href: str, label: str, colour: str = _ACCENT) -> str:
    """A link styled as a button that survives Gmail and Outlook."""
    safe = html.escape(href, quote=True)
    return (
        f'<a href="{safe}" target="_blank" style="display:inline-block;padding:9px 16px;'
        f'border-radius:6px;background:{colour};color:#ffffff;font-size:15px;font-weight:600;'
        f'text-decoration:none;">{html.escape(label)}</a>'
    )


def _day(item: dict) -> str:
    raw = (item.get("created_at") or item.get("published") or "")[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%-d %b")
    except ValueError:
        return ""


def _build_html_digest(by_flag: dict, interactive: bool = False) -> str:
    """The weekly newsletter, organised by category.

    Email clients (Gmail above all) ignore drop-downs, so the email stays
    short instead: an overview by category, the ACT headlines, then each
    category with its ACT stories in full and the rest as one line each.
    `interactive=True` is the same page for a browser — the file Telegram
    carries — where each category and each source folds away.
    """
    today = datetime.now().strftime("%-d %B %Y")
    items = [i for flag in _FLAGS for i in by_flag.get(flag, [])]
    total = len(items)
    act = len(by_flag.get("ACT", []))

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
        f'<div style="font-size:13px;text-transform:uppercase;letter-spacing:1px;color:{colour};font-weight:700;">{flag}</div></div></td>'
        for flag, (_, _, _, colour, bg) in _FLAGS.items()
    )
    lead = (f"Start with the <b>{act}</b> ACT stor{'ies' if act != 1 else 'y'} — they change what you must do."
            if act else "Nothing this week changes what you must do.")
    out.append(
        '<tr><td style="padding:26px 27px 6px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{tiles}</tr></table>'
        f'<p style="font-size:17px;line-height:1.55;margin:18px 5px 0;">{lead}</p>'
        '</td></tr>'
    )

    categories = _by_category(items)
    out.append(_category_overview(categories))
    if by_flag.get("ACT"):
        out.append(_act_list(by_flag["ACT"]))

    for topic, stories in categories:
        counts = _counts(stories)
        heading = (f'<span style="font-size:23px;font-weight:700;">{html.escape(topic)}</span> '
                   f'<span style="font-size:15px;color:{_MUTED};">· {counts}</span>')
        body = "".join(
            _item_html(i, _FLAGS[i["flag"]][0]) if i.get("flag") == "ACT" else _compact_row(i)
            for i in stories
        )
        if interactive:
            opened = " open" if any(i.get("flag") == "ACT" for i in stories) else ""
            out.append(
                f'<tr><td style="padding:14px 32px 0;"><details{opened} style="border-top:1px solid {_RULE};padding-top:14px;">'
                f'<summary><span class="chev" style="color:{_MUTED};">▸</span> {heading}</summary>'
                f'<div style="padding-top:6px;">{body}</div></details></td></tr>'
            )
        else:
            out.append(
                f'<tr><td style="padding:26px 32px 0;"><div style="border-top:3px solid {_INK};padding-top:12px;">{heading}</div>'
                f'<div style="padding-top:4px;">{body}</div></td></tr>'
            )

    out.append(_sources_html(items, interactive))
    out.append(
        f'<tr><td style="padding:26px 32px 30px;border-top:1px solid {_RULE};font-size:14px;line-height:1.6;color:{_MUTED};">'
        'Summaries are triage, not advice: each says who wrote it, and an ACT story is read at its source '
        'before it is acted on. Every story comes from a free public feed — nothing here is behind a paywall.'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )
    return "".join(out)


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
    return " · ".join(f"{n} {flag}" for flag in _FLAGS
                      if (n := sum(1 for i in stories if i.get("flag") == flag)))


def _category_overview(categories: list) -> str:
    rows = "".join(
        f'<tr><td style="font-size:16px;padding:7px 0;border-bottom:1px solid {_RULE};">{html.escape(topic)}</td>'
        f'<td align="right" style="font-size:14px;padding:7px 0;border-bottom:1px solid {_RULE};white-space:nowrap;">'
        + " ".join(
            f'<span style="color:{_FLAGS[flag][3]};font-weight:700;">{n} {flag}</span>'
            for flag in _FLAGS if (n := sum(1 for i in stories if i.get("flag") == flag))
        )
        + '</td></tr>'
        for topic, stories in categories
    )
    return (f'<tr><td style="padding:24px 32px 4px;"><div style="font-size:19px;font-weight:700;margin-bottom:6px;">'
            f'This week by category</div><table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'{rows}</table></td></tr>')


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
            f'<div style="font-size:19px;font-weight:700;color:{colour};margin-bottom:4px;">Act on these first</div>'
            f'{rows}</div></td></tr>')


def _compact_row(item: dict) -> str:
    """A KNOW or NOTE story in one tidy line: urgency, headline, key point."""
    flag = item.get("flag", "NOTE")
    colour = _FLAGS.get(flag, _FLAGS["NOTE"])[3]
    title = html.escape(item.get("title", "Untitled"))
    link = item.get("link", "")
    head = (f'<a href="{html.escape(link, quote=True)}" target="_blank" style="color:{_INK};font-weight:700;'
            f'text-decoration:none;">{title}</a>') if link else f"<b>{title}</b>"
    points = summary_points(item.get("ai_summary") or "")
    point = (f'<div style="font-size:15px;color:#334155;margin-top:3px;line-height:1.5;">'
             f'{bold_html(html.escape(points[0]))}</div>') if points else ""
    source = html.escape(item.get("source_name", ""))
    return (f'<div style="padding:11px 0;border-bottom:1px solid {_RULE};">'
            f'<div style="font-size:16px;line-height:1.4;"><span style="font-size:12px;font-weight:700;color:{colour};'
            f'margin-right:6px;">{flag}</span>{head}</div>{point}'
            f'<div style="font-size:13px;color:{_MUTED};margin-top:3px;">{source}</div></div>')


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
    """One story card: headline, source and date, the summary as dot points
    with the key facts bolded, and a button to the article."""
    colour = next((c for key, (css, _, _, c, _) in _FLAGS.items() if css == flag_class), _ACCENT)
    title = html.escape(item.get("title", "Untitled"))
    teaser = html.escape(item.get("summary", ""))
    link = item.get("link", "")
    meta = " · ".join(part for part in (html.escape(item.get("source_name", "")), _day(item)) if part)
    confidence = item.get("confidence")

    body = f'<div style="border-left:4px solid {colour};padding:6px 0 6px 16px;">'
    if link:
        body += (f'<a href="{html.escape(link, quote=True)}" target="_blank" style="font-size:20px;font-weight:700;'
                 f'color:{_INK};text-decoration:none;line-height:1.35;">{title}</a>')
    else:
        body += f'<div style="font-size:20px;font-weight:700;line-height:1.35;">{title}</div>'
    if meta or confidence is not None:
        badge = ""
        if confidence is not None and item.get("flag") in {"ACT", "KNOW"} and confidence < 0.6:
            badge = f' · <span style="color:#b45309;">flag uncertain ({confidence:.0%})</span>'
        body += f'<div style="font-size:14px;color:{_MUTED};margin-top:4px;">{meta}{badge}</div>'

    # A summary you had written stayed on the dashboard and never reached the
    # email, which is the copy actually read each week (IMPROVEMENTS.md item 4).
    points = summary_points(item.get("ai_summary") or "")
    if points:
        origin = html.escape(summary_origin(item.get("ai_source")))
        bullets = "".join(
            f'<li style="margin:0 0 6px;">{bold_html(html.escape(point))}</li>' for point in points
        )
        body += (f'<ul style="font-size:17px;line-height:1.55;margin:12px 0 0;padding-left:22px;">{bullets}</ul>'
                 f'<div style="font-size:13px;color:{_MUTED};margin-top:4px;font-style:italic;">{origin}</div>')
    elif teaser:
        # No summary yet: the publisher's own public words, so there is
        # something to read, clearly not presented as a summary.
        body += f'<div style="font-size:16px;color:#334155;line-height:1.55;margin-top:10px;">{teaser}</div>'

    if link:
        body += f'<div style="margin-top:14px;">{_button(link, "Read the article →", colour)}</div>'
        if item.get("link_ok") is False:
            body += '<div style="font-size:14px;color:#b91c1c;margin-top:6px;">⚠️ This link did not resolve when checked.</div>'

    body += '</div>'
    return body
