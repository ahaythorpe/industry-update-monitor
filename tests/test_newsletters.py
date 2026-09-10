"""Tests for newsletters read from the Gmail label as digest items."""

import unittest

from src.monitor import (
    check_links,
    collate_items,
    email_to_item,
    is_checkable_link,
    match_source_for_sender,
)

SOURCES = [
    {"name": "CFS FirstTech", "flag": "ACT"},
    {"name": "Macquarie Technical Services", "flag": "ACT"},
    {"name": "FAAA", "flag": "KNOW"},
    {"name": "FS Industry Moves", "flag": "KNOW"},
]


def _email(**overrides):
    email = {
        "subject": "FirstTech update: Division 296 draft rules",
        "sender": "CFS FirstTech <firsttech@cfs.com.au>",
        "received": "2026-09-09T02:00:00+00:00",
        "body": (
            "The draft rules for Division 296 were released this week.\n"
            "Advisers should review client balances above $3 million.\n"
            "Unsubscribe from this newsletter."
        ),
        "link": "https://mail.google.com/mail/u/0/#all/18f2",
    }
    email.update(overrides)
    return email


class SenderMatchingTests(unittest.TestCase):
    def test_a_configured_source_name_in_the_sender_matches(self):
        matched = match_source_for_sender("CFS FirstTech <firsttech@cfs.com.au>", SOURCES)
        self.assertEqual(matched["name"], "CFS FirstTech")

    def test_a_distinctive_first_word_is_enough(self):
        matched = match_source_for_sender("Macquarie Group <news@macquarie.com>", SOURCES)
        self.assertEqual(matched["name"], "Macquarie Technical Services")

    def test_an_unknown_sender_matches_nothing(self):
        # Better no prior than the wrong one: a guess here would put an ACT
        # prior on somebody's marketing email.
        self.assertIsNone(match_source_for_sender("Deals Weekly <hi@deals.test>", SOURCES))

    def test_a_short_first_word_cannot_match_on_its_own(self):
        self.assertIsNone(match_source_for_sender("FS Weekly <hi@elsewhere.test>", [SOURCES[3]]))

    def test_an_empty_sender_is_safe(self):
        self.assertIsNone(match_source_for_sender("", SOURCES))
        self.assertIsNone(match_source_for_sender(None, SOURCES))


class EmailToItemTests(unittest.TestCase):
    def test_a_newsletter_becomes_a_digest_item(self):
        item = email_to_item(_email(), SOURCES)
        self.assertEqual(item["title"], "FirstTech update: Division 296 draft rules")
        self.assertEqual(item["source_name"], "CFS FirstTech")
        self.assertEqual(item["source_flag"], "ACT")
        self.assertEqual(item["intake"], "email")
        self.assertEqual(item["link"], "https://mail.google.com/mail/u/0/#all/18f2")

    def test_the_summary_comes_from_the_email_and_drops_the_footer(self):
        summary = email_to_item(_email(), SOURCES)["summary"]
        self.assertIn("Division 296", summary)
        self.assertNotIn("Unsubscribe", summary)

    def test_a_one_line_body_ending_in_a_footer_still_summarises(self):
        # Filtering whole lines discarded a single-paragraph newsletter
        # entirely, leaving "No summary text was available."
        item = email_to_item(
            _email(body="The ATO updated its LRBA guidance this week. Unsubscribe here."),
            SOURCES,
        )
        self.assertIn("ATO updated its LRBA guidance", item["summary"])

    def test_the_received_date_is_used_and_is_timezone_aware(self):
        published = email_to_item(_email(), SOURCES)["published"]
        self.assertEqual(published.year, 2026)
        self.assertIsNotNone(published.tzinfo)

    def test_an_unparseable_date_does_not_break_intake(self):
        self.assertIsNone(email_to_item(_email(received="not a date"), SOURCES)["published"])

    def test_an_unmatched_sender_keeps_the_sender_as_the_source(self):
        item = email_to_item(_email(sender="Someone <hi@elsewhere.test>"), SOURCES)
        self.assertEqual(item["source_name"], "Someone <hi@elsewhere.test>")
        self.assertIsNone(item["source_flag"])

    def test_the_item_classifies_like_any_other(self):
        # The source flag is a prior; the words still decide.
        item = collate_items([email_to_item(_email(), SOURCES)])[0]
        self.assertEqual(item["flag"], "ACT")


class LinkCheckTests(unittest.TestCase):
    def test_a_newsletter_link_is_never_link_checked(self):
        # It redirects to a Google login for every client but your browser, so
        # checking it would mark every newsletter dead and drop it.
        self.assertFalse(is_checkable_link({"intake": "email"}))
        self.assertTrue(is_checkable_link({"intake": "rss"}))
        self.assertTrue(is_checkable_link({}))

    def test_check_links_leaves_newsletters_alone(self):
        items = [email_to_item(_email(), SOURCES)]
        check_links(items)
        self.assertNotIn("link_ok", items[0])

    def test_a_newsletter_survives_a_run_that_requires_working_links(self):
        items = [email_to_item(_email(), SOURCES)]
        check_links(items)
        self.assertEqual(len(collate_items(items, require_working_link=True)), 1)


if __name__ == "__main__":
    unittest.main()
