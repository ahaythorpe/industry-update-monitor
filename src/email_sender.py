"""
Email digest sender for Industry Update Monitor.

Sends collated, prioritised items as an HTML email digest via Gmail SMTP.
Requires a Gmail app password (not the regular Gmail password), kept in the
macOS Keychain under advice-monitor-email, or in .env.

Safe: never includes full article text, only publisher teasers and links.
"""

import html
import os
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


def _button(href: str, label: str, colour: str = _ACCENT) -> str:
    """A link styled as a button that survives Gmail and Outlook."""
    safe = html.escape(href, quote=True)
    return (
        f'<a href="{safe}" target="_blank" style="display:inline-block;padding:7px 14px;'
        f'border-radius:6px;background:{colour};color:#ffffff;font-size:13px;font-weight:600;'
        f'text-decoration:none;">{html.escape(label)}</a>'
    )


def _day(item: dict) -> str:
    raw = (item.get("created_at") or item.get("published") or "")[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%-d %b")
    except ValueError:
        return ""


def _build_html_digest(by_flag: dict) -> str:
    """The weekly email, laid out as a newsletter: at-a-glance counts, then
    each urgency grouped by category, then every source with its articles."""
    today = datetime.now().strftime("%-d %B %Y")
    total = sum(len(items) for items in by_flag.values())
    act = len(by_flag.get("ACT", []))

    out = [
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>',
        f'<body style="margin:0;padding:0;background:#f1f5f9;font-family:Helvetica,Arial,sans-serif;color:{_INK};">',
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;">'
        '<tr><td align="center" style="padding:24px 12px;">',
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="width:100%;max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;">',
        # Masthead
        f'<tr><td style="background:{_INK};padding:28px 32px;">'
        '<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#7dd3fc;font-weight:700;">Advice Monitor</div>'
        '<div style="font-size:24px;font-weight:700;color:#ffffff;margin-top:6px;">This week in Australian advice</div>'
        f'<div style="font-size:13px;color:#cbd5e1;margin-top:6px;">{today} · {total} stories from the public trade press</div>'
        '</td></tr>',
    ]

    # At a glance
    tiles = "".join(
        f'<td width="33%" style="padding:0 4px;"><div style="background:{bg};border-radius:8px;padding:12px;text-align:center;">'
        f'<div style="font-size:22px;font-weight:700;color:{colour};">{len(by_flag.get(flag, []))}</div>'
        f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{colour};font-weight:700;">{flag}</div></div></td>'
        for flag, (_, _, _, colour, bg) in _FLAGS.items()
    )
    lead = (f"Start with the <strong>{act}</strong> ACT item{'s' if act != 1 else ''} — they change what you must do."
            if act else "Nothing this week changes what you must do.")
    out.append(
        '<tr><td style="padding:24px 28px 8px;">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{tiles}</tr></table>'
        f'<p style="font-size:14px;line-height:1.5;color:{_MUTED};margin:16px 4px 0;">{lead}</p>'
        '</td></tr>'
    )

    for flag, (css, heading, blurb, colour, _bg) in _FLAGS.items():
        items = by_flag.get(flag, [])
        if not items:
            continue
        out.append(
            f'<tr><td style="padding:24px 32px 4px;">'
            f'<div style="border-top:3px solid {colour};padding-top:12px;">'
            f'<div style="font-size:18px;font-weight:700;color:{colour};">{heading} · {len(items)}</div>'
            f'<div style="font-size:13px;color:{_MUTED};margin-top:2px;">{blurb}</div></div></td></tr>'
        )
        topics: dict = {}
        for item in items:
            topics.setdefault(item.get("topic") or "Other news", []).append(item)
        for topic, grouped in topics.items():
            out.append(
                f'<tr><td style="padding:14px 32px 0;font-size:11px;letter-spacing:1.5px;'
                f'text-transform:uppercase;color:{_MUTED};font-weight:700;">{html.escape(topic)}</td></tr>'
            )
            for item in grouped:
                out.append(f'<tr><td style="padding:8px 32px;">{_item_html(item, css)}</td></tr>')

    out.append(_sources_html([i for items in by_flag.values() for i in items]))

    out.append(
        f'<tr><td style="padding:24px 32px 28px;border-top:1px solid {_RULE};font-size:12px;line-height:1.6;color:{_MUTED};">'
        'Summaries are triage, not advice: each says who wrote it, and an ACT item is read at its source '
        'before it is acted on. Every story comes from a free public feed — nothing here is behind a paywall.'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )
    return "".join(out)


def _sources_html(items: list) -> str:
    """Every publisher this week, each article under it with its own button."""
    by_source: dict = {}
    for item in items:
        by_source.setdefault(item.get("source_name") or "Other", []).append(item)
    if not by_source:
        return ""
    rows = [
        f'<tr><td style="padding:28px 32px 4px;"><div style="border-top:3px solid {_INK};padding-top:12px;'
        'font-size:18px;font-weight:700;">Sources this week</div></td></tr>'
    ]
    for name in sorted(by_source, key=str.lower):
        articles = by_source[name]
        rows.append(
            f'<tr><td style="padding:14px 32px 2px;font-size:14px;font-weight:700;">{html.escape(name)} '
            f'<span style="font-weight:400;color:{_MUTED};font-size:12px;">· {len(articles)}</span></td></tr>'
        )
        for item in articles:
            link = item.get("link", "")
            visit = (f'<a href="{html.escape(link, quote=True)}" target="_blank" style="color:{_ACCENT};'
                     'font-weight:600;text-decoration:none;white-space:nowrap;">Visit →</a>') if link else ""
            rows.append(
                f'<tr><td style="padding:3px 32px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
                f'<tr><td style="font-size:13px;line-height:1.4;color:{_INK};padding:5px 0;border-bottom:1px solid {_RULE};">'
                f'{html.escape(item.get("title", "Untitled"))}</td>'
                f'<td align="right" width="70" style="font-size:13px;padding:5px 0 5px 12px;border-bottom:1px solid {_RULE};">{visit}</td>'
                '</tr></table></td></tr>'
            )
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
    """One story card. All feed-supplied text is escaped."""
    colour = next((c for key, (css, _, _, c, _) in _FLAGS.items() if css == flag_class), _ACCENT)
    title = html.escape(item.get("title", "Untitled"))
    teaser = html.escape(item.get("summary", ""))
    link = item.get("link", "")
    meta = " · ".join(part for part in (html.escape(item.get("source_name", "")), _day(item)) if part)
    confidence = item.get("confidence")

    body = f'<div style="border-left:4px solid {colour};padding:4px 0 4px 14px;">'
    if link:
        body += (f'<a href="{html.escape(link, quote=True)}" target="_blank" style="font-size:16px;font-weight:700;'
                 f'color:{_INK};text-decoration:none;line-height:1.35;">{title}</a>')
    else:
        body += f'<div style="font-size:16px;font-weight:700;line-height:1.35;">{title}</div>'
    if meta or confidence is not None:
        badge = ""
        if confidence is not None and item.get("flag") in {"ACT", "KNOW"}:
            badge = f' · {confidence:.0%} sure of the flag' if confidence >= 0.6 else f' · <span style="color:#b45309;">only {confidence:.0%} sure of the flag</span>'
        body += f'<div style="font-size:12px;color:{_MUTED};margin-top:3px;">{meta}{badge}</div>'

    # A summary you had written stayed on the dashboard and never reached the
    # email, which is the copy actually read each week (IMPROVEMENTS.md item 4).
    summary = html.escape(item.get("ai_summary") or "")
    if summary:
        origin = html.escape(summary_origin(item.get("ai_source")))
        body += (f'<div style="font-size:14px;line-height:1.55;margin-top:8px;">{summary}</div>'
                 f'<div style="font-size:11px;color:{_MUTED};margin-top:3px;font-style:italic;">{origin}</div>')

    # The publisher's own words stay, so a summary can be checked against them.
    if teaser:
        style = "font-size:13px;color:#475569;" if summary else "font-size:14px;color:#334155;"
        body += f'<div style="{style}line-height:1.5;margin-top:8px;">{teaser}</div>'

    if link:
        body += f'<div style="margin-top:10px;">{_button(link, "Read the article →", colour)}</div>'
        if item.get("link_ok") is False:
            body += '<div style="font-size:12px;color:#b91c1c;margin-top:4px;">⚠️ This link did not resolve when checked.</div>'

    body += '</div>'
    return body
