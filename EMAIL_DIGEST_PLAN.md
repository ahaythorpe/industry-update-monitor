# Emailed Digest Plan

Simple, free, no hosting. Weekly digest emails to yourself.

---

## The idea

Right now: `python src/monitor.py` prints a digest to stdout.

Next: add `--email` flag so it emails the digest to you instead. Works with AI switch OFF (free teasers), and later supports AI summaries when switched on.

---

## Tech approach

**Email sending:** Gmail SMTP + app-specific password (free, in `.env`, kept out of git).

**Format:** HTML email with:
- 🔴 ACT items first
- 🟠 KNOW items second  
- 🟢 NOTE items last (collapsed/optional)
- Each item: flag | title | teaser | "Read →" link

**Integration:** 
- New module `src/email_sender.py` — handles SMTP setup and sending
- `src/monitor.py` refactored to use it: `--email` flag or `USE_EMAIL = True` in config
- Same script, different output destination

**Cost:** Free. No API, no hosting, no recurring charges. Gmail's free tier covers this.

---

## Setup (user-facing)

### Step 1: Create Gmail app password
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and "Windows Computer" (or your device)
3. Google generates a 16-character password
4. Copy it (you'll see it once)

### Step 2: Add to `.env`
```
EMAIL_ADDRESS=your-gmail@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
```

### Step 3: Run with `--email`
```bash
python src/monitor.py --email
```

That's it. Digest lands in your inbox.

---

## Email module structure

```python
# src/email_sender.py

def send_digest_email(
    digest_items: list[Item],
    to_email: str,
    subject: str = "Weekly Industry Update Monitor Digest",
    use_ai: bool = False
) -> bool:
    """
    Send digest as HTML email to recipient.
    
    digest_items: List of Item dicts (flag, title, teaser, link, ai_summary)
    to_email: recipient email
    use_ai: if True, include ai_summary in email
    
    Returns True if sent; False if failed.
    """
    # Connect to Gmail SMTP
    # Build HTML email (flag colors, organized by priority)
    # Send via SMTP
    # Return success/failure
```

---

## Monitor.py changes

Add argument:
```python
parser.add_argument('--email', action='store_true', help='Email digest instead of printing')
```

If `--email` or `USE_EMAIL=True`:
- Call `send_digest_email(items, os.getenv('EMAIL_ADDRESS'), use_ai=USE_AI)`
- Print success message to stdout ("Digest emailed to...")
- No stdout dump of digest itself

---

## Email HTML format (rough)

```html
<h1>Industry Update Monitor Weekly Digest</h1>
<p>Week of [date]. [X items total]</p>

<h2>🔴 ACT (Action Required) — [count]</h2>
<div class="item">
  <h3>Title</h3>
  <p>Teaser...</p>
  <p><a href="https://...">Read at Source →</a></p>
</div>
...

<h2>🟠 KNOW (Should Know) — [count]</h2>
... (same format)

<h2>🟢 NOTE (Background) — [count]</h2>
<details><summary>Show [X] note items</summary>
... (collapsible)
</details>

<p style="font-size: 0.8em; color: #666;">
  <a href="https://github.com/your-repo">Built with Industry Update Monitor</a>
</p>
```

---

## AI integration (later, when USE_AI=True)

If `ai_summary` exists on an item, include it in the email:

```html
<div class="item">
  <h3>Title</h3>
  <p><strong>AI Summary:</strong> [ai_summary]</p>
  <p><em>Teaser: [teaser]</em></p>
  <p><a href="https://...">Read at Source →</a></p>
</div>
```

Users see both AI summary and teaser; they can choose which they read.

---

## Success criteria

- ✅ Email module sends HTML email via Gmail SMTP
- ✅ App password stored in `.env`, not committed
- ✅ Works with AI switch OFF (teaser emails only)
- ✅ Works with AI switch ON (includes AI summaries)
- ✅ `python src/monitor.py --email` sends digest
- ✅ Setup instructions clear and safe
- ✅ No cost, no hosting

---

## Build order

1. Create `src/email_sender.py` with send function
2. Add `.env` keys to `.env.example`
3. Add `--email` argument to monitor.py
4. Test locally with `--email` flag
5. Write setup doc (app password instructions)
6. Commit to GitHub as a feature
7. Later: integrate AI summaries (no code change needed; just works if USE_AI=True)
