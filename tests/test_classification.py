"""Tests for the no-AI classifier, link hygiene and collation."""

import unittest
from datetime import datetime, timedelta, timezone

from src.monitor import (
    ACT_THRESHOLD,
    classify_scored,
    classify_text,
    collate_items,
    normalise_link,
    strip_html,
    topic_for,
)


def _aged(days):
    return datetime.now(timezone.utc) - timedelta(days=days)


class WordBoundaryTests(unittest.TestCase):
    """Substring matching used to flag these as regulatory action."""

    def test_ban_does_not_match_inside_other_words(self):
        for text in ("Albanese government super plan", "Urban research house update",
                     "Banking sector outlook stays flat"):
            self.assertEqual(classify_text(text), "NOTE", text)

    def test_law_does_not_match_lawyer_or_flawed(self):
        for text in ("Lawyer joins boutique firm", "A flawed outlook for markets"):
            self.assertNotEqual(classify_scored(text)["flag"], "ACT", text)

    def test_real_enforcement_language_still_scores_act(self):
        verdict = classify_scored("ASIC bans adviser and cancels licence", "Effective immediately.")
        self.assertEqual(verdict["flag"], "ACT")
        self.assertGreaterEqual(verdict["act_score"], ACT_THRESHOLD)


class ScoringTests(unittest.TestCase):
    def test_title_hits_outweigh_body_hits(self):
        in_title = classify_scored("Compliance deadline for advisers", "")
        in_body = classify_scored("Advisers weigh options", "Compliance deadline mentioned in passing.")
        self.assertGreater(in_title["act_score"], in_body["act_score"])

    def test_single_incidental_body_term_is_not_act(self):
        # A going-concern story that merely mentions the regulator in its
        # teaser was previously flagged ACT.
        verdict = classify_scored(
            "'Material uncertainty' over a listed licensee as a going concern",
            "The company said the regulatory environment remained challenging.",
        )
        self.assertNotEqual(verdict["flag"], "ACT")

    def test_source_flag_is_a_prior_not_an_override(self):
        # An ACT-flagged source publishing background must not yield ACT.
        verdict = classify_scored("Photo gallery from our day out", "", source_flag="ACT")
        self.assertEqual(verdict["flag"], "NOTE")

    def test_source_prior_breaks_a_tie_in_its_favour(self):
        without = classify_scored("Consultation on licensee rules", "")
        with_prior = classify_scored("Consultation on licensee rules", "", source_flag="ACT")
        self.assertGreater(with_prior["act_score"], without["act_score"])

    def test_event_marketing_is_demoted(self):
        verdict = classify_scored("Congress 2026 program and early bird registrations open", "")
        self.assertEqual(verdict["flag"], "NOTE")
        self.assertTrue(verdict["demoted_by"])

    def test_confidence_is_bounded_and_ranks_clear_calls_higher(self):
        clear = classify_scored("ASIC bans adviser, cancels licence and issues penalty", "")
        borderline = classify_scored("Adviser numbers tick up", "")
        for verdict in (clear, borderline):
            self.assertGreaterEqual(verdict["confidence"], 0.0)
            self.assertLessEqual(verdict["confidence"], 1.0)
        self.assertGreater(clear["confidence"], borderline["confidence"])

    def test_matched_terms_are_reported_for_inspection(self):
        verdict = classify_scored("ASIC compliance deadline", "")
        self.assertIn(r"\basic\b", verdict["matched"])


class LinkTests(unittest.TestCase):
    def test_tracking_parameters_are_stripped(self):
        self.assertEqual(
            normalise_link("https://Example.com/story/?utm_source=x&utm_medium=y&id=7#top"),
            "https://example.com/story?id=7",
        )

    def test_trailing_slash_and_fragment_do_not_split_an_item(self):
        self.assertEqual(
            normalise_link("https://example.com/a/"),
            normalise_link("https://example.com/a#section"),
        )

    def test_non_http_links_are_rejected(self):
        for bad in ("javascript:alert(1)", "mailto:a@b.test", "", "not a url"):
            self.assertEqual(normalise_link(bad), "")


