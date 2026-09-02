"""
Industry Update Monitor  —  safe, free-first, no paywall bypassing.

CORE RULE (do not remove): this tool only ever reads content that was
legitimately delivered to you — RSS feeds and free pages the publisher serves
to the public. It NEVER logs in, NEVER fetches text behind a paywall, and
NEVER stores or reconstructs locked content. Feeds in, free sources out.

Parts:
  1. load_sources()          -> your flagged, categorised source list
  2. fetch_feed_items()      -> pull headlines+summaries from a source's RSS
  3. classify_scored()       -> weighted keyword flag + 0-1 confidence, no AI
  4. collate_items()         -> dedupe, filter by age/confidence, prioritise
  5. check_links()           -> confirm every link in the digest resolves
  6. summarise_items()       -> plain-text digest with references
  7. senders                 -> email_sender.py / whatsapp_sender.py

Run:  python src/monitor.py
Deps: pip install feedparser python-dotenv
"""

import json
import os
import re
import argparse
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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
USE_EMAIL = False  # Set to True to email digest; requires EMAIL_ADDRESS and EMAIL_PASSWORD in .env

FLAG_EMOJI = {"ACT": "🔴 ACT", "KNOW": "🟠 KNOW", "NOTE": "🟢 NOTE"}
ALLOWED_ACCESS = {"free", "free_signup"}
ALLOWED_INTAKE = {"email_alert", "email_newsletter", "rss"}
FLAG_ORDER = {"ACT": 0, "KNOW": 1, "NOTE": 2}

# Several publishers (Momentum Media titles, Cloudflare-fronted sites) return
# 403 to feedparser's default agent. A plain browser UA is enough; we still only
# ever request the public feed the publisher chose to serve.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
FETCH_TIMEOUT = 20
DEFAULT_MAX_AGE_DAYS = 14
DEFAULT_MIN_CONFIDENCE = 0.0

# Analytics parameters that break URL-based deduplication without changing the
# page they point at.
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "yclid", "msclkid"}
TRACKING_PREFIXES = ("utm_",)

# Scoring. A term found in the title counts double: headlines describe the
# story, teaser bodies are full of incidental vocabulary.
TITLE_WEIGHT = 2
SOURCE_PRIOR_WEIGHT = 2
ACT_THRESHOLD = 6
KNOW_THRESHOLD = 4

# Patterns are word-bounded on purpose. Bare substring matching flagged
# "Albanese" and "urban" as bans, and "lawyer" and "flawed" as law.
ACT_TERMS = (
    # Regulators, enforcement bodies and their instruments.
    (r"\basic\b", 3),
    (r"\bafca\b", 3),
    (r"\bapra\b", 3),
    (r"\baustrac\b", 3),
    (r"\btpb\b", 3),
    (r"tax practitioners board", 3),
    (r"\bfederal court\b", 3),
    (r"enforceable undertaking", 3),
    (r"infringement notice", 3),
    (r"banning order", 3),
    (r"\bban(s|ned|ning)?\b", 3),
    (r"\bbreach(es|ed|ing)?\b", 3),
    (r"\bdetermination(s)?\b", 3),
    (r"\bpenalt(y|ies)\b", 3),
    (r"\bprosecut\w*", 3),
    (r"\bconvict\w*", 3),
    (r"\bdisqualif\w*", 3),
    (r"\bsanction(s|ed)?\b", 3),
    (r"\bremediation\b", 3),
    (r"\bcancel(s|led|lation)?\b", 2),
    (r"\bsuspend(s|ed|ing|sion)?\b", 2),
    (r"\blicen[cs]e(s|d)?\b", 2),
    (r"\bcourt\b", 2),
    # Things that change what an adviser must actually do.
    (r"\bcompliance\b", 3),
    (r"\bobligation(s)?\b", 3),
    (r"\bdeadline(s)?\b", 3),
    (r"\bmandatory\b", 3),
    (r"\blegislation\b", 3),
    (r"\blegislative\b", 3),
    (r"\brule change(s)?\b", 3),
    (r"exposure draft", 3),
    (r"draft legislation", 3),
    (r"regulatory guide", 3),
    (r"\brg ?\d+\b", 3),
    (r"best interests duty", 3),
    (r"code of ethics", 3),
    (r"fee consent", 3),
    (r"ongoing fee arrangement", 3),
    (r"\bregulator(s|y)?\b", 2),
    (r"\bregulation(s)?\b", 2),
    (r"\bconsultation(s)?\b", 2),
    (r"professional standards", 2),
    (r"\bcpd\b", 2),
    (r"\blev(y|ies)\b", 2),
    # Named Australian advice reform programs.
    (r"\bcslr\b", 3),
    (r"\bdbfo\b", 3),
    (r"\bqar\b", 3),
    (r"\bnca\b", 2),
    # Super and tax settings advisers have to apply.
    (r"division ?296", 3),
    (r"\bdiv ?296\b", 3),
    (r"contribution cap(s)?", 3),
    (r"transfer balance cap", 3),
    (r"preservation age", 3),
    (r"\bsis act\b", 3),
    (r"\blrba(s)?\b", 3),
    (r"limited recourse borrowing", 3),
    (r"super(annuation)? guarantee", 3),
    (r"anti-?hawking", 3),
    (r"design and distribution", 3),
    (r"target market determination", 3),
    (r"\btmd\b", 2),
    (r"tax(ation)? ruling", 3),
    (r"\bruling(s)?\b", 2),
    (r"\brule(s)?\b", 2),
)

