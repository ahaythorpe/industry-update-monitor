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


class StripHtmlTests(unittest.TestCase):
    def test_tags_and_entities_are_removed(self):
        self.assertEqual(strip_html("<p>Fees &amp; costs</p>"), "Fees & costs")

    def test_none_is_safe(self):
        self.assertEqual(strip_html(None), "")


if __name__ == "__main__":
    unittest.main()
