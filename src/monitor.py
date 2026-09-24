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
  7. senders                 -> email_sender.py / telegram_sender.py (whatsapp_sender.py retired)

Run:  python src/monitor.py
Deps: pip install feedparser python-dotenv
"""

import json
import os
import re
import argparse
import itertools
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
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
    r"(?:stock\.adobe\.com(?:\.au)?|adobe\.stock\.com|adobestock[\w.]*|shutterstock[\w.]*"
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


# What a finished sentence looks like. A teaser that ends any other way was cut
# by the publisher.
SENTENCE_ENDINGS = ("…", ".", "!", "?", "”", '"', ")")


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

    # A WordPress teaser stops mid-clause: "...bringing the total down to
    # 15,156 for the [&#8230;]". Once the marker is stripped, the last
    # "sentence" is half a clause. Drop it when a whole sentence remains —
    # showing "for the…" tells the reader nothing. If the fragment is all the
    # publisher gave us, keep it: half a lead still beats an empty summary.
    if len(sentences) > 1 and not sentences[-1].endswith(SENTENCE_ENDINGS):
        sentences = sentences[:-1]

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
    elif not summary.endswith(SENTENCE_ENDINGS):
        # The publisher's teaser was itself cut off (a "[…] The post ..." tail).
        summary += "…"
    return summary


# Elements whose text is not part of the story. Every Momentum Media title
# (ifa, Money Management, SMSF Adviser) opens its RSS teaser with a <figure>
# holding the article photo and a <figcaption> credit; flattening the tags
# alone left the caption as the story's first words — "SMSF property Hogan
# said…", "CPA Australia Richard Webb…", "ASIC An ASIC review…". The caption is
# a separate element, so remove it with its contents rather than guessing at
# where a credit ends in the plain text.
ELEMENT_NOISE = re.compile(
    r"<(figcaption|script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)


def strip_html(text):
    """Flatten a publisher's HTML teaser to plain text."""
    without_noise = ELEMENT_NOISE.sub(" ", text or "")
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", without_noise))).strip()


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


# A site that answers these to a HEAD request is refusing the polite question,
# not saying the page is gone, so the link is left unchecked rather than dead.
HEAD_REFUSED = {401, 403, 405, 429, 501}


def check_link(url, timeout=FETCH_TIMEOUT):
    """
    HEAD-check one public URL: does the page exist, without downloading it.

    HEAD only, never GET. A GET would open the article page, which
    SAFEGUARDS.md section A rules out even when nothing is read or kept. It
    used to fall back to GET when a site refused HEAD; now a refusal, or no
    answer at all, leaves the link unchecked (ok None), which keeps the item.
    Only a clear "not found" marks it dead. Redirects stay HEAD requests.
    """
    if not url:
        return {"ok": False, "status": None, "url": url, "error": "no link"}
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"ok": True, "status": response.status, "url": response.url, "error": None}
    except urllib.error.HTTPError as error:
        if error.code in HEAD_REFUSED or error.code >= 500:
            return {"ok": None, "status": error.code, "url": url, "error": "not checked"}
        return {"ok": False, "status": error.code, "url": url, "error": str(error.reason)}
    except Exception as error:  # network, DNS, TLS, timeout
        return {"ok": None, "status": None, "url": url, "error": type(error).__name__}


def is_checkable_link(item):
    """
    Whether this item's link is a public page a link check can reach.

    A newsletter item links back to the message in your own mailbox, which
    redirects to a Google login for any client but your browser. Checking it
    would mark every newsletter dead and drop it from the digest.
    """
    return item.get("intake") != "email"


def check_links(items, workers=8, timeout=FETCH_TIMEOUT):
    """Annotate items in place with link_ok/link_status; adopt redirect targets."""
    if not items:
        return items
    checkable = [item for item in items if is_checkable_link(item)]
    if not checkable:
        return items
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda item: check_link(item.get("link", ""), timeout), checkable))
    for item, result in zip(checkable, results):
        item["link_ok"] = result["ok"]
        item["link_status"] = result["status"]
        if result["ok"] and result["url"]:
            item["link"] = result["url"]
    return items


# ---------- Part 4: collation ----------
# Topic labels for the web dashboard. Order matters only for ties: a
# regulatory label wins a draw, matching the ACT-first ordering elsewhere.
# Where an item goes when no rule scores. Named as the leftovers rather than
# as a subject, because it is the biggest bucket and a reader should see it as
# "no rule matched this yet", not as a theme to read end to end.
FALLBACK_TOPIC = "General"

TOPIC_RULES = (
    ("Compliance", re.compile(r"\bcompliance\b|\bobligation|\bbreach|code of ethics|best interests|fee consent|\bcpd\b|professional standards|\bgovernance\b", re.I)),
    ("Regulation", re.compile(r"\basic\b|\bafca\b|\bapra\b|\baustrac\b|legislation|regulator|consultation|\bcslr\b|\bdbfo\b|\bqar\b|\bnca\b|\blev(y|ies)\b|\btribunal\b|\bbann(ed|ing)\b|\bbans\b", re.I)),
    ("Super & tax", re.compile(r"division ?296|\bdiv ?296\b|\blrba|\bsmsf\b|super(annuation)?|contribution cap|transfer balance|\bato\b|preservation age|\bpension|\bretiree|retirement (income|balance|savings|phase|spending)", re.I)),
    ("Insurance", re.compile(r"\binsurance\b|\binsurer(s)?\b|\btpd\b|life compan|\bclaims?\b|risk advice", re.I)),
    # "retirement" used to be here and was the single worst term in the file:
    # it means a person leaving a job AND the whole subject of retirement
    # income, so four stories about retirement balances and retirees were
    # filed under staff changes. A departure is reported as "retires" or
    # "steps down"; the noun belongs to Super & tax.
    ("Key personnel movements", re.compile(r"\bappoint|\bhire|\bjoins\b|steps down|\bresign|\bretir(es|ing|ed)\b|\bdeparture|\bsuccession\b|\bexits\b|adds? .{0,25}\bteam\b|chief executive|\bceo\b|\bchair", re.I)),
    ("Business", re.compile(r"\bacqui|\bmerge|takeover|\bstake\b|licensee|platform", re.I)),
    # Markets and product news: mostly NOTE-level background, and the largest
    # thing that had no rule at all. Worth its own label precisely so it can be
    # skipped — an adviser reading for obligations does not need the ETF count.
    ("Markets & investing", re.compile(r"\betf\b|\bfunds? manager|managed portfolio|managed fund|private (credit|asset)|outflow|inflow|nasdaq|\basx\b|equit(y|ies) market|listed .{0,12}trust|tokenis|index fund|asset class|billionaire|\bmarkets?\b|\binvestors?\b|\bai boom\b|long-term growth", re.I)),
    # What an adviser charges and how. Distinct from Business (who owns whom)
    # and from Compliance (fee consent, which is an obligation).
    ("Fees & pricing", re.compile(r"pricing of advice|asset-based fee|advice fees|fee model|cost of advice|price for complexity|fee structure", re.I)),
    # Running the practice, and the software for it.
    ("Practice & technology", re.compile(r"digital advice|practice management|advice tech|\bsoftware\b|\bdelegate\b|workflow|paraplann", re.I)),
)


def topic_for(title, summary=""):
    """
    Label an item for dashboard grouping.

    Scored, not first-match. The rules used to be checked in declaration order
    and the first hit won, so "ASIC zeroes in on recurring compliance
    breaches" was filed under Super & tax because its teaser happened to
    mention superannuation advice. A term in the headline counts double, the
    same rule the flag classifier uses: the headline describes the story.
    """
    title_text = title or ""
    body = summary or ""
    best_label, best_score = FALLBACK_TOPIC, 0
    for label, pattern in TOPIC_RULES:
        score = TITLE_WEIGHT * len(pattern.findall(title_text)) + len(pattern.findall(body))
        if score > best_score:
            best_label, best_score = label, score
    return best_label


def _fingerprint(title):
    """Loose title key so the same wire story from two outlets collapses."""
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()[:70]