class CollationTests(unittest.TestCase):
    def test_same_article_with_different_tracking_params_dedupes(self):
        items = [
            {"title": "ASIC bans adviser", "summary": "Licence cancelled.", "link": "https://a.test/x?utm_source=news"},
            {"title": "ASIC bans adviser", "summary": "Licence cancelled.", "link": "https://a.test/x"},
        ]
        self.assertEqual(len(collate_items(items)), 1)

    def test_stale_items_are_dropped(self):
        items = [
            {"title": "ASIC bans adviser", "summary": "", "link": "https://a.test/new", "published": _aged(1)},
            {"title": "ASIC bans another adviser", "summary": "", "link": "https://a.test/old", "published": _aged(400)},
        ]
        collated = collate_items(items, max_age_days=14)
        self.assertEqual([i["link"] for i in collated], ["https://a.test/new"])

    def test_undated_items_survive_the_age_filter(self):
        items = [{"title": "ASIC bans adviser", "summary": "", "link": "https://a.test/x"}]
        self.assertEqual(len(collate_items(items, max_age_days=14)), 1)

    def test_dead_links_are_dropped_when_required(self):
        items = [
            {"title": "ASIC bans adviser", "summary": "", "link": "https://a.test/ok", "link_ok": True},
            {"title": "ASIC bans other adviser", "summary": "", "link": "https://a.test/dead", "link_ok": False},
        ]
        self.assertEqual(len(collate_items(items, require_working_link=True)), 1)
        self.assertEqual(len(collate_items(items, require_working_link=False)), 2)

    def test_flag_and_confidence_filters(self):
        items = [
            {"title": "ASIC bans adviser and cancels licence", "summary": "", "link": "https://a.test/1"},
            {"title": "Market wrap for the quarter", "summary": "", "link": "https://a.test/2"},
        ]
        self.assertEqual([i["flag"] for i in collate_items(items, flags={"ACT"})], ["ACT"])
        self.assertEqual(len(collate_items(items, min_confidence=0.0)), 2)

    def test_min_confidence_drops_borderline_calls(self):
        items = [
            {"title": "Adviser numbers tick up", "summary": "", "link": "https://a.test/3"},
            {"title": "ASIC bans adviser, cancels licence, issues penalty", "summary": "", "link": "https://a.test/4"},
        ]
        kept = collate_items(items, min_confidence=0.8)
        self.assertEqual([i["title"] for i in kept], ["ASIC bans adviser, cancels licence, issues penalty"])

    def test_min_confidence_is_range_checked(self):
        with self.assertRaises(ValueError):
            collate_items([], min_confidence=1.5)

    def test_items_are_ordered_by_flag_then_confidence(self):
        items = [
            {"title": "Market wrap", "summary": "", "link": "https://a.test/3"},
            {"title": "Adviser appointed to board", "summary": "", "link": "https://a.test/2"},
            {"title": "ASIC bans adviser, cancels licence, issues penalty", "summary": "", "link": "https://a.test/1"},
        ]
        collated = collate_items(items)
        self.assertEqual([i["flag"] for i in collated], ["ACT", "KNOW", "NOTE"])

    def test_classification_is_recomputed_not_inherited(self):
        # The old pipeline stamped the source flag onto every item, so the
        # classifier never ran on feed items at all.
        items = [{"title": "Photo gallery from the golf day", "summary": "",
                  "link": "https://a.test/g", "source_flag": "ACT"}]
        self.assertEqual(collate_items(items)[0]["flag"], "NOTE")

    def test_a_note_never_displaces_an_act_for_the_same_link(self):
        # Two outlets, one story, one link. The background-worded copy scores a
        # confident 1.0 NOTE; the copy that reads as ACT scrapes in around 0.7.
        # Keeping the higher confidence dropped the ACT out of the digest.
        items = [
            {"title": "Adviser levy consultation opens", "summary": "",
             "link": "https://a.test/story?utm_source=a", "source_name": "Outlet A"},
            {"title": "Coffee catch up with the team", "summary": "",
             "link": "https://a.test/story?utm_source=b", "source_name": "Outlet B"},
        ]
        for ordering in (items, list(reversed(items))):
            kept = collate_items(ordering)
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0]["flag"], "ACT")


class StripHtmlTests(unittest.TestCase):
    def test_tags_and_entities_are_removed(self):
        self.assertEqual(strip_html("<p>Fees &amp; costs</p>"), "Fees & costs")

    def test_none_is_safe(self):
        self.assertEqual(strip_html(None), "")


class TopicTests(unittest.TestCase):
    """Topics are scored, not first-match — declaration order used to decide."""

    def test_headline_subject_beats_an_incidental_body_mention(self):
        topic = topic_for(
            "ASIC zeroes in on recurring compliance breaches",
            "ASIC has warned licensees about lapses in superannuation advice practices.",
        )
        self.assertEqual(topic, "Compliance")

    def test_a_super_story_still_reads_as_super(self):
        topic = topic_for(
            "Late-run LRBAs attracting ATO attention",
            "The tax office received more than 13,000 new SMSF registrations.",
        )
        self.assertEqual(topic, "Super & tax")

    def test_insurer_counts_as_insurance_vocabulary(self):
        # The rule matched "insurance" but not "insurer", so a story about an
        # insurer scored nothing for the topic named after it.
        self.assertEqual(topic_for("Life insurer lifts income protection premiums", ""), "Insurance")

    def test_a_regulatory_label_wins_a_tie(self):
        # "Insurer sanctioned over serious breaches" scores 2 for Insurance and
        # 2 for Compliance; the breach is what the reader has to act on.
        self.assertEqual(topic_for("Insurer sanctioned over serious breaches", ""), "Compliance")

    def test_an_unmatched_item_falls_back_to_the_general_pile(self):
        # Deliberately about nothing the rules cover. The example used to be a
        # markets headline, which stopped being unmatched the day Markets &
        # investing was added — a fallback test has to use something no rule
        # could ever plausibly claim.
        self.assertEqual(
            topic_for("Storms disrupt travel in regional areas", "Flights were delayed."),
            "General",
        )

    def test_markets_news_is_labelled_rather_than_left_in_the_general_pile(self):
        # 19 of 50 items had no rule at all, and most of them were this.
        self.assertEqual(
            topic_for("Active ETF launches push ETF products past 500", ""),
            "Markets & investing",
        )

    def test_a_tribunal_banning_is_regulation(self):
        self.assertEqual(
            topic_for("ART reviews five-year bans of two former advisers", ""),
            "Regulation",
        )

    def test_what_an_adviser_charges_is_not_the_same_as_who_owns_whom(self):
        # Business is acquisitions and licensees; this is pricing.
        self.assertEqual(
            topic_for("Asset-based fees dwindle as firms price for complexity", ""),
            "Fees & pricing",
        )


if __name__ == "__main__":
    unittest.main()
