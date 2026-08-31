"""
Advice Industry Monitor  —  safe, free-first, no paywall bypassing.

CORE RULE (do not remove): this tool only ever reads content that was
legitimately delivered to you — RSS feeds and free pages the publisher serves
to the public. It NEVER logs in, NEVER fetches text behind a paywall, and
NEVER stores or reconstructs locked content. Feeds in, free sources out.

Parts:
  1. load_sources()          -> your flagged, categorised source list
  2. fetch_feed_items()      -> pull headlines+summaries from a source's RSS
  3. summarise_items()       -> AI summary WITH references (stub + real call)
  4. find_free_version()     -> given a free headline/teaser, search your free
                                sources for the same story (never reads the wall)

Run:  python monitor.py
Deps: pip install feedparser anthropic     (anthropic only needed for AI parts)
"""

import json
import os
import re
import argparse
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv not installed, fall back to reading .env manually
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

DATA = Path(__file__).resolve().parent.parent / "data" / "sources.json"
USE_AI = False
USE_EMAIL = False  # Set to True to email digest; requires EMAIL_ADDRESS and EMAIL_PASSWORD in .env

FLAG_EMOJI = {"ACT": "🔴 ACT", "KNOW": "🟠 KNOW", "NOTE": "🟢 NOTE"}
ALLOWED_ACCESS = {"free", "free_signup"}
ALLOWED_INTAKE = {"email_alert", "email_newsletter", "rss"}
FLAG_ORDER = {"ACT": 0, "KNOW": 1, "NOTE": 2}

ACT_TERMS = (
    "asic", "afca", "regulator", "legislation", "regulatory", "breach",
    "ban", "banned", "deadline", "obligation", "determination", "law",
    "rule change", "compliance", "licence cancellation",
)
KNOW_TERMS = (
    "policy", "reform", "industry", "appointed", "appoints", "chief",
    "commentary", "technical", "strategy", "announces", "hired", "hire",
)
PROMOTIONAL_TERMS = (
    "unsubscribe", "sponsored", "advertisement", "register now", "limited offer",
)


class UnsafeSourceError(ValueError):
    """Raised when a source is not explicitly allowed for automated intake."""


def validate_feed_source(source):
    """Validate a configured public feed before any network request is made."""
    if not isinstance(source, dict):
        raise UnsafeSourceError("fetch_feed_items requires a configured source object")
    if source.get("access") not in ALLOWED_ACCESS:
        raise UnsafeSourceError(f"source is not free: {source.get('name', '(unnamed)')}")
    if source.get("intake") not in ALLOWED_INTAKE:
        raise UnsafeSourceError(f"source intake is not approved: {source.get('name', '(unnamed)')}")

    feed_url = source.get("rss")
    parsed_feed = urlparse(feed_url or "")
    parsed_home = urlparse(source.get("home") or "")
    if parsed_feed.scheme not in {"http", "https"} or not parsed_feed.netloc:
        raise UnsafeSourceError(f"source has no valid public RSS URL: {source.get('name', '(unnamed)')}")
    if parsed_feed.hostname != parsed_home.hostname:
        raise UnsafeSourceError("RSS host must match the configured source home")
    feed_path = parsed_feed.path.lower()
    feed_markers = ("/feed", "/rss", "/atom")
    feed_extensions = (".xml", ".rss", ".atom", ".json")
    if not feed_path.endswith(feed_extensions) and not any(marker in feed_path for marker in feed_markers):
        raise UnsafeSourceError("configured URL does not look like a public feed")
    return feed_url


def classify_email(email):
    """Assign a cautious priority using only the received email's text."""
    text = f"{email.get('subject', '')} {email.get('body', '')}".lower()
    return classify_text(text)


def classify_text(text):
    """Assign a cautious priority using supplied public text only."""
    text = (text or "").lower()
    if any(term in text for term in ACT_TERMS):
        return "ACT"
    if any(term in text for term in KNOW_TERMS):
        return "KNOW"
    return "NOTE"


def collate_items(items, max_items=50):
    """Deduplicate and prioritise RSS-style items without using AI."""
    if max_items < 1 or max_items > 100:
        raise ValueError("max_items must be between 1 and 100")
    unique = {}
    for item in items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        link = item.get("link", "").strip()
        key = link or f"{title.lower()}|{summary[:120].lower()}"
        if not key or key in unique:
            continue
        enriched = dict(item)
        enriched["flag"] = item.get("flag") or classify_text(f"{title} {summary}")
        unique[key] = enriched
    return sorted(unique.values(), key=lambda item: FLAG_ORDER[item["flag"]])[:max_items]


