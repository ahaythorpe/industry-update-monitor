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


def send_digest_email(
    items: list,
    to_email: str,
    subject: str = "Weekly Advice Monitor Digest",
    use_ai: bool = False,
) -> bool:
    """
    Send a digest of items as an HTML email via Gmail SMTP.
    
    Args:
        items: list of dicts with keys: flag, title, summary, link, ai_summary (optional)
        to_email: recipient email address
        subject: email subject line
        use_ai: if True, include ai_summary field if present
        
    Returns:
        True if email sent successfully; False if failed.
        
    Requires in .env:
        EMAIL_ADDRESS=your-gmail@gmail.com
        EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  (app password, not regular password)
    """
    from_email = os.getenv("EMAIL_ADDRESS")
    app_password = os.getenv("EMAIL_PASSWORD")
    
    if not from_email or not app_password:
        print("❌ Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD in .env")
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
        
        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_email, app_password)
            server.send_message(msg)
        
        print(f"✅ Digest emailed to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Gmail authentication failed. Check EMAIL_ADDRESS and EMAIL_PASSWORD in .env")
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
    
    html_parts = [
        """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                h1 { color: #1a1a1a; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }
                h2 { color: #333; margin-top: 30px; margin-bottom: 15px; font-size: 1.1em; }
                .item { margin-bottom: 20px; padding: 15px; border-left: 4px solid #ddd; background: #f9f9f9; }
                .item-act { border-left-color: #dc2626; background: #fef2f2; }
                .item-know { border-left-color: #ea580c; background: #fffbf0; }
                .item-note { border-left-color: #16a34a; background: #f0fdf4; }
                .item h3 { margin: 0 0 10px 0; font-size: 1em; color: #1a1a1a; }
                .flag { display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; margin-right: 8px; }
                .flag-act { background: #fecaca; color: #991b1b; }
                .flag-know { background: #fed7aa; color: #92400e; }
                .flag-note { background: #bbf7d0; color: #166534; }
                .teaser { margin: 10px 0; font-size: 0.95em; color: #555; }
                .summary { margin: 10px 0; padding: 10px; background: white; border-radius: 4px; font-size: 0.95em; color: #444; border-left: 3px solid #0066cc; }
                .link { margin: 10px 0; }
                .link a { color: #0066cc; text-decoration: none; font-weight: 500; }
                .link a:hover { text-decoration: underline; }
                .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.85em; color: #666; }
                .footer a { color: #0066cc; text-decoration: none; }
                .count { color: #666; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Advice Monitor Weekly Digest</h1>
                <p style="color: #666;">Week of <strong>{}</strong></p>
        """.format(today)
    ]
    
    # ACT section
    if by_flag["ACT"]:
        html_parts.append(
            f'<h2>🔴 ACT (Action Required) <span class="count">— {len(by_flag["ACT"])} items</span></h2>'
        )
        for item in by_flag["ACT"]:
            html_parts.append(_item_html(item, "act", use_ai))
    
    # KNOW section
    if by_flag["KNOW"]:
        html_parts.append(
            f'<h2>🟠 KNOW (Should Know) <span class="count">— {len(by_flag["KNOW"])} items</span></h2>'
        )
        for item in by_flag["KNOW"]:
            html_parts.append(_item_html(item, "know", use_ai))
    
    # NOTE section (collapsible if many items)
    if by_flag["NOTE"]:
        note_count = len(by_flag["NOTE"])
        if note_count > 5:
            html_parts.append(
                f'<h2>🟢 NOTE (Background) <span class="count">— {note_count} items</span></h2>'
                '<details style="cursor: pointer;">'
                f'<summary style="font-weight: bold; padding: 10px; background: #f0fdf4; border-radius: 4px;">Show {note_count} note items</summary>'
            )
            for item in by_flag["NOTE"]:
                html_parts.append(_item_html(item, "note", use_ai))
            html_parts.append('</details>')
        else:
            html_parts.append(
                f'<h2>🟢 NOTE (Background) <span class="count">— {note_count} items</span></h2>'
            )
            for item in by_flag["NOTE"]:
                html_parts.append(_item_html(item, "note", use_ai))
    
    # Footer
    html_parts.append(
        """
                <div class="footer">
                    <p>Built with <a href="https://github.com/your-username/advice-monitor">Advice Monitor</a> — open source, free, safe, no paywalls.</p>
                    <p style="font-size: 0.8em; color: #999;">This digest contains only public teasers and links. Always read the source before acting on anything flagged 🔴.</p>
                </div>
            </div>
        </body>
        </html>
        """
    )
    
    return "".join(html_parts)


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