def _outranks(candidate, existing):
    """
    Decide which copy of the same story the digest keeps.

    Flag first, confidence second. The two confidences are not on one scale:
    a pure-background NOTE scores 1.0 ("confidently nothing to do") while an
    ACT that just clears its threshold scores ~0.6. Ranking on confidence
    alone let the NOTE-worded copy of a syndicated story silently replace the
    copy that read as ACT — the one failure archive/PRD.md calls the real cost.
    """
    candidate_rank = FLAG_ORDER.get(candidate.get("flag"), 3)
    existing_rank = FLAG_ORDER.get(existing.get("flag"), 3)
    if candidate_rank != existing_rank:
        return candidate_rank < existing_rank
    return candidate["confidence"] > existing["confidence"]


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
        if existing is None or _outranks(enriched, existing):
            unique[key] = enriched

    return sorted(
        unique.values(),
        key=lambda item: (
            FLAG_ORDER.get(item["flag"], 3),
            -item["confidence"],
            -(_item_timestamp(item) or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
        ),
    )[:max_items]


def _is_promotional(text):
    return any(term in text.lower() for term in PROMOTIONAL_TERMS)


def _clean_email_text(text):
    """
    Drop tags and promotional text from a received newsletter.

    Filtered a sentence at a time, within each line. Line breaks are kept until
    after the filter runs — collapsing them first merges a footer's
    "Unsubscribe" into the whole body and discards it all — but dropping the
    whole line had the same failure on a one-line body: a newsletter whose
    single paragraph ended "Unsubscribe here." summarised to nothing.
    """
    text = unescape(re.sub(r"<[^>]+>", " ", text or ""))
    kept = []
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if not cleaned:
            continue
        wanted = [part for part in _sentences(cleaned) if not _is_promotional(part)]
        if wanted:
            kept.append(" ".join(wanted))
    return " ".join(kept)


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


# ---------- Part 2b: newsletters (Gmail label — legitimate intake) ----------
# Four configured sources have no feed at all, two of them ACT-flagged product
# technical services. They arrive in the inbox, so the digest never saw them:
# gmail_dry_run.py printed an assessment to the terminal and stopped there.


def match_source_for_sender(sender, sources):
    """
    Find the configured source a newsletter came from, by name.

    Deliberately literal: the configured source name (or its distinctive first
    word) must appear in the sender line. A guess here would attach the wrong
    ACT prior to somebody's marketing email.
    """
    haystack = (sender or "").lower()
    if not haystack:
        return None
    best = None
    for source in sources or []:
        name = (source.get("name") or "").lower()
        if not name:
            continue
        if name in haystack:
            return source
        first_word = name.split()[0]
        # Two letters is not a match — "FS" would hit half the internet.
        if len(first_word) > 3 and first_word in haystack and best is None:
            best = source
    return best


def email_to_item(email, sources=None):
    """Convert one legitimately received newsletter into a digest item."""
    source = match_source_for_sender(email.get("sender") or email.get("source"), sources)
    published = None
    received = email.get("received")
    if received:
        try:
            published = datetime.fromisoformat(received)
        except (TypeError, ValueError):
            published = None
    if published is not None and published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)

    subject = email.get("subject", "")
    teaser = extractive_summary(email)
    return {
        "title": subject,
        "summary": summarise_teaser(subject, teaser) or teaser,
        "teaser": teaser[:600],
        "link": email.get("link", ""),
        "published": published,
        "source_name": (source or {}).get("name") or email.get("sender", "Newsletter"),
        "source_flag": (source or {}).get("flag"),
        "intake": "email",
    }


def fetch_gmail_items(sources=None, label=None, max_messages=25, newer_than_days=14,
                      credentials_path="credentials.json", token_path="token.json"):
    """
    Read the configured Gmail label and return digest items.

    Read-only, one label, no writes — the restrictions live in gmail_reader.
    Raises a clear error rather than a traceback when Gmail is not set up,
    because Gmail access is opt-in and must stay that way.
    """
    try:
        from src import gmail_reader
    except ImportError:
        import gmail_reader

    if not Path(credentials_path).exists():
        raise SystemExit(
            f"❌ Gmail is not set up: no {credentials_path}. See SETUP.md Part 4. "
            "Nothing else about the run needs it — drop --gmail to skip."
        )

    service = gmail_reader.build_gmail_service(credentials_path, token_path)
    emails = gmail_reader.read_label(
        service,
        label_name=label or gmail_reader.LABEL_NAME,
        max_messages=max_messages,
        newer_than_days=newer_than_days,
    )
    return [email_to_item(email, sources) for email in emails]


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
# How much of a feed's own article text to keep for summarising.
#
# Most publishers put the full story in content:encoded — part of the feed
# they generate and serve on purpose, so reading it fetches nothing and visits
# no article page. Capped anyway: a briefing is pasted into a chat window, and
# 9,000 characters an item would blow the paste long before fifteen items.
# The first few paragraphs carry the news; the rest is background.
# Raised from 1,500 on 23 Sep 2026 so the local model reads the whole article
# the feed carries, not its opening paragraph. Only the local model gets all of
# it: pastes for a chat window are cut to PASTE_BODY_LIMIT in format_briefing.
FEED_BODY_LIMIT = 12000
PASTE_BODY_LIMIT = 3000