KNOW_TERMS = (
    # People moves.
    (r"\bappoint(s|ed|ment|ments)?\b", 3),
    (r"\bhire(s|d)?\b", 3),
    (r"\bjoins\b", 3),
    (r"steps down", 3),
    (r"\bresign\w*", 3),
    (r"\bretirement\b", 3),
    (r"\bdepart(s|ure|ing)?\b", 3),
    (r"chief executive", 3),
    (r"managing director", 3),
    (r"\bceo\b", 3),
    (r"\bchair(man|woman|person)?\b", 3),
    (r"\bnamed as\b", 3),
    (r"\bnames\b", 2),
    # Corporate activity.
    (r"\bacqui(re|res|red|ring|sition|sitions)\b", 3),
    (r"\bmerge(r|rs|s|d)?\b", 3),
    (r"\btakeover\b", 3),
    (r"\bstake\b", 2),
    # Policy and profession context.
    (r"\breform(s|ing)?\b", 3),
    (r"first guardian", 3),
    (r"adviser numbers", 3),
    (r"\bpolicy\b", 2),
    (r"\badvocacy\b", 2),
    (r"\bsubmission(s)?\b", 2),
    (r"\bshield\b", 2),
    (r"\blicensee(s)?\b", 2),
    (r"\bcslr\b", 2),
    (r"\bdbfo\b", 2),
    (r"\bqar\b", 2),
    (r"\bnca\b", 2),
    # Weak background signals.
    (r"\bindustry\b", 1),
    (r"\bcommentary\b", 1),
    (r"\btechnical\b", 1),
    (r"\bstrateg(y|ic)\b", 1),
    (r"\bannounce\w*", 1),
    (r"\bresearch\b", 1),
    (r"\bsurvey\b", 1),
    (r"\breport(s)?\b", 1),
    (r"\bsuper(annuation)?\b", 1),
    (r"\bplatform(s)?\b", 1),
    (r"\bconsumer(s)?\b", 1),
    (r"\brule(s)?\b", 1),
    (r"\bruling(s)?\b", 1),
)

# Marketing and events. These are real items but they never need action, so
# they pull a score down rather than up.
DEMOTE_TERMS = (
    (r"\bwebinar(s)?\b", 3),
    (r"\bconference(s)?\b", 3),
    (r"\bcongress\b", 3),
    (r"\bawards?\b", 3),
    (r"early bird", 3),
    (r"\bregistration(s)?\b", 3),
    (r"\bnomination(s)?\b", 3),
    (r"\bmasterclass\b", 3),
    (r"\broadshow\b", 3),
    (r"\bsponsored\b", 3),
    (r"\bpodcast\b", 2),
)