def _clean_email_text(text):
    text = unescape(re.sub(r"<[^>]+>", " ", text or ""))
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned and not any(term in cleaned.lower() for term in PROMOTIONAL_TERMS):
            lines.append(cleaned)
    return " ".join(lines)


def extractive_summary(email, max_sentences=2):
    """Return up to two useful sentences already present in the email."""
    text = _clean_email_text(email.get("body", ""))
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not sentences:
        return "No summary text was available."
    subject_terms = set(re.findall(r"[a-z]{4,}", email.get("subject", "").lower()))
    ranked = sorted(
        enumerate(sentences),
        key=lambda pair: (
            -sum(term in pair[1].lower() for term in subject_terms),
            pair[0],
        ),
    )
    selected = sorted(ranked[:max_sentences])
    return " ".join(sentences[index] for index, _ in selected)


def assess_email(email):
    """Create a sourced, non-AI assessment of one legitimately received email."""
    flag = classify_email(email)
    result = {
        "flag": flag,
        "summary": extractive_summary(email),
        "source": email.get("source", email.get("sender", "unknown")),
        "link": email.get("link", ""),
    }
    if flag == "ACT":
        result["instruction"] = "Read the original source before relying on this."
    return result


def format_assessment(assessments):
    """Format assessments as readable bullet points grouped by priority."""
    lines = ["\n=== EMAIL ASSESSMENT (no AI) ==="]
    for item in sorted(assessments, key=lambda value: FLAG_ORDER[value["flag"]]):
        lines.append(f"\n{FLAG_EMOJI[item['flag']]}")
        lines.append(f"- {item['summary']}")
        if item.get("instruction"):
            lines.append(f"- {item['instruction']}")
        lines.append(f"- Source: {item['source']}")
        lines.append(f"- Link: {item['link'] or '(no link supplied)'}")
    return "\n".join(lines)


# ---------- Part 1: sources ----------
def load_sources():
    with open(DATA) as f:
        cfg = json.load(f)
    return cfg["sources"], cfg["free_search_sources"]


def show_sources():
    sources, _ = load_sources()
    print("\n=== YOUR SOURCES ===")
    for s in sources:
        rss = s["rss"] or "(no RSS set — add on the site)"
        print(f"{FLAG_EMOJI[s['flag']]:9} | {s['access']:12} | {s['name']}")
        print(f"            feed: {rss}")


# ---------- Part 2a: fetch (RSS only — legitimate intake) ----------
def fetch_feed_items(source, limit=10):
    """Read an explicitly configured public RSS feed."""
    import feedparser  # imported here so Part 1 works without it installed
    feed = feedparser.parse(validate_feed_source(source))
    items = []
    for entry in feed.entries[:limit]:
        items.append({
            "title": entry.get("title", ""),
            # 'summary' is the teaser the publisher CHOOSES to make public.
            # We use only this. We never fetch the full/locked article body.
            "summary": entry.get("summary", "")[:600],
            "link": entry.get("link", ""),
        })
    return items


