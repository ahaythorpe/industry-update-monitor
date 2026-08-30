# Email Digest Setup

How to set up weekly emailed digests from Advice Monitor.

---

## Overview

Once you've got Phase 1 working locally (RSS collation + keyword prioritisation), you can add email delivery with a simple setup.

**Cost:** Free. No API charges, no hosting.  
**Setup time:** 5 minutes.  
**Requires:** Gmail account (or another email provider with SMTP — Gmail shown here).

---

## Step 1: Generate a Gmail app password

Gmail doesn't allow scripts to log in with your regular password. Instead, you create an app-specific password:

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. You may be prompted to sign in again. Do so.
3. Select **"Mail"** and **"Windows Computer"** (or your device type)
4. Google generates a 16-character password. **Copy it now** — you'll see it once.
5. Keep it somewhere safe for step 2.

---

## Step 2: Add to `.env`

Create a `.env` file in the project root (if you don't have one already):

```
# Email configuration
EMAIL_ADDRESS=your-gmail@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
```

Replace:
- `your-gmail@gmail.com` with your actual Gmail address
- `xxxx xxxx xxxx xxxx` with the 16-character app password (spaces are fine)

**Important:** `.env` is in `.gitignore`. It will never be committed to GitHub. Keep it private.

---

## Step 3: Test the email

Run with the `--email` flag:

```bash
python src/monitor.py --email
```

You should see:
```
✅ Digest emailed to your-gmail@gmail.com
```

Check your inbox. The digest arrives as an HTML email with:
- 🔴 ACT items (action required) first
- 🟠 KNOW items (should know) second
- 🟢 NOTE items (background) collapsed/optional
- Each item includes the original source link

---

## Troubleshooting

### "Email not configured"
**Issue:** `EMAIL_ADDRESS and EMAIL_PASSWORD in .env`  
**Fix:** Make sure `.env` exists and has both keys set.

### "Gmail authentication failed"
**Issue:** Wrong credentials in `.env`  
**Fix:** 
- Verify the Gmail address is correct
- Regenerate the app password (Steps 1–4 above) and paste it again
- Make sure you used an **app password**, not your regular Gmail password

### "Email send failed: 535 5.7.8"
**Issue:** Gmail rejected the password  
**Fix:** Same as authentication failed — regenerate and re-paste the app password.

### Still having issues?
Check that:
- You have internet connection (SMTP needs it)
- Two-factor authentication is enabled on your Gmail (required for app passwords)
- The `.env` file has no extra spaces or quotes around the password

---

## Using email with AI summaries (later)

By default, emailed digests show only publisher teasers (the free mode).

Once you set up AI (flip `USE_AI = True` and have a prepaid Anthropic key), you can email AI-summarised digests:

```bash
python src/monitor.py --email --ai
```

Each item in the email will include:
- The AI summary (one-sentence plain English explanation)
- The original teaser (so you can see what the publisher wrote)
- The source link (always)

Cost: the AI summaries cost cents per week, but only when the digest is run. Same safeguards apply — capped key, prepaid balance, no surprises.

---

## Scheduling weekly runs (next step, optional)

Right now you run `python src/monitor.py --email` manually. To automate it:

**On macOS/Linux:**
Use `crontab` to schedule a weekly run. Example:

```bash
crontab -e
```

Add this line (runs Mondays at 08:00):

```
0 8 * * 1 cd /Users/bella/Projects/advice-monitor && python src/monitor.py --email
```

Replace `/Users/bella/Projects/advice-monitor` with your project path.

**On Windows:**
Use Task Scheduler to run the Python command weekly.

**Via GitHub Actions (recommended later):**
Add a `.github/workflows/weekly-digest.yml` to automate it via GitHub (no local setup needed). This runs in the cloud and emails you automatically.

For now, running manually is fine — you're building the habit.

---

## Privacy & safety

- `.env` is git-ignored; your credentials never leave your machine.
- Emails contain only publisher teasers and links (never locked article text).
- Gmail's app password is specific to "Mail" — nothing else can use it.
- Revoke the app password anytime from Gmail settings (> App passwords > remove).

You control it completely.
