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


def _build_html_digest(by_flag: dict) -> str:
    """Build HTML email body with items grouped by flag."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Build HTML with proper escaping
    markup = '<!DOCTYPE html><html><head><meta charset="utf-8"><style type="text/css">'
    markup += 'body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }'
    markup += '.container { max-width: 600px; margin: 0 auto; padding: 20px; }'
    markup += 'h1 { color: #1a1a1a; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }'
    markup += 'h2 { color: #333; margin-top: 30px; margin-bottom: 15px; font-size: 1.1em; }'
    markup += '.item { margin-bottom: 20px; padding: 15px; border-left: 4px solid #ddd; background: #f9f9f9; }'
    markup += '.item-act { border-left-color: #dc2626; background: #fef2f2; }'
    markup += '.item-know { border-left-color: #ea580c; background: #fffbf0; }'
    markup += '.item-note { border-left-color: #16a34a; background: #f0fdf4; }'
    markup += '.item h3 { margin: 0 0 10px 0; font-size: 1em; color: #1a1a1a; }'
    markup += '.teaser { margin: 10px 0; font-size: 0.95em; color: #555; }'
    markup += '.summary { margin: 10px 0; padding: 10px; background: white; border-radius: 4px; font-size: 0.95em; color: #444; border-left: 3px solid #0066cc; }'
    markup += '.link { margin: 10px 0; }'
    markup += '.link a { color: #0066cc; text-decoration: none; font-weight: 500; }'
    markup += '.footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.85em; color: #666; }'
    markup += '.count { color: #666; font-size: 0.9em; }'
    markup += '.confidence { display: inline-block; margin-left: 8px; padding: 1px 7px; border-radius: 10px; background: #eee; color: #555; font-size: 0.75em; font-weight: 600; vertical-align: middle; }'
    markup += '.badge-low { background: #fde68a; color: #78350f; }'
    markup += '.deadlink { color: #b91c1c; font-size: 0.85em; }'
    markup += '</style></head><body><div class="container">'
    markup += '<h1>Industry Update Monitor Weekly Digest</h1>'
    markup += f'<p style="color: #666;">Week of <strong>{today}</strong></p>'
    
    # ACT section
    if by_flag["ACT"]:
        markup += f'<h2>ACT (Action Required) — {len(by_flag["ACT"])} items</h2>'
        for item in by_flag["ACT"]:
            markup += _item_html(item, "act")
    
    # KNOW section
    if by_flag["KNOW"]:
        markup += f'<h2>KNOW (Should Know) — {len(by_flag["KNOW"])} items</h2>'
        for item in by_flag["KNOW"]:
            markup += _item_html(item, "know")
    
    # NOTE section
    if by_flag["NOTE"]:
        note_count = len(by_flag["NOTE"])
        markup += f'<h2>NOTE (Background) — {note_count} items</h2>'
        for item in by_flag["NOTE"]:
            markup += _item_html(item, "note")
    
    # Footer
    markup += '<div class="footer"><p>Built with Industry Update Monitor - open source, free, safe, no paywalls.</p></div>'
    markup += '</div></body></html>'
    
    return markup


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
    """Build HTML for a single digest item. All feed-supplied text is escaped."""
    title = html.escape(item.get("title", "Untitled"))
    teaser = html.escape(item.get("summary", ""))
    link = item.get("link", "")
    source_name = html.escape(item.get("source_name", ""))
    confidence = item.get("confidence")

    body = f'<div class="item item-{flag_class}">'
    body += f'<h3>{title}'
    if confidence is not None and item.get("flag") in {"ACT", "KNOW"}:
        badge_class = "confidence" if confidence >= 0.6 else "confidence badge-low"
        body += f'<span class="{badge_class}">{confidence:.0%}</span>'
    body += '</h3>'

    # A summary you had written stayed on the dashboard and never reached the
    # email, which is the copy actually read each week (IMPROVEMENTS.md item 4).
    summary = html.escape(item.get("ai_summary") or "")
    if summary:
        origin = html.escape(summary_origin(item.get("ai_source")))
        body += f'<div class="summary"><strong>{origin}:</strong> {summary}</div>'

    if teaser:
        body += f'<div class="teaser">{teaser}</div>'

    if link:
        safe_link = html.escape(link, quote=True)
        via = f' <span class="count">via {source_name}</span>' if source_name else ""
        body += f'<div class="link"><a href="{safe_link}" target="_blank">Read at source →</a>{via}</div>'
        if item.get("link_ok") is False:
            body += '<div class="deadlink">⚠️ This link did not resolve when checked.</div>'

    body += '</div>'
    return body