# ---------- Part 2b: AI summary WITH references ----------
def summarise_items(items, use_ai=False):
    """
    Summarise the week's items and flag each. Always keeps the source link
    as the reference so you can verify anything you'd act on.
    """
    if use_ai and not USE_AI:
        raise RuntimeError("AI is disabled. Set USE_AI = True only after explicit cost approval.")
    if not use_ai:
        # Free offline mode: no AI, just a tidy digest you can read.
        lines = ["\n=== WEEKLY DIGEST (no-AI mode) ==="]
        for it in collate_items(items):
            flag = it.get("flag", classify_text(f"{it.get('title', '')} {it.get('summary', '')}"))
            lines.append(f"\n{FLAG_EMOJI[flag]}")
            lines.append(f"\n• {it['title']}")
            if it["summary"]:
                lines.append(f"  {it['summary'][:200].strip()}...")
            lines.append(f"  ref: {it['link']}")
        return "\n".join(lines)

    # AI mode: one cheap batched call. Uses a small model to keep cost down.
    from anthropic import Anthropic
    client = Anthropic()  # reads ANTHROPIC_API_KEY from your environment
    bundle = "\n\n".join(
        f"TITLE: {it['title']}\nTEASER: {it['summary']}\nLINK: {it['link']}"
        for it in items
    )
    prompt = (
        "You are helping a trainee financial adviser triage this week's industry "
        "news. For EACH item below, output one line:\n"
        "FLAG | one-sentence summary | LINK\n"
        "FLAG is ACT (changes what an adviser must do), KNOW (useful context), "
        "or NOTE (background/data). Only summarise the teaser given — do not invent "
        "detail or assume anything not present. Always keep the LINK.\n\n"
        f"{bundle}"
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",  # cheap model for routine summarising
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ---------- Part 3: find a free version of a paywalled story ----------
def find_free_version(headline, teaser, free_sources, use_ai=False):
    """
    SAFE paywall handling. Input is ONLY the free headline + teaser (e.g. from
    an RSS feed). This function NEVER touches the locked article. It searches
    your free sources for the same story and returns free links.

    Offline stub returns a search plan you can run manually; AI mode drafts
    search queries. Actual web search you wire to your own search tool/API.
    """
    plan = {
        "topic_from_free_teaser": f"{headline} — {teaser[:120]}",
        "search_these_free_sources": free_sources,
        "note": "Only the publisher's free teaser was used. Locked text never read.",
    }
    if use_ai and not USE_AI:
        raise RuntimeError("AI is disabled. Set USE_AI = True only after explicit cost approval.")
    if not use_ai:
        return plan

    from anthropic import Anthropic
    client = Anthropic()
    prompt = (
        "A paywalled article has this PUBLIC headline and teaser only:\n"
        f"HEADLINE: {headline}\nTEASER: {teaser}\n\n"
        "The user wants to read the same story for free. Write 3 short web-search "
        "queries likely to surface the SAME underlying story on free sources "
        "(regulators, the FAAA, Treasury, ABS, free news). Output only the 3 queries, "
        "one per line. Do not attempt to access the paywalled text."
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    plan["ai_search_queries"] = msg.content[0].text
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Advice Industry Monitor")
    parser.add_argument("--email", action="store_true", help="Email digest instead of printing to stdout")
    parser.add_argument("--preview", action="store_true", help="Write a local HTML preview of the digest to output/digest_preview.html")
    parser.add_argument("--ai", action="store_true", help="Enable AI summarisation (requires ANTHROPIC_API_KEY in .env)")
    args = parser.parse_args()

    # Override config from command line
    if args.ai:
        USE_AI = True

    show_sources()

    # Demo of the digest with a couple of fake items (no network needed):
    demo = [
        {"title": "ASIC bans adviser over SMSF advice",
         "summary": "The regulator cancelled the licence after finding...",
         "link": "https://www.asic.gov.au/example",
         "flag": "ACT"},
        {"title": "Super reform: what the new levy means",
         "summary": "Commentary on the CSLR special levy allocation...",
         "link": "https://www.professionalplanner.com.au/example",
         "flag": "KNOW"},
    ]

    if args.preview:
        from email_sender import _build_html_digest
        preview_dir = Path(__file__).resolve().parent.parent / "output"
        preview_dir.mkdir(exist_ok=True)
        preview_path = preview_dir / "digest_preview.html"
        html = _build_html_digest({"ACT": demo[:1], "KNOW": demo[1:], "NOTE": []}, use_ai=False)
        preview_path.write_text(html, encoding="utf-8")
        print(f"📄 Local preview written to {preview_path}")
    elif args.email or USE_EMAIL:
        from email_sender import send_digest_email
        recipient = os.getenv("EMAIL_ADDRESS")
        if recipient:
            send_digest_email(demo, recipient, use_ai=USE_AI)
        else:
            print("❌ Cannot email: EMAIL_ADDRESS not set in .env")
    else:
        print(summarise_items(demo, use_ai=False))

    print("\n=== PART 3 DEMO (safe paywall handling) ===")
    result = find_free_version(
        "Super reform: what the new levy means",
        "Commentary on the CSLR special levy allocation between sub-sectors...",
        load_sources()[1],
        use_ai=False,
    )
    print(json.dumps(result, indent=2))