def _trim_to_sentence(text, limit):
    """Cut to `limit`, backing up to the last finished sentence if there is one."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    # Only back up to a sentence if a reasonable amount survives; otherwise a
    # single long opening paragraph would be thrown away entirely.
    return cut[:end + 1] if end > limit * 0.4 else cut.rstrip() + "…"


def feed_body(entry):
    """
    The article text the publisher put in their own feed, if any.

    This is content:encoded, not the article page: nothing is fetched, no
    paywall is approached, and a publisher who does not want it there does not
    put it there. SAFEGUARDS.md section A permits it explicitly.
    """
    for block in entry.get("content") or []:
        value = block.get("value") if isinstance(block, dict) else None
        if not value:
            continue
        cleaned = clean_teaser(value)
        if cleaned:
            return _trim_to_sentence(cleaned, FEED_BODY_LIMIT)
    return ""


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
        # The feed's own article text where the publisher supplies it, the
        # teaser where they do not. Recorded either way so a reader can tell
        # which they are looking at.
        body = feed_body(entry)
        items.append({
            "title": title,
            "summary": summarise_teaser(title, teaser),
            "teaser": teaser[:600],
            "brief_text": body or teaser[:600],
            "body_source": "feed_content" if body else "feed_summary",
            "link": entry.get("link", ""),
            "published": _entry_published(entry),
            "source_name": source.get("name", ""),
            "source_flag": source.get("flag"),
            "intake": "rss",
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


def _bibliography(items, sources=None):
    """
    One entry per source that actually contributed an item.

    The dashboard used to build its bibliography from item links, which listed
    the same publisher once per article and pointed "Visit" at a single story.
    A bibliography is a list of the publications consulted, so it is built from
    the source list and carries the publisher's own home page.
    """
    homes = {s.get("name", ""): s.get("home", "") for s in (sources or [])}
    counts = {}
    for item in items:
        name = item.get("source_name", "")
        if name:
            counts[name] = counts.get(name, 0) + 1
    return [
        {"name": name, "home": homes.get(name, ""), "count": counts[name]}
        for name in sorted(counts)
    ]


def export_json(items, path, sources=None):
    """Write the digest as JSON for the web dashboard to read."""
    path = Path(path)
    kept = _existing_summaries(path)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # The dashboard groups and downloads by category, so it needs the same
        # label order the classifier used. Publishing it here means the two
        # cannot drift the way a hardcoded copy in TypeScript would.
        "topics": list(TOPIC_LABELS),
        "sources": _bibliography(items, sources),
        # The glossary travels with the digest so a deployed dashboard, which
        # cannot see data/, still explains its terms.
        "glossary": load_glossary(),
        "items": [],
    }
    for item in items:
        item_id = normalise_link(item.get("link", "")) or item.get("title", "")
        exported = {
            "id": item_id,
            "ref": summary_ref(item.get("link", ""), item.get("title", "")),
            "title": item.get("title", ""),
            "teaser": item.get("summary", ""),
            # The fuller teaser, for summarising. "teaser" above is the
            # two-sentence display version the dashboard shows on a card;
            # exporting only that quietly discarded up to two thirds of what
            # the feed gave us, so a briefing carried ~33 words an item and
            # the summaries that came back were one-liners.
            "brief_text": item.get("brief_text") or item.get("teaser") or item.get("summary", ""),
            # Where that text came from: the publisher's own feed content, or
            # just their teaser. Never an article page — nothing fetches one.
            "body_source": item.get("body_source", "feed_summary"),
            "link": item.get("link", ""),
            "source_name": item.get("source_name", ""),
            "intake": item.get("intake", "rss"),
            "flag": item.get("flag", "NOTE"),
            "topic": topic_for(item.get("title", ""), item.get("summary", "")),
            "confidence": item.get("confidence"),
            "is_read": False,
            "created_at": (
                item["published"].isoformat()
                if isinstance(item.get("published"), datetime)
                else datetime.now(timezone.utc).isoformat()
            ),
            "ai_summary": None,
            "ai_source": None,
            "ai_generated_at": None,
        }
        # A summary you wrote by hand survives the next fetch. Without this,
        # re-running --json every week silently threw away the work of pasting
        # the briefing into a web AI tool.
        exported.update(kept.get(item_id, {}))
        payload["items"].append(exported)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def attach_saved_summaries(items, digest_path):
    """
    Put summaries already recorded in the digest back onto freshly fetched items.

    IMPROVEMENTS.md item 4. A run that emails or WhatsApps the digest fetches
    the feeds again, and those items carry no summary — so the work of pasting
    a briefing into a model reached the dashboard and nothing else. Matching is
    on the same id `export_json` writes, the normalised link.

    Returns the number of items that gained one. Missing or unreadable digest
    is not an error: there is simply nothing saved yet.
    """
    kept = _existing_summaries(digest_path)
    if not kept:
        return 0
    attached = 0
    for item in items:
        saved = kept.get(normalise_link(item.get("link", "")) or item.get("title", ""))
        if saved and saved.get("ai_summary"):
            item.update(saved)
            attached += 1
    return attached


def _existing_summaries(path):
    """Summaries already recorded in the digest at this path, keyed by item id."""
    try:
        previous = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    kept = {}
    for item in previous.get("items", []):
        if item.get("ai_summary"):
            kept[item.get("id")] = {
                "ai_summary": item["ai_summary"],
                "ai_source": item.get("ai_source"),
                "ai_generated_at": item.get("ai_generated_at"),
            }
    return kept


# ---------- Part 6: the manual AI round trip ----------
# Phase 3 without an API key: the tool writes a briefing, you paste it into a
# web AI tool, and you paste the reply back. Section D of SAFEGUARDS.md is the
# prompt, verbatim, with an ID added so the reply can be matched to an item.
# When an API key is eventually justified, only the middle step changes.
BRIEF_PROMPT = """You are helping a trainee financial adviser triage this week's Australian
advice-industry news. You will be given items, each with an ID, a TITLE, a public TEASER, and a
LINK. For each item output one line: `ID | FLAG | one-sentence summary | LINK`. FLAG is ACT
(changes what an adviser must do), KNOW (useful context), or NOTE (background/data). Rules:
summarise ONLY from the teaser given; never invent detail or add facts not present; if the teaser
is too thin, write "thin — open source"; always keep the ID and the LINK unchanged; do not attempt
to access anything beyond the text provided."""

# The second pass. One prompt cannot do triage and detail: "one line each,
# only from the teaser" is right for sorting fifty items and guarantees
# one-liners, which is exactly what you do not want on the handful that
# matter. So the triage prompt above is left alone and this one is used on a
# narrowed set, with the same output shape so replies import identically.
DEEP_PROMPT = """You are helping a trainee financial adviser understand this week's Australian
advice-industry news in depth. You will be given items, each with an ID, a TITLE, a SOURCE, a
DATE, the publisher's own text, and a LINK. For each item output one line:
`ID | FLAG | summary | LINK`. FLAG is ACT (changes what an adviser must do), KNOW (useful
context), or NOTE (background/data). Write two to four sentences, on a single line, and lead with
the specific facts — figures, dates, names, what changed — rather than the framing. Rules: use
ONLY the text provided; never invent detail or add facts not present; if the text runs to less
than about eighty words, write "thin — open source" and nothing else; say so if the DATE means a
figure or a poll may have been overtaken; always keep the ID and the LINK unchanged; do not
attempt to access anything beyond the text provided."""

# What --ollama uses by default since 23 Sep 2026: the newsletter wanted dot
# points with the key fact bolded, not one flat sentence. Still one line per
# item — the points are separated by "• " on that line — so the reply imports
# exactly like the other two, and every renderer splits it back into a list.
NEWSLETTER_PROMPT = """You are writing this week's newsletter for Australian financial advisers who
are busy and not experts in every area. You will be given items, each with an ID, a TITLE, a
SOURCE, a DATE, the article text, and a LINK. For each item output exactly one line:
`ID | FLAG | summary | LINK`. FLAG is ACT (changes what an adviser must do), KNOW (useful
context), or NOTE (background/data). The summary is three or four dot points written on that
same line, each starting with "• ". Write the way you would explain it to a colleague over coffee:
plain everyday words, short sentences of no more than 25 words. The first point says what happened
and why it matters, in words anyone could follow. The next points give the key facts: who, how
much, when, what changes. Put the single most important fact in each point in **bold**. Keep
acronyms to a minimum: write the plain-English name first and put the acronym in brackets after it
(for example "the scheme that pays clients of collapsed advice firms (CSLR)", "the corporate
regulator (ASIC)"), and after that use the plain name. Explain any other technical term in a few
plain words, or leave it out if the point works without it. Only go into technical detail when the reader needs it to act. Never write generic
advice such as "advisers should stay informed" or "should review their practices"; if the text
gives no practical consequence, leave that point out. Take care with figures, above all in tables:
say what each number measures exactly as the text does, and never say who pays, owes or receives
money unless the text says so plainly. Rules: use ONLY the article text for facts
about the story; never invent detail or add facts not present; if the text is too thin, write
"• Thin story. Open the source."; never break the line; always keep the ID and the LINK
unchanged; do not attempt to access anything beyond the text provided."""

# Dot points are longer to write than one sentence, so fewer per paste keeps
# each one inside the per-paste wait on a laptop that is short of memory.
NEWSLETTER_CHUNK = 3

# Roughly a comfortable paste for one chat message. Items are never split
# across blocks.
BRIEF_CHUNK = 15

# A deep item carries the publisher's own article text rather than a teaser,
# so far fewer fit in one paste.
DEEP_CHUNK = 6

# The digest has carried a category per item since the dashboard started
# grouping by one, but the briefing did not use it: pastes were chunked
# 15-at-a-time in flag order, so a single paste mixed People moves with
# Compliance. A summary reads better when the paste it came from is all one
# subject, so the briefing can now be filtered or split the same way the
# dashboard groups. The fallback label is included too, so it
# belongs in the list a user may ask for by name.
TOPIC_LABELS = tuple(label for label, _ in TOPIC_RULES) + (FALLBACK_TOPIC,)


def resolve_topics(names):
    """
    Match category names as typed to the labels the classifier actually uses.

    Returns (resolved, unknown). Case and surrounding space are forgiven
    because these are typed at a shell prompt; a misspelling is reported
    rather than quietly dropped, which would otherwise read as "that category
    had no news this week".
    """
    by_lower = {label.lower(): label for label in TOPIC_LABELS}
    resolved, unknown = [], []
    for name in names:
        name = name.strip()
        if not name:
            continue
        label = by_lower.get(name.lower())
        if label is None:
            unknown.append(name)
        elif label not in resolved:
            resolved.append(label)
    return resolved, unknown


def topic_of(item):
    """An item's category, falling back to the classifier's own default."""
    return item.get("topic") or FALLBACK_TOPIC


def filter_by_topic(items, topics):
    """Keep only the items whose category is one of `topics`."""
    wanted = {label.lower() for label in topics}
    return [item for item in items if topic_of(item).lower() in wanted]


def filter_by_flag(items, flags):
    """Keep only the items carrying one of `flags`, e.g. just the KNOW ones."""
    wanted = {flag.upper() for flag in flags}
    return [item for item in items if (item.get("flag") or "").upper() in wanted]


def slug(label):
    """`Super & tax` -> `super-tax`, so a label can name a file."""
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


# The two ways a digest can be cut, each as (key of an item, order of its
# labels). Grouping by both at once is the useful case: "the KNOW items in
# Compliance" is a paste you can actually read in one sitting, where "every
# KNOW item" is not.
GROUP_DIMENSIONS = {
    "topic": (topic_of, TOPIC_LABELS),
    "flag": (lambda item: item.get("flag") or "NOTE",
             tuple(sorted(FLAG_ORDER, key=FLAG_ORDER.get))),
}


def resolve_grouping(spec):
    """
    Read `topic`, `flag` or `topic,flag` into an ordered tuple of dimensions.

    Order is the caller's: `topic,flag` nests flags inside categories and
    names the file compliance-know.md, `flag,topic` the other way round.
    """
    resolved, unknown = [], []
    for name in (spec or "").split(","):
        name = name.strip().lower()
        if not name:
            continue
        if name not in GROUP_DIMENSIONS:
            unknown.append(name)
        elif name not in resolved:
            resolved.append(name)
    return tuple(resolved), unknown


def group_items(items, grouping):
    """
    Split the digest by the combination of dimensions asked for.

    Returns [(label, slug, items)] with empty combinations left out — a
    category with no ACT items this week gets no file rather than one holding
    nothing. An empty grouping returns a single group of everything, so the
    caller has one code path whether or not it is splitting.
    """
    if not grouping:
        return [("All items", "briefing", list(items))]

    keyers = [GROUP_DIMENSIONS[name][0] for name in grouping]
    orders = [GROUP_DIMENSIONS[name][1] for name in grouping]

    buckets = {}
    for item in items:
        buckets.setdefault(tuple(key(item) for key in keyers), []).append(item)

    groups = []
    for combination in itertools.product(*orders):
        if combination in buckets:
            groups.append((
                " · ".join(combination),
                "-".join(slug(part) for part in combination),
                buckets[combination],
            ))
    return groups


def summary_ref(link, title=""):
    """A short, stable handle for one item, for the round trip through a chat."""
    import hashlib

    basis = normalise_link(link) or (title or "")
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:6]


def format_briefing(items, chunk_size=BRIEF_CHUNK, prompt=BRIEF_PROMPT, body_limit=PASTE_BODY_LIMIT):
    """Render the digest as paste-ready blocks for a web AI tool."""
    blocks = []
    for start in range(0, len(items), chunk_size):
        batch = items[start:start + chunk_size]
        lines = [prompt, ""]
        for item in batch:
            ref = item.get("ref") or summary_ref(item.get("link", ""), item.get("title", ""))
            lines.append(f"ID: {ref}")
            lines.append(f"TITLE: {item.get('title', '')}")
            # Who published it and when. Without these a reader cannot tell a
            # masthead's own view from a regulator's, and cannot tell that a
            # poll or a set of quarterly figures has already been overtaken.
            lines.append(f"SOURCE: {item.get('source_name') or '(unknown)'}")
            lines.append(f"DATE: {(item.get('created_at') or '')[:10] or '(unknown)'}")
            text = item.get('brief_text') or item.get('teaser') or item.get('summary') or '(none)'
            lines.append(
                f"TEASER: {_trim_to_sentence(text, body_limit) if body_limit else text}"
            )
            lines.append(f"LINK: {item.get('link', '')}")
            lines.append("")
        blocks.append("\n".join(lines).strip())
    return blocks


def write_briefing(items, path, chunk_size=BRIEF_CHUNK, label=None, prompt=BRIEF_PROMPT):
    """
    Write the briefing blocks to a file, one paste per block.

    `label` names the category in the paste marker, so a file split by
    category says which one it is without the reader counting files.
    """
    blocks = format_briefing(items, chunk_size, prompt)
    parts = []
    for number, block in enumerate(blocks, start=1):
        marker = f"paste {number} of {len(blocks)}"
        if label:
            marker = f"{label} — {marker}"
        parts.append(f"<!-- {marker} -->\n\n{block}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n---\n\n".join(parts) + "\n", encoding="utf-8")
    return path, len(blocks)


# Titles and teasers travel; article text never does.
BUNDLE_BOUNDARY = (
    "Boundary: this bundle holds titles and teasers only. Do not ask a tool to fetch the links — "
    "open them yourself, in your own browser."
)


def _bundle_day(generated_at=None):
    if generated_at:
        return str(generated_at)[:10]
    return datetime.now().strftime("%Y-%m-%d")


def format_bundle_readme(written, generated_at=None):
    """
    The entry point for a downloaded briefing folder.

    `written` is what write_briefing_groups returns:
    [(label, path, blocks, item_count)]. Kept in step with
    web/lib/bundle.ts's bundleReadme — two routes, one output.
    """
    day = _bundle_day(generated_at)
    items = sum(count for _, _, _, count in written)
    pastes = sum(blocks for _, _, blocks, _ in written)

    lines = [
        f"# Briefing bundle — {day}",
        "",
        f"From the Industry Update Monitor digest generated {day}.",
        f"{items} item{'' if items == 1 else 's'} across {len(written)} "
        f"file{'' if len(written) == 1 else 's'}, "
        f"{pastes} paste{'' if pastes == 1 else 's'} in total.",
        "",
        "## What to do with it",
        "",
        "1. Open one `.md` file. Each is one subject, and each paste inside it is sized for one",
        "   chat message.",
        "2. Paste a block into the AI tool of your choice. The prompt is already at the top of it.",
        "3. Paste the reply back with `python src/monitor.py --import-summaries FILE`, or into the",
        "   dashboard. Replies are matched on the six-character ID at the start of each line, so",
        "   they land on the right items whichever file they came from.",
        "4. `links.md` is every item once, with its link, for opening sources yourself.",
        "",
        "## The rule",
        "",
        BUNDLE_BOUNDARY,
        "",
        "A summary is triage. A 🔴 ACT item is read at its original source before it is acted on,",
        "no matter what any summary says.",
        "",
        "## Files",
        "",
    ]
    for label, path, blocks, count in written:
        lines.append(
            f"- `{Path(path).name}` — {label}: {count} item{'' if count == 1 else 's'}, "
            f"{blocks} paste{'' if blocks == 1 else 's'}"
        )
    lines.append("")
    return "\n".join(lines)


def format_bundle_links(items, generated_at=None):
    """Every item once, with its link. Mirrors web/lib/bundle.ts's bundleLinks."""
    lines = [
        f"# Links — {_bundle_day(generated_at)}",
        "",
        "Every item once, in digest order. Open these yourself; do not hand the list to a tool to",
        "fetch.",
        "",
    ]
    for item in items:
        ident = item.get("ref") or item.get("id") or "——————"
        title = str(item.get("title") or "Untitled").replace("|", "/")
        lines.append(f"## {ident} · {item.get('flag', 'NOTE')} · {title}")
        lines.append("")
        lines.append(f"- Source: {item.get('source_name') or 'Unknown'}")
        lines.append(f"- Date: {str(item.get('created_at') or '')[:10] or 'not recorded'}")
        if item.get("intake") == "email":
            # A newsletter's link opens the message in its owner's own mailbox.
            # It is not a public article and must not be offered as one.
            lines.append(
                f"- Newsletter — opens in your own mailbox, not a public page: {item.get('link', '')}"
            )
        else:
            lines.append(f"- Link: {item.get('link', '')}")
        lines.append("")
    return "\n".join(lines)


def write_briefing_groups(directory, items, grouping, chunk_size=BRIEF_CHUNK, prompt=BRIEF_PROMPT):
    """
    Write one briefing per group, so each paste is one coherent subject.

    Returns [(label, path, blocks, item_count)] in label order. The prompt,
    the IDs and the round trip back through --import-summaries are unchanged:
    only the grouping of the pastes differs, so replies from these files
    import exactly like replies from the single-file briefing.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for label, name, group in group_items(items, grouping):
        path, blocks = write_briefing(
            group, directory / f"{name}.md", chunk_size, label=label, prompt=prompt
        )
        written.append((label, path, blocks, len(group)))

    # Unzip today and you get Markdown files with no entry point
    # (IMPROVEMENTS.md item 12). These two are that entry point, and the
    # dashboard's zip carries the same pair.
    (directory / "README.md").write_text(
        format_bundle_readme(written), encoding="utf-8"
    )
    (directory / "links.md").write_text(
        format_bundle_links(items), encoding="utf-8"
    )
    return written


# The reply comes back through a chat window, so it may arrive bulleted,
# bolded, numbered or fenced. Only the pipe-separated shape has to survive.
SUMMARY_LINE = re.compile(
    # "ID: " is allowed in front: qwen3 echoes the label from the prompt.
    r"^\s*(?:[-*>]\s*|\d+[.)]\s*)?\**\s*(?:ID:\s*)?(?P<ref>[0-9a-f]{6})\s*\**\s*\|"
    r"\s*(?P<flag>ACT|KNOW|NOTE)?\s*\|?"
    r"\s*(?P<summary>[^|]+?)\s*(?:\|\s*(?P<link>\S*)\s*)?$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_summaries(text):
    """Pull `ID | FLAG | summary | LINK` lines out of a pasted reply."""
    found = {}
    for match in SUMMARY_LINE.finditer(text or ""):
        summary = re.sub(r"\s+", " ", match.group("summary") or "").strip(" _-")
        # Stray emphasis around the whole line goes; a **bold** pair inside a
        # dot point stays, because the newsletter renders it.
        if summary.count("**") % 2 or (summary.startswith("*") and "•" not in summary):
            summary = summary.strip("*").strip()
        if summary:
            found[match.group("ref").lower()] = summary
    return found


def import_summaries(reply_path, digest_path, origin="manual"):
    """
    Merge summaries from a reply into the digest the dashboard reads.

    Returns (matched, unmatched_refs, total_in_reply). Nothing is invented: a
    reply line whose ID is not in the digest is reported, never guessed at.

    `origin` is recorded as-is and must say who wrote the summary: "manual" for
    a reply pasted back by hand, "ollama:<model>" for a model on this machine.
    A model's work must never inherit the label that means you wrote it.
    """
    digest = json.loads(Path(digest_path).read_text(encoding="utf-8"))
    replies = parse_summaries(Path(reply_path).read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).isoformat()

    matched = 0
    seen = set()
    for item in digest.get("items", []):
        ref = item.get("ref") or summary_ref(item.get("link", ""), item.get("title", ""))
        if ref in replies:
            item["ai_summary"] = replies[ref]
            # Labelled with who wrote it, so the dashboard never presents a
            # summary as something it is not.
            item["ai_source"] = origin
            item["ai_generated_at"] = stamp
            matched += 1
            seen.add(ref)

    Path(digest_path).write_text(json.dumps(digest, indent=2, ensure_ascii=False), encoding="utf-8")
    return matched, sorted(set(replies) - seen), len(replies)


# ---------- Part 7: plain-English terms ----------
# IMPROVEMENTS.md item 1. A local, hand-written glossary — no model, no
# network, no key. It says what a term plainly means, why it matters to
# someone learning, and where to confirm it. What it never does is turn a
# gloss into a conclusion: `Possible meaning` and `Check` stay as the words,
# and an ACT item is still read at its source.

GLOSSARY = Path(__file__).resolve().parent.parent / "data" / "glossary.json"

# Four is the reading-time cap. An item using more terms than that is usually
# using them loosely, and a wall of glosses under a headline is the thing item
# 1 is trying not to become.
TERMS_PER_ITEM = 4


def load_glossary(path=GLOSSARY):
    """
    Read the hand-written glossary.

    A missing or unreadable file is not an error. The explanations are an aid;
    without them the sheet is still a sheet, so the sweep goes on without.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [term for term in data.get("terms", []) if term.get("term")]


def _term_pattern(spelling):
    """
    Whole-word, and case-sensitive when the spelling is an acronym.

    `ART` is the tribunal; `art` is not, and `PDS` should not be found inside a
    word. A spelling that is not all capitals matches either case, because a
    headline may capitalise an ordinary phrase.
    """
    flags = 0 if spelling.isupper() else re.IGNORECASE
    return re.compile(rf"(?<!\w){re.escape(spelling)}(?!\w)", flags)


def spellings_of(entry):
    """Every way the glossary expects one term to be written."""
    return [entry["term"]] + list(entry.get("also", []))


def terms_in(text, glossary=None, limit=TERMS_PER_ITEM):
    """
    Which glossary terms appear in a piece of text, in the glossary's order.

    Nothing is inferred: a term is returned because its own spelling is there.
    """
    glossary = load_glossary() if glossary is None else glossary
    found = []
    for entry in glossary:
        if any(_term_pattern(spelling).search(text or "") for spelling in spellings_of(entry)):
            found.append(entry)
            if limit and len(found) >= limit:
                break
    return found


def item_terms(item, glossary=None, limit=TERMS_PER_ITEM):
    """The terms an item used, read from the words already in the digest."""
    text = f"{item.get('title') or ''} {item.get('teaser') or item.get('summary') or ''}"
    return terms_in(text, glossary, limit)


def format_terms(items, glossary=None):
    """
    Explain each term once, however many items used it.

    Once per sheet rather than once per item is the whole reading-time
    argument: a term running through twenty items costs one paragraph, not
    twenty. Each entry keeps the three parts apart — what it may mean, why it
    matters, and what to check — so an aid cannot be read as a ruling.
    """
    glossary = load_glossary() if glossary is None else glossary
    if not glossary:
        return []

    used = {}
    for item in items:
        for entry in item_terms(item, glossary):
            used.setdefault(entry["term"], [entry, 0])[1] += 1
    if not used:
        return []

    lines = ["## Terms on this sheet", ""]
    lines.append("Learning aids, written by hand. They explain a word, not the item that used it:")
    lines.append("what the item says is in the item's own words above, and nothing here is inferred")
    lines.append("from it. Where a term matters to an ACT item, the primary source is still the")
    lines.append("thing to read.")
    lines.append("")
    for entry, count in used.values():
        lines.append(f"### {entry['term']}")
        lines.append("")
        # A settled term has a plain meaning and saying "possible" about it
        # only teaches distrust of the whole sheet. A proposal, a threshold or
        # a rule under review is the opposite case, and says so in both lines.
        if entry.get("changing"):
            lines.append(f"- Possible meaning: {entry.get('means', '(not written yet)')}")
        else:
            lines.append(f"- In plain English: {entry.get('means', '(not written yet)')}")
        if entry.get("matters"):
            lines.append(f"- Why it matters: {entry['matters']}")
        if entry.get("check"):
            label = "Needs confirmation" if entry.get("changing") else "Check"
            lines.append(f"- {label}: {entry['check']}")
        lines.append(f"- Used by {count} item{'s' if count != 1 else ''} on this sheet.")
        lines.append("")
    return lines


# ---------- Part 8: the weekly sweep ----------
# IMPROVEMENTS.md item 3. The reading is the habit and it stays yours; what a
# tool can do is put the week in the order the flags already imply, and give
# the sweep somewhere to record how long it took and what earned its place.
# Nothing here fetches anything: it reads the digest already on disk.

SWEEP_INTENT = {
    "ACT": "read at the source",
    "KNOW": "pick what is worth it",
    "NOTE": "only if time remains",
}


def sweep_filename(when=None):
    """`sweep-2026-09-17.md` — one sheet per sweep, named for the day it is for."""
    return f"sweep-{(when or date.today()).isoformat()}.md"


def resolve_sweep_path(target, when=None):
    """
    Read `--sweep [PATH]` into the file to write.

    A directory gets a dated sheet inside it, so the default `--sweep` keeps a
    run-by-run record rather than one file overwritten every week. An explicit
    `.md` filename is taken as given.
    """
    path = Path(target)
    if path.suffix.lower() != ".md":
        path = path / sweep_filename(when)
    return path


def _sweep_date(value):
    """`2026-09-14T22:42:25+00:00` -> `14 Sep 2026`; anything unparseable -> ''."""
    try:
        parsed = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return ""
    return f"{parsed.day} {parsed:%b %Y}"


def _sweep_item(item, glossary=None):
    """One tickable entry: what it is, who said it, and where to read it."""
    lines = [f"- [ ] {item.get('title') or '(untitled)'}"]

    meta = [item.get("source_name") or "(unknown source)"]
    # Confidence is shown only where it means "trust this flag". On a NOTE it
    # means "confidently background", which reads as importance if shown.
    if item.get("confidence") is not None and (item.get("flag") or "").upper() in {"ACT", "KNOW"}:
        meta.append(f"{item['confidence']:.0%} confident")
    published = _sweep_date(item.get("created_at"))
    if published:
        meta.append(published)
    lines.append(f"      {' · '.join(meta)}")

    teaser = " ".join((item.get("teaser") or item.get("summary") or "").split())
    if teaser:
        lines.append(f"      {teaser}")

    # A summary written by hand is labelled as such wherever it is shown, so it
    # never reads as something this tool generated.
    hand = " ".join((item.get("ai_summary") or "").split())
    if hand:
        origin = "Summarised by hand" if item.get("ai_source") == "manual" else "Summary"
        lines.append(f"      {origin}: {hand}")

    if item.get("link"):
        # A newsletter links to the message in your own mailbox, not to a
        # public article, so say that rather than offering it as a source.
        # "email" is what email_to_item writes and what is_checkable_link and
        # the dashboard both test. Not "email_newsletter", which is the
        # sources.json intake, and which no digest item ever carries.
        if item.get("intake") == "email":
            lines.append(f"      In your inbox: {item['link']}")
        else:
            lines.append(f"      {item['link']}")
    if item.get("link_ok") is False:
        lines.append("      ⚠️ This link did not resolve when it was checked.")

    # Named here, explained once at the end of the sheet.
    used = [entry["term"] for entry in item_terms(item, glossary)] if glossary else []
    if used:
        lines.append(f"      Terms: {', '.join(used)}")

    lines.append("      Useful? [ ] yes  [ ] no")
    return "\n".join(lines)


def _sweep_source_table(items):
    """What each publication contributed this week, as the basis for keeping it."""
    flags = tuple(sorted(FLAG_ORDER, key=FLAG_ORDER.get))
    tally = {}
    for item in items:
        name = item.get("source_name") or "(unknown source)"
        counts = tally.setdefault(name, dict.fromkeys(flags, 0))
        flag = (item.get("flag") or "NOTE").upper()
        if flag in counts:
            counts[flag] += 1

    rows = ["| Publication | " + " | ".join(flags) + " | Total |",
            "| --- | " + " | ".join("---" for _ in flags) + " | --- |"]
    # Most ACT first, then most items: the order the question "is this worth
    # keeping?" is actually asked in.
    for name, counts in sorted(
        tally.items(), key=lambda pair: (-pair[1]["ACT"], -sum(pair[1].values()), pair[0])
    ):
        rows.append(
            f"| {name} | " + " | ".join(str(counts[flag]) for flag in flags)
            + f" | {sum(counts.values())} |"
        )
    return rows


def format_sweep(items, when=None, generated_at=None, glossary=None):
    """
    Render the week as a sheet to work down and tick off.

    Flag order is the reading order SAFEGUARDS.md section G sets: ACT first and
    at the source, then the KNOW items worth the time, then NOTE only if time
    remains. The blanks are the record — minutes, useful items, and which
    publications earned their place — because none of that can be inferred.
    """
    when = when or date.today()
    total = len(items)
    generated = _sweep_date(generated_at)
    # Read once for the whole sheet, not once per item.
    glossary = load_glossary() if glossary is None else glossary

    lines = [f"# Weekly sweep — {when.day} {when:%b %Y}", ""]
    lines.append("Started: ____   Finished: ____")
    lines.append("")
    lines.append(
        f"{total} item{'s' if total != 1 else ''}"
        + (f" from the digest of {generated}" if generated else "")
        + "."
    )
    lines.append("")
    lines.append("Read down, not across: ACT first, then the KNOW items worth your time,")
    lines.append("then NOTE only if time remains.")
    lines.append("")

    for flag in sorted(FLAG_ORDER, key=FLAG_ORDER.get):
        in_flag = [item for item in items if (item.get("flag") or "NOTE").upper() == flag]
        lines.append(f"## {FLAG_EMOJI[flag]} — {SWEEP_INTENT[flag]} ({len(in_flag)})")
        lines.append("")
        if not in_flag:
            lines.append("Nothing this week.")
            lines.append("")
            continue
        for item in in_flag:
            lines.append(_sweep_item(item, glossary))
            lines.append("")

    lines.extend(format_terms(items, glossary))

    lines.append("## After the sweep")
    lines.append("")
    lines.append(f"Minutes: ____   Useful items: ____ of {total}")
    lines.append("")
    lines.append("Sources that earned their place: ______________________________")
    lines.append("")
    lines.append("Sources that did not: ________________________________________")
    lines.append("")
    lines.append("What each one gave you this week:")
    lines.append("")
    lines.extend(_sweep_source_table(items))
    lines.append("")
    lines.append("A ticked ACT box is not a read ACT item. Its box means you went to the")
    lines.append("primary source, which is the one thing no summary here replaces.")
    return "\n".join(lines) + "\n"


def write_sweep(items, path, when=None, generated_at=None, glossary=None):
    """
    Write the sweep sheet, refusing to write over one that may hold your ticks.

    A sheet is worked on by hand over a week, so overwriting it silently would
    throw away the only copy of the record this feature exists to keep.
    """
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        format_sweep(items, when=when, generated_at=generated_at, glossary=glossary),
        encoding="utf-8",
    )
    return path


