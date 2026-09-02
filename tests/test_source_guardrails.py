import unittest

from src.monitor import (
    UnsafeSourceError,
    assess_email,
    collate_items,
    extractive_summary,
    format_assessment,
    validate_feed_source,
)


class SourceGuardrailTests(unittest.TestCase):
    def setUp(self):
        self.valid_source = {
            "name": "Example free feed",
            "access": "free",
            "intake": "rss",
            "rss": "https://example.com/feed.xml",
            "home": "https://example.com",
        }

    def assert_source_rejected(self, **changes):
        source = self.valid_source.copy()
        source.update(changes)
        with self.assertRaises(UnsafeSourceError):
            validate_feed_source(source)

    def test_accepts_configured_free_feed(self):
        self.assertEqual(validate_feed_source(self.valid_source), self.valid_source["rss"])

    def test_rejects_paid_source(self):
        self.assert_source_rejected(access="paid")

    def test_rejects_non_rss_intake(self):
        self.assert_source_rejected(intake="listen")

    def test_rejects_missing_or_invalid_feed(self):
        self.assert_source_rejected(rss=None)
        self.assert_source_rejected(rss="https://example.com/article/123")

    def test_rejects_feed_on_different_host(self):
        self.assert_source_rejected(rss="https://other.example/feed.xml")

    def test_rejects_raw_url_instead_of_source(self):
        with self.assertRaises(UnsafeSourceError):
            validate_feed_source("https://example.com/feed.xml")

    def test_assesses_act_email_and_preserves_source(self):
        email = {
            "subject": "ASIC announces compliance deadline",
            "body": "ASIC announces a compliance deadline. Advisers should review the notice.",
            "source": "ASIC alert",
            "link": "https://example.com/notice",
        }
        assessment = assess_email(email)
        self.assertEqual(assessment["flag"], "ACT")
        self.assertEqual(assessment["link"], email["link"])
        self.assertIn("Read the original source", assessment["instruction"])

    def test_extractive_summary_drops_promotional_lines(self):
        email = {
            "subject": "Future Fund update",
            "body": (
                "Future Fund chief steps down. A new appointment is expected.\n"
                "Unsubscribe from this newsletter."
            ),
        }
        summary = extractive_summary(email)
        self.assertIn("Future Fund chief steps down", summary)
        self.assertNotIn("Unsubscribe", summary)

    def test_format_assessment_orders_act_before_know_and_note(self):
        assessments = [
            {"flag": "NOTE", "summary": "Market data.", "source": "ABS", "link": "abs"},
            {"flag": "ACT", "summary": "Regulatory notice.", "source": "ASIC", "link": "asic", "instruction": "Read the original source before relying on this."},
            {"flag": "KNOW", "summary": "Industry update.", "source": "FS", "link": "fs"},
        ]
        report = format_assessment(assessments)
        self.assertLess(report.index("🔴 ACT"), report.index("🟠 KNOW"))
        self.assertLess(report.index("🟠 KNOW"), report.index("🟢 NOTE"))

    def test_collate_items_removes_duplicates_and_prioritises(self):
        items = [
            {"title": "Market data", "summary": "Background.", "link": "market"},
            {"title": "ASIC notice", "summary": "Compliance deadline.", "link": "asic"},
            {"title": "ASIC notice", "summary": "Compliance deadline.", "link": "asic"},
        ]
        collated = collate_items(items)
        self.assertEqual([item["flag"] for item in collated], ["ACT", "NOTE"])
        self.assertEqual(len(collated), 2)

    def test_collate_items_enforces_limit(self):
        with self.assertRaises(ValueError):
            collate_items([], max_items=101)

if __name__ == "__main__":
    unittest.main()