PROMOTIONAL_TERMS = (
    "unsubscribe", "sponsored", "advertisement", "register now", "limited offer",
)


def _compile(terms):
    return tuple((re.compile(pattern), weight, pattern) for pattern, weight in terms)


_ACT_RULES = _compile(ACT_TERMS)
_KNOW_RULES = _compile(KNOW_TERMS)
_DEMOTE_RULES = _compile(DEMOTE_TERMS)


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


# ---------- Part 3: classification (weighted keywords, no AI) ----------
# Publisher furniture that carries no meaning: photo credits, agency captions
# and the WordPress "The post ... appeared first on ..." footer. These were
# being scored as if they were part of the story and shown as its summary.
BOILERPLATE_PATTERNS = (
    re.compile(r"\bThe post\b.*?\bappeared first on\b.*", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bRead more\b.*$", re.IGNORECASE),
    re.compile(r"\bContinue reading\b.*$", re.IGNORECASE),
    re.compile(r"\[\s*(?:…|\.\.\.)\s*\]"),
    re.compile(r"\bshare this\b.*$", re.IGNORECASE),
)

# A leading credit line: "Image: Studio Zenith/stock.adobe.com.au", "Image:
# Supplied", "Supplied: Praemium", "Image by onephoto/stock.adobe.com". Each
# rule is anchored on something unambiguous — a stock-photo domain, or a
# marker word followed by a colon — so none of them can eat real prose.
# A photo-agency domain is unambiguous, so no marker word is required: the
# credit may read "Bits and Splits/adobe.stock.com" with no "Image:" at all.
CREDIT_DOMAIN = re.compile(
    r"^\s*[^.!?]{0,50}?"
    r"(?:stock\.adobe\.com(?:\.au)?|adobe\.stock\.com|shutterstock[\w.]*"
    r"|gettyimages[\w.]*|istockphoto[\w.]*|unsplash\.com)\b\S*\s*",
    re.IGNORECASE,
)
# "Supplied" is only a credit when a marker word introduces it — plenty of real
# sentences contain the word ("the company supplied documents to ASIC").
CREDIT_SUPPLIED = re.compile(
    r"^\s*(?:image|images|photo|picture|pic|source|credit)s?\b[^.!?]{0,30}?supplied\b\S*\s*",
    re.IGNORECASE,
)
CREDIT_MARKER = re.compile(
    r"^\s*(?:image|images|photo|picture|pic|supplied|source|credit)s?\s*[:\-–]\s*",
    re.IGNORECASE,
)
# "Supplied: Praemium Praemium is betting..." leaves the subject doubled.
REPEATED_LEAD_WORD = re.compile(r"^([A-Z][\w'’-]*)\s+\1\b")


def clean_teaser(text):
    """Strip publisher furniture from a public teaser, keeping the story."""
    cleaned = strip_html(text)
    for pattern in BOILERPLATE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = CREDIT_DOMAIN.sub("", cleaned, count=1)
    cleaned = CREDIT_SUPPLIED.sub("", cleaned, count=1)
    cleaned = CREDIT_MARKER.sub("", cleaned, count=1)
    cleaned = REPEATED_LEAD_WORD.sub(r"\1", cleaned, count=1)
    return re.sub(r"\s+", " ", cleaned).strip(" -–—:;,")


def _sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def summarise_teaser(title, teaser, max_sentences=2, max_chars=320):
    """
    Build a readable summary from the publisher's own teaser.

    Whole sentences only, chosen for overlap with the headline — the digest
    used to show the first 200 characters and cut mid-word.
    """
    cleaned = clean_teaser(teaser)
    if not cleaned:
        return ""
    sentences = _sentences(cleaned)
    if not sentences:
        return ""

    title_terms = set(re.findall(r"[a-z]{4,}", (title or "").lower()))
    ranked = sorted(
        enumerate(sentences),
        key=lambda pair: (
            -sum(term in pair[1].lower() for term in title_terms),
            pair[0],
        ),
    )
    chosen = sorted(index for index, _ in ranked[:max_sentences])

    summary = ""
    for index in chosen:
        candidate = f"{summary} {sentences[index]}".strip()
        if summary and len(candidate) > max_chars:
            break
        summary = candidate
    if not summary:
        summary = sentences[0]
    if len(summary) > max_chars:
        # Trim to the last whole word rather than slicing a word in half.
        summary = summary[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    elif not summary.endswith(("…", ".", "!", "?", "”", '"', ")")):
        # The publisher's teaser was itself cut off (a "[…] The post ..." tail).
        summary += "…"
    return summary


def strip_html(text):
    """Flatten a publisher's HTML teaser to plain text."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _score(title, body, rules):
    """Score one term list, counting title hits at TITLE_WEIGHT."""
    title_text = (title or "").lower()
    body_text = (body or "").lower()
    total = 0
    matched = []
    for pattern, weight, label in rules:
        in_title = pattern.search(title_text) is not None
        in_body = pattern.search(body_text) is not None
        if not (in_title or in_body):
            continue
        total += weight * (TITLE_WEIGHT if in_title else 1)
        matched.append(label)
    return total, matched


def _confidence(winner, threshold, loser):
    """
    How much to trust this flag, on 0.5-1.0.

    Two things make a call trustworthy: how far past the threshold the winning
    score got (strength), and how far clear of the runner-up it stayed
    (separation). An item that scrapes in at threshold with the other class
    right behind it lands near 0.5 and should be read before it is relied on.
    """
    strength = min(1.0, max(0.0, (winner - threshold) / (threshold * 3)))
    separation = 1.0 if loser <= 0 else max(0.0, 1.0 - loser / winner)
    return 0.5 + (0.35 * strength) + (0.15 * separation)


def classify_scored(title, summary="", source_flag=None):
    """
    Flag an item and say how confident we are, using public text only.

    Returns a dict with the flag, a 0-1 confidence, both raw scores and the
    patterns that fired — so a low-confidence call can be inspected rather
    than just trusted.
    """
    act_score, act_matched = _score(title, summary, _ACT_RULES)
    know_score, know_matched = _score(title, summary, _KNOW_RULES)
    demote_score, demote_matched = _score(title, summary, _DEMOTE_RULES)

    # The configured source flag is a prior, not a verdict: it nudges the
    # score it agrees with, it never overrides what the words say.
    if source_flag == "ACT":
        act_score += SOURCE_PRIOR_WEIGHT
    elif source_flag == "KNOW":
        know_score += SOURCE_PRIOR_WEIGHT

    act_score = max(0, act_score - demote_score)
    know_score = max(0, know_score - demote_score)

    if act_score >= ACT_THRESHOLD:
        flag = "ACT"
        confidence = _confidence(act_score, ACT_THRESHOLD, know_score)
    elif know_score >= KNOW_THRESHOLD:
        flag = "KNOW"
        confidence = _confidence(know_score, KNOW_THRESHOLD, act_score)
    else:
        flag = "NOTE"
        # For NOTE, confidence is confidence in "this needs no action": an item
        # that nearly cleared a threshold is a low-confidence NOTE.
        near_miss = max(act_score / ACT_THRESHOLD, know_score / KNOW_THRESHOLD)
        confidence = min(1.0, max(0.0, 1.0 - near_miss))

    return {
        "flag": flag,
        "confidence": round(confidence, 2),
        "act_score": act_score,
        "know_score": know_score,
        "matched": act_matched + know_matched,
        "demoted_by": demote_matched,
    }


def classify_text(text, source_flag=None):
    """Assign a cautious priority using supplied public text only."""
    return classify_scored(text, "", source_flag=source_flag)["flag"]


def classify_email(email):
    """Assign a cautious priority using only the received email's text."""
    return classify_scored(
        email.get("subject", ""),
        strip_html(email.get("body", "")),
    )["flag"]


# ---------- Part 5: link hygiene ----------
def normalise_link(url):
    """Strip tracking noise so the same article from two feeds dedupes as one."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
        and not key.lower().startswith(TRACKING_PREFIXES)
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        path,
        parsed.params,
        urlencode(query),
        "",  # fragments never change the article
    ))


def check_link(url, timeout=FETCH_TIMEOUT):
    """HEAD-check one public URL, falling back to GET where HEAD is refused."""
    if not url:
        return {"ok": False, "status": None, "url": url, "error": "no link"}
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT}, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return {"ok": True, "status": response.status, "url": response.url, "error": None}
        except urllib.error.HTTPError as error:
            # 403/405 usually means "not via HEAD", so try GET before judging.
            if method == "HEAD" and error.code in {403, 405, 501}:
                continue
            return {"ok": False, "status": error.code, "url": url, "error": str(error.reason)}
        except Exception as error:  # network, DNS, TLS, timeout
            if method == "HEAD":
                continue
            return {"ok": False, "status": None, "url": url, "error": type(error).__name__}
    return {"ok": False, "status": None, "url": url, "error": "unreachable"}


def check_links(items, workers=8, timeout=FETCH_TIMEOUT):
    """Annotate items in place with link_ok/link_status; adopt redirect targets."""
    if not items:
        return items
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda item: check_link(item.get("link", ""), timeout), items))
    for item, result in zip(items, results):
        item["link_ok"] = result["ok"]
        item["link_status"] = result["status"]
        if result["ok"] and result["url"]:
            item["link"] = result["url"]
    return items


# ---------- Part 4: collation ----------
def _fingerprint(title):
    """Loose title key so the same wire story from two outlets collapses."""
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()[:70]


def _item_timestamp(item):
    published = item.get("published")
    if isinstance(published, datetime):
        return published
    return None


def collate_items(
    items,
    max_items=50,
    min_confidence=DEFAULT_MIN_CONFIDENCE,
    max_age_days=None,
    require_working_link=False,
    flags=None,
):
    """Deduplicate, filter and prioritise RSS-style items without using AI."""
    if max_items < 1 or max_items > 100:
        raise ValueError("max_items must be between 1 and 100")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be between 0.0 and 1.0")

    cutoff = None
    if max_age_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    unique = {}
    for item in items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        link = normalise_link(item.get("link", ""))
        key = link or _fingerprint(title) or summary[:120].lower()
        if not key:
            continue

        if require_working_link and item.get("link_ok") is False:
            continue

        published = _item_timestamp(item)
        if cutoff and published and published < cutoff:
            continue

        # Always classify from the item's own words. The source's flag is only
        # a prior — before, it was written straight over the top of this and
        # the classifier never ran on feed items at all.
        classify_body = item.get("teaser") or summary
        verdict = classify_scored(title, classify_body, source_flag=item.get("source_flag"))
        if flags and verdict["flag"] not in flags:
            continue
        if verdict["confidence"] < min_confidence:
            continue

        enriched = dict(item)
        enriched.update({
            "flag": verdict["flag"],
            "confidence": verdict["confidence"],
            "matched_terms": verdict["matched"],
        })

        existing = unique.get(key)
        if existing is None or enriched["confidence"] > existing["confidence"]:
            unique[key] = enriched

    return sorted(
        unique.values(),
        key=lambda item: (
            FLAG_ORDER.get(item["flag"], 3),
            -item["confidence"],
            -(_item_timestamp(item) or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
        ),
    )[:max_items]


def _clean_email_text(text):
    """Drop tags and promotional lines. Line breaks are kept until after the
    promotional filter runs — collapsing them first merges a footer's
    "Unsubscribe" into the whole body and discards it all."""
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
    sentences = [s for s in sentences if not any(t in s.lower() for t in PROMOTIONAL_TERMS)]
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
    verdict = classify_scored(email.get("subject", ""), strip_html(email.get("body", "")))
    result = {
        "flag": verdict["flag"],
        "confidence": verdict["confidence"],
        "summary": extractive_summary(email),
        "source": email.get("source", email.get("sender", "unknown")),
        "link": email.get("link", ""),
    }
    if verdict["flag"] == "ACT":
        result["instruction"] = "Read the original source before relying on this."
    return result


def format_assessment(assessments):
    """Format assessments as readable bullet points grouped by priority."""
    lines = ["\n=== EMAIL ASSESSMENT (no AI) ==="]
    for item in sorted(assessments, key=lambda value: FLAG_ORDER[value["flag"]]):
        confidence = item.get("confidence")
        header = FLAG_EMOJI[item["flag"]]
        if confidence is not None:
            header += f"  (confidence {confidence:.0%})"
        lines.append(f"\n{header}")
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
        rss = s["rss"] or "(no RSS — intake is {})".format(s.get("intake", "manual"))
        print(f"{FLAG_EMOJI[s['flag']]:9} | {s['access']:12} | {s['name']}")
        print(f"            feed: {rss}")


# ---------- Part 2a: fetch (RSS only — legitimate intake) ----------
def _fetch_feed_bytes(url, timeout=FETCH_TIMEOUT):
    """Fetch the raw feed with an explicit agent and timeout."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _entry_published(entry):
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def fetch_feed_items(source, limit=10, timeout=FETCH_TIMEOUT):
    """Read an explicitly configured public RSS feed."""
    import feedparser  # imported here so Part 1 works without it installed
    feed = feedparser.parse(_fetch_feed_bytes(validate_feed_source(source), timeout))
    items = []
    for entry in feed.entries[:limit]:
        title = strip_html(entry.get("title", ""))
        # 'summary' is the teaser the publisher CHOOSES to make public.
        # We use only this. We never fetch the full/locked article body.
        teaser = clean_teaser(entry.get("summary", ""))
        items.append({
            "title": title,
            "summary": summarise_teaser(title, teaser),
            "teaser": teaser[:600],
            "link": entry.get("link", ""),
            "published": _entry_published(entry),
            "source_name": source.get("name", ""),
            "source_flag": source.get("flag"),
        })
    return items


def fetch_all_sources(sources, limit=15, timeout=FETCH_TIMEOUT):
    """Fetch every source that has a configured feed, reporting failures."""
    items, failures = [], []
    for source in sources:
        if not source.get("rss"):
            continue
        try:
            items.extend(fetch_feed_items(source, limit=limit, timeout=timeout))
        except Exception as error:
            failures.append((source.get("name", "(unnamed)"), f"{type(error).__name__}: {error}"))
    return items, failures


# ---------- Part 5: digest ----------
def summarise_items(items, **collate_kwargs):
    """Render the collated digest as plain text, with references kept."""
    lines = ["\n=== WEEKLY DIGEST ==="]
    current_flag = None
    for it in collate_items(items, **collate_kwargs):
        if it["flag"] != current_flag:
            current_flag = it["flag"]
            lines.append(f"\n{FLAG_EMOJI[current_flag]}")
        lines.append(f"\n• {it['title']}  [{it['confidence']:.0%} confidence]")
        if it["summary"]:
            lines.append(f"  {it['summary']}")
        if it.get("source_name"):
            lines.append(f"  via: {it['source_name']}")
        status = "" if it.get("link_ok") is not False else "  ⚠️ link did not resolve"
        lines.append(f"  ref: {it['link']}{status}")
    return "\n".join(lines)


def _load_email_sender():
    try:
        from src import email_sender
    except ImportError:
        import email_sender
    return email_sender


def _load_whatsapp_sender():
    try:
        from src import whatsapp_sender
    except ImportError:
        import whatsapp_sender
    return whatsapp_sender


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Industry Update Monitor")
    parser.add_argument("--email", action="store_true", help="Email digest instead of printing to stdout")
    parser.add_argument("--preview", action="store_true", help="Write a local HTML preview of the digest to output/digest_preview.html")
    parser.add_argument("--whatsapp", action="store_true", help="Send the digest as a WhatsApp newsletter (previews if Twilio is unconfigured)")
    parser.add_argument("--whatsapp-to", help="WhatsApp recipient in +614... form; defaults to WHATSAPP_TO in .env")
    parser.add_argument("--per-flag", type=int, default=6, help="Max items per flag in the WhatsApp newsletter")
    parser.add_argument("--days", type=int, default=DEFAULT_MAX_AGE_DAYS, help="Drop items older than this many days (0 = no limit)")
    parser.add_argument("--min-confidence", type=float, default=DEFAULT_MIN_CONFIDENCE, help="Drop items whose flag confidence is below this (0.0-1.0)")
    parser.add_argument("--flags", default="ACT,KNOW,NOTE", help="Comma-separated flags to include, e.g. ACT,KNOW")
    parser.add_argument("--limit", type=int, default=50, help="Maximum items in the digest (1-100)")
    parser.add_argument("--no-check-links", action="store_true", help="Skip the link health check (faster, but dead links may ship)")
    parser.add_argument("--sources", action="store_true", help="Print the source list before the digest")
    args = parser.parse_args()

    if args.sources:
        show_sources()

    sources, _ = load_sources()
    items, failures = fetch_all_sources(sources, limit=15)
    for name, error in failures:
        print(f"⚠️  Error fetching {name}: {error}")

    if not items:
        raise SystemExit(
            "❌ No items fetched from any configured feed. Check data/sources.json — "
            "every source needs a live 'rss' URL, and the run needs network access."
        )

    print(f"📥 Fetched {len(items)} items from {len(sources) - len(failures)} sources.")

    if not args.no_check_links:
        check_links(items)
        broken = sum(1 for item in items if item.get("link_ok") is False)
        if broken:
            print(f"🔗 {broken} of {len(items)} links did not resolve and were dropped.")

    wanted_flags = {f.strip().upper() for f in args.flags.split(",") if f.strip()}
    unknown = wanted_flags - set(FLAG_ORDER)
    if unknown:
        raise SystemExit(f"❌ Unknown flag(s): {', '.join(sorted(unknown))}. Choose from ACT, KNOW, NOTE.")

    collate_kwargs = {
        "max_items": args.limit,
        "flags": wanted_flags,
        "min_confidence": args.min_confidence,
        "max_age_days": args.days or None,
        "require_working_link": not args.no_check_links,
    }
    digest_items = collate_items(items, **collate_kwargs)
    counts = {flag: sum(1 for i in digest_items if i["flag"] == flag) for flag in FLAG_ORDER}
    print(f"🏷️  Digest: {len(digest_items)} items — ACT {counts['ACT']}, KNOW {counts['KNOW']}, NOTE {counts['NOTE']}")

    if args.preview:
        email_sender = _load_email_sender()
        preview_dir = Path(__file__).resolve().parent.parent / "output"
        preview_dir.mkdir(exist_ok=True)
        preview_path = preview_dir / "digest_preview.html"
        grouped = {flag: [i for i in digest_items if i["flag"] == flag] for flag in FLAG_ORDER}
        html = email_sender._build_html_digest(grouped)
        preview_path.write_text(html, encoding="utf-8")
        print(f"📄 Local preview written to {preview_path}")
        if args.whatsapp:
            _load_whatsapp_sender().send_whatsapp_digest(
                digest_items, to_number=args.whatsapp_to, per_flag_limit=args.per_flag
            )
    elif args.email or USE_EMAIL:
        email_sender = _load_email_sender()
        recipient = os.getenv("EMAIL_ADDRESS")
        if recipient:
            email_sender.send_digest_email(digest_items, recipient)
        else:
            print("❌ Cannot email: EMAIL_ADDRESS not set in .env")
    elif args.whatsapp:
        whatsapp_sender = _load_whatsapp_sender()
        whatsapp_sender.send_whatsapp_digest(
            digest_items, to_number=args.whatsapp_to, per_flag_limit=args.per_flag
        )
    else:
        print(summarise_items(items, **collate_kwargs))