# ---------- Part 9: summaries from a model on this machine ----------
# IMPROVEMENTS.md item 11, and Phase 3 of archive/PRD.md without a key or a bill. The
# manual round trip already defines the prompt, the blocks, the reply format
# and the ID matching, so this is a transport and nothing more: the same
# briefing goes to a model on localhost instead of into a chat window, and the
# same importer merges what comes back. See SETUP.md Part 2.

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
# Measured on this machine: three items took 93 seconds through an 8B model,
# including loading it. Thirteen in one paste did not finish inside 180s. So a
# paste is smaller than the chat-window default, and the wait is longer — both
# still bounded, so a stuck model cannot hold the weekly run open all night.
OLLAMA_TIMEOUT = 600
OLLAMA_CHUNK = 5
# The cap is on pastes, because a paste is the unit of work and the thing that
# takes minutes. Twenty at three items each is 60 items — a whole week of dot
# points, about a quarter of an hour on this laptop.
OLLAMA_MAX_BLOCKS = 20
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class OllamaUnavailable(RuntimeError):
    """Ollama could not be reached, or refused. Reported, never retried."""


class OllamaPartial(OllamaUnavailable):
    """A later paste failed; `partial` holds the replies that did come back."""

    def __init__(self, message, partial):
        super().__init__(message)
        self.partial = partial


