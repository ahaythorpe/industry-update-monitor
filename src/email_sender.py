"""
Email digest sender for Advice Monitor.

Sends collated, prioritised items as an HTML email digest via Gmail SMTP.
Requires Gmail app password stored in .env (not regular Gmail password).

Safe: never includes full article text, only publisher teasers and links.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def _smtp_config() -> dict:
    """Resolve the SMTP configuration, preferring provider variables when present."""
    smtp_host = os.getenv("SMTP_HOST")
    if smtp_host:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER") or os.getenv("EMAIL_ADDRESS")
        smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
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
        "password": os.getenv("EMAIL_PASSWORD"),
        "from_email": os.getenv("EMAIL_ADDRESS"),
        "use_tls": False,
    }


def send_digest_email(
    items: list,
    to_email: str,
    subject: str = "Weekly Advice Monitor Digest",
    use_ai: bool = False,
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
        html = _build_html_digest(by_flag, use_ai)

        # Create email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        # Attach HTML part
        msg.attach(MIMEText(html, "html"))

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


def _build_html_digest(by_flag: dict, use_ai: bool) -> str:
    """Build HTML email body with items grouped by flag."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Build HTML with proper escaping
    html = '<!DOCTYPE html><html><head><meta charset="utf-8"><style type="text/css">'
    html += 'body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }'
    html += '.container { max-width: 600px; margin: 0 auto; padding: 20px; }'
    html += 'h1 { color: #1a1a1a; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }'
    html += 'h2 { color: #333; margin-top: 30px; margin-bottom: 15px; font-size: 1.1em; }'
    html += '.item { margin-bottom: 20px; padding: 15px; border-left: 4px solid #ddd; background: #f9f9f9; }'
    html += '.item-act { border-left-color: #dc2626; background: #fef2f2; }'
    html += '.item-know { border-left-color: #ea580c; background: #fffbf0; }'
    html += '.item-note { border-left-color: #16a34a; background: #f0fdf4; }'
    html += '.item h3 { margin: 0 0 10px 0; font-size: 1em; color: #1a1a1a; }'
    html += '.teaser { margin: 10px 0; font-size: 0.95em; color: #555; }'
    html += '.summary { margin: 10px 0; padding: 10px; background: white; border-radius: 4px; font-size: 0.95em; color: #444; border-left: 3px solid #0066cc; }'
    html += '.link { margin: 10px 0; }'
    html += '.link a { color: #0066cc; text-decoration: none; font-weight: 500; }'
    html += '.footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.85em; color: #666; }'
    html += '.count { color: #666; font-size: 0.9em; }'
    html += '</style></head><body><div class="container">'
    html += '<h1>Advice Monitor Weekly Digest</h1>'
    html += f'<p style="color: #666;">Week of <strong>{today}</strong></p>'
    
    # ACT section
    if by_flag["ACT"]:
        html += f'<h2>ACT (Action Required) — {len(by_flag["ACT"])} items</h2>'
        for item in by_flag["ACT"]:
            html += _item_html(item, "act", use_ai)
    
    # KNOW section
    if by_flag["KNOW"]:
        html += f'<h2>KNOW (Should Know) — {len(by_flag["KNOW"])} items</h2>'
        for item in by_flag["KNOW"]:
            html += _item_html(item, "know", use_ai)
    
    # NOTE section
    if by_flag["NOTE"]:
        note_count = len(by_flag["NOTE"])
        html += f'<h2>NOTE (Background) — {note_count} items</h2>'
        for item in by_flag["NOTE"]:
            html += _item_html(item, "note", use_ai)
    
    # Footer
    html += '<div class="footer"><p>Built with Advice Monitor - open source, free, safe, no paywalls.</p></div>'
    html += '</div></body></html>'
    
    return html


def _item_html(item: dict, flag_class: str, use_ai: bool) -> str:
    """Build HTML for a single digest item."""
    title = item.get("title", "Untitled")
    teaser = item.get("summary", "")
    link = item.get("link", "")
    ai_summary = item.get("ai_summary")
    
    html = f'<div class="item item-{flag_class}">'
    html += f'<h3>{title}</h3>'
    
    if teaser:
        html += f'<div class="teaser">{teaser}</div>'
    
    if use_ai and ai_summary:
        html += f'<div class="summary"><strong>Summary:</strong> {ai_summary}</div>'
    
    if link:
        html += f'<div class="link"><a href="{link}" target="_blank">Read at source →</a></div>'
    
    html += '</div>'
    return html
