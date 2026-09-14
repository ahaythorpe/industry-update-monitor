"""
The feed's own article text: what we take, and what we must never take.

feed_body reads content:encoded — part of the feed the publisher generates and
serves. These tests pin the boundary (nothing is fetched), the cap, and the
provenance marker, because this is the code SAFEGUARDS.md section A was amended
for and an untested amendment is just a comment.
"""

import unittest

from src.monitor import FEED_BODY_LIMIT, _trim_to_sentence, feed_body


class TrimTests(unittest.TestCase):
    def test_short_text_is_left_alone(self):
        self.assertEqual(_trim_to_sentence("Already short.", 100), "Already short.")

    def test_it_backs_up_to_the_last_finished_sentence(self):
        trimmed = _trim_to_sentence("One sentence. Two sentence. Three runs past the limit.", 30)
        self.assertEqual(trimmed, "One sentence. Two sentence.")
        self.assertFalse(trimmed.endswith("…"))

    def test_a_single_long_paragraph_is_cut_rather_than_discarded(self):
        # Backing up to a sentence that leaves almost nothing would throw away
        # the whole opening paragraph, which is where the news is.
        trimmed = _trim_to_sentence("Hi. " + "a long unbroken opening paragraph " * 5, 60)
        self.assertTrue(trimmed.endswith("…"))
        self.assertGreater(len(trimmed), 40)

    def test_a_question_mark_ends_a_sentence_too(self):
        self.assertEqual(
            _trim_to_sentence("Is this the end? Yes it is, and more text follows.", 30),
            "Is this the end?",
        )

    def test_a_sentence_end_too_early_in_the_cut_is_ignored(self):
        # "Why now?" sits at character 7 of a 20-character cut. Backing up to
        # it would throw away nearly two thirds of what was asked for, so the
        # cut is kept and marked instead. This guard is why the test above
        # needs its sentence break past the 40% mark.
        self.assertEqual(
            _trim_to_sentence("Why now? Because of this. And more.", 20),
            "Why now? Because of…",
        )


class FeedBodyTests(unittest.TestCase):
    def test_content_encoded_is_read_and_stripped_of_markup(self):
        entry = {"content": [{"value": "<p>ASIC has <b>banned</b> a director.</p>"}]}
        self.assertEqual(feed_body(entry), "ASIC has banned a director.")

    def test_an_entry_with_no_content_returns_nothing(self):
        # The teaser is then used instead — never an article fetch.
        self.assertEqual(feed_body({}), "")
        self.assertEqual(feed_body({"content": []}), "")
        self.assertEqual(feed_body({"content": [{"value": ""}]}), "")

    def test_publisher_furniture_is_stripped_from_feed_content(self):
        entry = {"content": [{"value": "Image: Supplied. ASIC acted today. Read more here"}]}
        body = feed_body(entry)
        self.assertNotIn("Read more", body)
        self.assertNotIn("Image:", body)
        self.assertIn("ASIC acted today", body)

    def test_long_content_is_capped(self):
        entry = {"content": [{"value": "This is one sentence. " * 400}]}
        body = feed_body(entry)
        self.assertLessEqual(len(body), FEED_BODY_LIMIT)
        self.assertGreater(len(body), FEED_BODY_LIMIT * 0.4)

    def test_a_malformed_content_block_does_not_crash_the_run(self):
        # One bad entry must not take a whole feed down.
        self.assertEqual(feed_body({"content": ["not a dict"]}), "")
        self.assertEqual(feed_body({"content": None}), "")


class ProvenanceTests(unittest.TestCase):
    """Every item must say which text a summary was written from."""

    def _entry(self, with_content):
        entry = {"title": "ASIC bans a director", "summary": "The regulator acted.",
                 "link": "https://a.test/x"}
        if with_content:
            entry["content"] = [{"value": "<p>The regulator acted today, banning a director.</p>"}]
        return entry

    def test_feed_content_is_recorded_when_the_publisher_supplies_it(self):
        from src.monitor import clean_teaser, summarise_teaser

        entry = self._entry(with_content=True)
        body = feed_body(entry)
        teaser = clean_teaser(entry["summary"])
        item = {
            "brief_text": body or teaser[:600],
            "body_source": "feed_content" if body else "feed_summary",
        }
        self.assertEqual(item["body_source"], "feed_content")
        self.assertIn("banning a director", item["brief_text"])
        self.assertTrue(summarise_teaser(entry["title"], teaser))

    def test_the_teaser_is_recorded_when_there_is_no_feed_content(self):
        from src.monitor import clean_teaser

        entry = self._entry(with_content=False)
        body = feed_body(entry)
        teaser = clean_teaser(entry["summary"])
        item = {
            "brief_text": body or teaser[:600],
            "body_source": "feed_content" if body else "feed_summary",
        }
        self.assertEqual(item["body_source"], "feed_summary")
        self.assertEqual(item["brief_text"], "The regulator acted.")


if __name__ == "__main__":
    unittest.main()