def _assert_local(host):
    """
    Refuse any host but this machine.

    The entire argument for this feature is that nothing leaves the laptop. A
    remote host would keep the code working and quietly break that promise, so
    it is refused here rather than trusted to a comment.
    """
    hostname = (urlparse(host).hostname or "").lower()
    if hostname not in LOCAL_HOSTS:
        raise OllamaUnavailable(
            f"Refusing to send items to {hostname or host}. --ollama talks to a model on this "
            f"machine only; set OLLAMA_HOST to a localhost address."
        )


def ollama_generate(prompt, model=None, host=None, timeout=OLLAMA_TIMEOUT):
    """
    One block in, the model's reply out.

    Temperature is zero because this is extraction, not writing: the same
    teaser should give the same line twice. Nothing is retried — a retry loop
    against a model that is refusing is how a weekly batch becomes an all-night
    one, and the agent rules ban them outright.
    """
    host = host or OLLAMA_HOST
    _assert_local(host)
    payload = json.dumps({
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        # Thinking models (qwen3, gpt-oss) otherwise write pages of private
        # reasoning before every answer: a 50-item week went from over 30
        # minutes, and a timeout on the last paste, to a few minutes.
        "think": False,
        # Ollama's default context is a few thousand tokens and it drops the
        # start of a longer prompt silently, which is where the instructions
        # are. Three whole articles need room.
        "options": {"temperature": 0, "num_ctx": 16384},
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = error.read().decode("utf-8", "replace")[:200]
        except Exception:  # noqa: BLE001 - the error body is a nicety, not a requirement
            pass
        if error.code == 404:
            raise OllamaUnavailable(
                f"Ollama has no model called {model or OLLAMA_MODEL}. "
                f"Pull it first: ollama pull {model or OLLAMA_MODEL}"
            ) from error
        raise OllamaUnavailable(f"Ollama refused the request (HTTP {error.code}). {detail}") from error
    except TimeoutError as error:
        raise OllamaUnavailable(
            f"{model or OLLAMA_MODEL} was still working after {timeout}s and the wait was given "
            f"up. It is running, just slow: send fewer items per paste "
            f"(--ollama-chunk 4), narrow the week (--flags ACT), or wait longer "
            f"(--ollama-timeout 900)."
        ) from error
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise OllamaUnavailable(
                f"Ollama did not answer within {timeout}s at {host}. If it is running, it is "
                f"loading the model — try again, or raise --ollama-timeout."
            ) from error
        raise OllamaUnavailable(
            f"Ollama is not answering at {host}. Start it with: ollama serve  "
            f"(install: brew install ollama — see SETUP.md Part 2). Reported as: {error}"
        ) from error
    except OSError as error:
        raise OllamaUnavailable(
            f"Ollama is not answering at {host}. Start it with: ollama serve  "
            f"(install: brew install ollama — see SETUP.md Part 2). Reported as: {error}"
        ) from error

    return (body.get("response") or "").strip()


def summarise_with_ollama(items, model=None, host=None, timeout=OLLAMA_TIMEOUT,
                          chunk_size=OLLAMA_CHUNK, prompt=BRIEF_PROMPT,
                          max_blocks=OLLAMA_MAX_BLOCKS, on_block=None):
    """
    Run the briefing through a local model and return its replies as one text.

    The text is in the same shape a chat window would have given back, so it
    goes through `parse_summaries` and `import_summaries` unchanged. It is
    written to disk by the caller before being imported, so a reply that went
    wrong can be read rather than guessed at.
    """
    # The whole article the feed carried: the model is on this machine, so
    # nothing here is sized for a chat window.
    blocks = format_briefing(items, chunk_size, prompt, body_limit=None)
    if max_blocks and len(blocks) > max_blocks:
        raise OllamaUnavailable(
            f"{len(blocks)} pastes is past the {max_blocks}-paste cap for one run. "
            f"Narrow it with --flags ACT,KNOW or --topic, or raise the cap deliberately."
        )

    replies = []
    for number, block in enumerate(blocks, start=1):
        if on_block:
            on_block(number, len(blocks))
        try:
            replies.append(ollama_generate(block, model=model, host=host, timeout=timeout))
        except OllamaUnavailable as error:
            # Twenty minutes of finished pastes are not thrown away because
            # the last one timed out: hand back what came in, still no retry.
            done = "\n".join(reply for reply in replies if reply)
            if done:
                raise OllamaPartial(f"Paste {number} of {len(blocks)} failed: {error}", done) from error
            raise
    return "\n".join(reply for reply in replies if reply)


def _load_email_sender():
    try:
        from src import email_sender
    except ImportError:
        import email_sender
    return email_sender


def _load_telegram_sender():
    try:
        from src import telegram_sender
    except ImportError:
        import telegram_sender
    return telegram_sender


def _load_whatsapp_sender():
    try:
        from src import whatsapp_sender
    except ImportError:
        import whatsapp_sender
    return whatsapp_sender


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Industry Update Monitor")
    parser.add_argument("--email", action="store_true", help="Email digest instead of printing to stdout")
    parser.add_argument("--telegram", action="store_true",
                        help="Send the digest to your own Telegram chat (previews if not set up)")
    parser.add_argument("--only-urgency", default=None, metavar="ACT,KNOW,NOTE",
                        help="Extra send: only these urgencies, e.g. KNOW (with --email/--telegram)")
    parser.add_argument("--only-category", default=None, metavar="CATEGORIES",
                        help='Extra send: only these categories, e.g. "Super & tax" (with --email/--telegram)')
    parser.add_argument("--from-digest", action="store_true",
                        help="Send (--email/--telegram/--preview) the saved digest, summaries included, instead of fetching again")
    parser.add_argument("--preview", action="store_true", help="Write a local HTML preview of the digest to output/digest_preview.html")
    parser.add_argument("--json", nargs="?", const="web/lib/digest.json", default=None,
                        help="Write the digest as JSON for the web dashboard (default: web/lib/digest.json)")
    parser.add_argument("--whatsapp", action="store_true", help="Retired, not recommended: send as a WhatsApp newsletter via Twilio (previews if unconfigured)")
    parser.add_argument("--whatsapp-to", help="WhatsApp recipient in +614... form; defaults to WHATSAPP_TO in .env")
    parser.add_argument("--per-flag", type=int, default=6, help="Max items per flag in the Telegram (or WhatsApp) newsletter")
    parser.add_argument("--days", type=int, default=DEFAULT_MAX_AGE_DAYS, help="Drop items older than this many days (0 = no limit)")
    parser.add_argument("--min-confidence", type=float, default=DEFAULT_MIN_CONFIDENCE, help="Drop items whose flag confidence is below this (0.0-1.0)")
    parser.add_argument("--flags", default="ACT,KNOW,NOTE", help="Comma-separated flags to include, e.g. ACT,KNOW")
    parser.add_argument("--limit", type=int, default=50, help="Maximum items in the digest (1-100)")
    parser.add_argument("--no-check-links", action="store_true", help="Skip the link health check (faster, but dead links may ship)")
    parser.add_argument("--sources", action="store_true", help="Print the source list before the digest")
    parser.add_argument("--gmail", action="store_true",
                        help="Also read newsletters from the industry-update-monitor Gmail label (read-only, opt-in)")
    parser.add_argument("--gmail-label", default=None, help="Gmail label to read (default: industry-update-monitor)")
    parser.add_argument("--gmail-max", type=int, default=25, help="Maximum newsletters to read (1-50)")
    parser.add_argument("--brief", nargs="?", const="output/briefing.md", default=None,
                        help="Write a paste-ready briefing for a web AI tool (default: output/briefing.md)")
    parser.add_argument("--deep", action="store_true",
                        help="Use the detailed prompt and smaller pastes; pair with --flags ACT,KNOW")
    parser.add_argument("--group-by", default=None, metavar="DIMS",
                        help="Split the briefing into one file per group: topic, flag, or topic,flag")
    parser.add_argument("--topic", default=None,
                        help="Comma-separated categories to brief, e.g. Compliance,Regulation")
    parser.add_argument("--ollama", nargs="?", const="", default=None, metavar="MODEL",
                        help="Summarise through a model on this machine (default: $OLLAMA_MODEL "
                             "or llama3.1:8b). Needs `ollama serve` — see SETUP.md Part 2")
    parser.add_argument("--ollama-timeout", type=int, default=OLLAMA_TIMEOUT, metavar="SECONDS",
                        help=f"How long to wait for one paste (default: {OLLAMA_TIMEOUT})")
    parser.add_argument("--ollama-chunk", type=int, default=OLLAMA_CHUNK, metavar="N",
                        help=f"Items per paste through the model (default: {OLLAMA_CHUNK})")
    parser.add_argument("--ollama-reply", default="output/ollama-reply.md", metavar="PATH",
                        help="Where the model's raw reply is written before it is imported")
    parser.add_argument("--sweep", nargs="?", const="output", default=None, metavar="PATH",
                        help="Write a tickable weekly sweep sheet (default: output/sweep-<date>.md)")
    parser.add_argument("--import-summaries", metavar="PATH", default=None,
                        help="Merge summaries pasted back from a web AI tool into the digest JSON")
    parser.add_argument("--digest", default="web/lib/digest.json",
                        help="Digest JSON that --brief reads and --import-summaries writes")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    digest_path = root / args.digest

    # A typo in an extra send must not read as "nothing on that this week".
    if args.only_category:
        chosen_topics, unknown = resolve_topics(args.only_category.split(","))
        if unknown:
            raise SystemExit(f"❌ Unknown category: {', '.join(unknown)}. "
                             f"Choose from: {', '.join(TOPIC_LABELS)}")
        args.only_category = ",".join(chosen_topics)
    if args.only_urgency:
        bad = {f.strip().upper() for f in args.only_urgency.split(",") if f.strip()} - set(FLAG_ORDER)
        if bad:
            raise SystemExit(f"❌ Unknown urgency: {', '.join(sorted(bad))}. Choose from ACT, KNOW, NOTE.")

    # Both flags only shape a briefing. Without --brief they would be read,
    # ignored, and a full fetch would run instead — so say so rather than
    # appearing to have filtered something.
    if (args.group_by or args.topic or args.deep) and args.brief is None:
        if args.deep:
            raise SystemExit("❌ --deep shapes the briefing. Add --brief, e.g. "
                             "python src/monitor.py --brief --deep --flags ACT,KNOW")
        name, value = ("--group-by", args.group_by) if args.group_by else ("--topic", args.topic)
        raise SystemExit(f"❌ {name} shapes the briefing. Add --brief, e.g. "
                         f"python src/monitor.py --brief {name} {value}")

    # Both halves of the manual round trip work from the digest already on
    # disk: no feeds are fetched, so they cost nothing and work offline.
    if (args.brief is not None or args.import_summaries or args.sweep is not None
            or args.ollama is not None):
        if not digest_path.exists():
            raise SystemExit(f"❌ No digest at {digest_path}. Run: python src/monitor.py --json")

        if args.ollama is not None:
            model = args.ollama or OLLAMA_MODEL
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
            model_items = digest.get("items", [])

            # --flags narrows a fetch and a briefing; it narrows this the same
            # way, which is also how a week is kept under the paste cap.
            wanted = {f.strip().upper() for f in args.flags.split(",") if f.strip()}
            if wanted != set(FLAG_ORDER):
                model_items = filter_by_flag(model_items, wanted)
            if not model_items:
                raise SystemExit(f"❌ No matching items in {digest_path}. "
                                 f"Refresh it with: python src/monitor.py --json")

            prompt = DEEP_PROMPT if args.deep else NEWSLETTER_PROMPT
            chunk = (min(args.ollama_chunk, DEEP_CHUNK) if args.deep
                     else min(args.ollama_chunk, NEWSLETTER_CHUNK))
            print(f"🖥️  Summarising {len(model_items)} item(s) through {model} on this machine, "
                  f"{chunk} per paste. Nothing leaves it, and it is slow — minutes, not seconds.")
            try:
                reply = summarise_with_ollama(
                    model_items, model=model, chunk_size=chunk, prompt=prompt,
                    timeout=args.ollama_timeout,
                    on_block=lambda n, total: print(f"   paste {n} of {total}…", flush=True),
                )
            except OllamaPartial as error:
                # Keep what came back; the items after the failure stay
                # unsummarised and the reader sees their teaser instead.
                print(f"⚠️  {error}\n   Keeping the summaries that did come back.")
                reply = error.partial
            except OllamaUnavailable as error:
                # Reported, not retried, and never quietly swapped for anything
                # that could bill: the run stops here.
                raise SystemExit(f"❌ {error}")

            reply_path = root / args.ollama_reply
            reply_path.parent.mkdir(parents=True, exist_ok=True)
            reply_path.write_text(reply + "\n", encoding="utf-8")
            matched, unmatched, total = import_summaries(
                reply_path, digest_path, origin=f"ollama:{model}"
            )
            print(f"🧾 {matched} of {total} summaries merged into {digest_path}, "
                  f"labelled ollama:{model}.")
            print(f"   The model's raw reply is at {reply_path} — read it before trusting it.")
            if unmatched:
                print(f"⚠️  {len(unmatched)} reply line(s) had an ID not in this digest: "
                      f"{', '.join(unmatched)}")
            if not matched:
                print("⚠️  Nothing matched. The model probably did not keep the ID | FLAG | "
                      "summary | LINK shape — see the raw reply.")

        if args.sweep is not None:
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
            sweep_items = digest.get("items", [])
            if not sweep_items:
                raise SystemExit(f"❌ No items in {digest_path}. "
                                 f"Refresh it with: python src/monitor.py --json")
            sweep_path = resolve_sweep_path(root / args.sweep)
            try:
                written = write_sweep(sweep_items, sweep_path,
                                      generated_at=digest.get("generated_at"))
            except FileExistsError:
                # It may already have a morning's ticks in it.
                raise SystemExit(f"❌ {sweep_path} already exists and may hold your ticks. "
                                 f"Rename it, or name another file: "
                                 f"python src/monitor.py --sweep output/sweep-2.md")
            act = sum(1 for item in sweep_items if (item.get("flag") or "").upper() == "ACT")
            print(f"🗒️  Sweep sheet written to {written} — {len(sweep_items)} items, "
                  f"{act} of them ACT.")
            print("   Work down it, tick as you go, and fill in the minutes at the end.")

        if args.brief is not None:
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
            brief_items = digest.get("items", [])

            asked_for = []
            if args.topic:
                topics, unknown = resolve_topics(args.topic.split(","))
                if unknown:
                    raise SystemExit(
                        f"❌ Unknown categor{'ies' if len(unknown) > 1 else 'y'}: "
                        f"{', '.join(unknown)}. Choose from {', '.join(TOPIC_LABELS)}."
                    )
                brief_items = filter_by_topic(brief_items, topics)
                asked_for.extend(topics)

            # --flags already narrows a fetch; it narrows a briefing the same
            # way, so "just this week's KNOW items" needs no new flag.
            wanted_flags = {f.strip().upper() for f in args.flags.split(",") if f.strip()}
            if wanted_flags != set(FLAG_ORDER):
                unknown = wanted_flags - set(FLAG_ORDER)
                if unknown:
                    raise SystemExit(f"❌ Unknown flag(s): {', '.join(sorted(unknown))}. "
                                     f"Choose from ACT, KNOW, NOTE.")
                brief_items = filter_by_flag(brief_items, wanted_flags)
                asked_for.extend(sorted(wanted_flags, key=FLAG_ORDER.get))

            if not brief_items:
                # An empty briefing file would read as "nothing to do"; say
                # what was asked for instead.
                raise SystemExit(
                    f"❌ No {' · '.join(asked_for) if asked_for else ''} items in this digest. "
                    f"Refresh it with: python src/monitor.py --json"
                )

            prompt = DEEP_PROMPT if args.deep else BRIEF_PROMPT
            chunk = DEEP_CHUNK if args.deep else BRIEF_CHUNK
            if args.deep and wanted_flags == set(FLAG_ORDER):
                print("💡 --deep on every flag is a lot of pasting. "
                      "Narrow it with --flags ACT,KNOW.")

            if args.group_by:
                grouping, unknown = resolve_grouping(args.group_by)
                if unknown:
                    raise SystemExit(f"❌ Cannot group by {', '.join(unknown)}. "
                                     f"Choose from {', '.join(GROUP_DIMENSIONS)}.")
                # output/briefing.md -> output/briefing/compliance-know.md, so
                # the default path still names the output without a second flag.
                folder = (root / args.brief).with_suffix("")
                written = write_briefing_groups(folder, brief_items, grouping, chunk, prompt)
                pastes = sum(blocks for _, _, blocks, _ in written)
                print(f"📝 {len(written)} group{'s' if len(written) != 1 else ''}, "
                      f"{pastes} paste{'s' if pastes != 1 else ''} written to {folder}/")
                for label, path, blocks, count in written:
                    print(f"   {label}: {path.name} — {count} item{'s' if count != 1 else ''}, "
                          f"{blocks} paste{'s' if blocks != 1 else ''}")
            else:
                written, blocks = write_briefing(brief_items, root / args.brief, chunk, prompt=prompt)
                print(f"📝 Briefing written to {written} — {blocks} paste{'s' if blocks != 1 else ''}.")

            print("   Paste each block into your AI web tool, then bring the reply back with:")
            print("   python src/monitor.py --import-summaries output/reply.md")

        if args.import_summaries:
            matched, unmatched, total = import_summaries(root / args.import_summaries, digest_path)
            print(f"🧾 {matched} of {total} summaries merged into {digest_path}.")
            if unmatched:
                print(f"⚠️  {len(unmatched)} reply line(s) had an ID not in this digest: {', '.join(unmatched)}")
        raise SystemExit(0)

    if args.sources:
        show_sources()

    if args.from_digest:
        # Send the digest already on disk — the one the local model summarised
        # — instead of fetching again, which would bring in fresh items with
        # no summaries yet.
        if not digest_path.exists():
            raise SystemExit(f"❌ No digest at {digest_path}. Run: python src/monitor.py --json")
        digest_items = [
            {**item, "summary": item.get("teaser", "")}
            for item in json.loads(digest_path.read_text(encoding="utf-8")).get("items", [])
        ]
        if not digest_items:
            raise SystemExit(f"❌ No items in {digest_path}. Run: python src/monitor.py --json")
        summarised = sum(1 for item in digest_items if item.get("ai_summary"))
        print(f"📂 Using the saved digest: {len(digest_items)} items, {summarised} summarised.")
        counts = {flag: sum(1 for i in digest_items if i["flag"] == flag) for flag in FLAG_ORDER}
    else:
        sources, _ = load_sources()
        items, failures = fetch_all_sources(sources, limit=15)
        for name, error in failures:
            print(f"⚠️  Error fetching {name}: {error}")

        if args.gmail:
            # Opt-in and read-only. Four configured sources have no feed at all,
            # two of them ACT-flagged, so without this they never reach the digest.
            newsletters = fetch_gmail_items(
                sources,
                label=args.gmail_label,
                max_messages=args.gmail_max,
                newer_than_days=args.days or 14,
            )
            print(f"📧 Read {len(newsletters)} newsletter(s) from the Gmail label.")
            items.extend(newsletters)

        if not items:
            raise SystemExit(
                "❌ No items fetched from any configured feed. Check data/sources.json — "
                "every source needs a live 'rss' URL, and the run needs network access."
            )

        print(f"📥 Fetched {len(items)} items from {len(sources) - len(failures)} sources.")

        if not args.no_check_links:
            check_links(items)
            broken = sum(1 for item in items if item.get("link_ok") is False)
            unchecked = sum(1 for item in items if "link_ok" in item and item["link_ok"] is None)
            if broken:
                print(f"🔗 {broken} of {len(items)} links did not resolve and were dropped.")
            if unchecked:
                print(f"🔗 {unchecked} link(s) not checked: the site refused a HEAD request, "
                      f"and pages are never opened to check them. Kept in the digest.")

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

        # The email and the Telegram message are what get read each week, so a
        # summary already recorded has to survive a fresh fetch to reach them.
        restored = attach_saved_summaries(digest_items, digest_path)
        if restored:
            print(f"🧾 {restored} saved summar{'ies' if restored != 1 else 'y'} carried over.")
        counts = {flag: sum(1 for i in digest_items if i["flag"] == flag) for flag in FLAG_ORDER}
    print(f"🏷️  Digest: {len(digest_items)} items — ACT {counts['ACT']}, KNOW {counts['KNOW']}, NOTE {counts['NOTE']}")

    if args.json and not args.from_digest:
        written = export_json(digest_items, root / args.json, sources)
        print(f"🗂️  Digest JSON written to {written}")

    if args.preview:
        email_sender = _load_email_sender()
        preview_dir = Path(__file__).resolve().parent.parent / "output"
        preview_dir.mkdir(exist_ok=True)
        preview_path = preview_dir / "digest_preview.html"
        grouped = {flag: [i for i in digest_items if i["flag"] == flag] for flag in FLAG_ORDER}
        # The email exactly as it would be sent: the short alert when
        # DASHBOARD_URL is set, the full newsletter otherwise.
        html = email_sender.build_email(grouped)
        preview_path.write_text(html, encoding="utf-8")
        print(f"📄 Local preview written to {preview_path}")
        if args.whatsapp:
            _load_whatsapp_sender().send_whatsapp_digest(
                digest_items, to_number=args.whatsapp_to, per_flag_limit=args.per_flag
            )
    elif args.email or USE_EMAIL:
        email_sender = _load_email_sender()
        recipient = os.getenv("EMAIL_ADDRESS")
        # An extra, focused send: only the urgencies / categories asked for.
        focus = " · ".join(v for v in (args.only_urgency, args.only_category) if v)
        chosen = _load_telegram_sender().tailor(digest_items, args.only_urgency, args.only_category)
        if focus and not chosen:
            print(f"ℹ️  Nothing this week matches {focus} — no email sent.")
        elif recipient:
            subject = (f"Advice Monitor extra: {focus}" if focus
                       else "Advice Monitor: this week in Australian advice")
            email_sender.send_digest_email(chosen, recipient, subject=subject)
        else:
            print("❌ Cannot email: EMAIL_ADDRESS not set in .env")
    elif args.telegram:
        _load_telegram_sender().send_telegram_digest(
            digest_items, flags=args.only_urgency, topics=args.only_category
        )
    elif args.whatsapp:
        whatsapp_sender = _load_whatsapp_sender()
        whatsapp_sender.send_whatsapp_digest(
            digest_items, to_number=args.whatsapp_to, per_flag_limit=args.per_flag
        )
    else:
        print(summarise_items(items, **collate_kwargs))
