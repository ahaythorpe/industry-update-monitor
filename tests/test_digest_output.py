"""Tests for teaser cleaning, summarisation and the WhatsApp newsletter."""

import unittest

from src.monitor import clean_teaser, summarise_teaser
from src.whatsapp_sender import MAX_BODY, format_whatsapp_digest


class TeaserCleaningTests(unittest.TestCase):
    def test_photo_credit_with_agency_domain_is_removed(self):
        for raw, expected_start in (
            ("Image: Studio Zenith/stock.adobe.com.au Three fund managers have hired.", "Three fund"),
            ("Bits and Splits/adobe.stock.com In a recent webinar, Cullen said.", "In a recent"),
            ("Image by onephoto/stock.adobe.com Ellem said on a webinar.", "Ellem said"),
        ):
            self.assertTrue(clean_teaser(raw).startswith(expected_start), raw)

    def test_supplied_credit_needs_a_marker_word(self):
        self.assertTrue(clean_teaser("Image: Supplied WT Financial is expanding.").startswith("WT Financial"))
        # The same word inside real prose must survive.
        prose = "The company supplied documents to ASIC during the investigation."
        self.assertEqual(clean_teaser(prose), prose)

    def test_repeated_lead_word_after_a_credit_is_collapsed(self):
        self.assertTrue(clean_teaser("Supplied: Praemium Praemium is betting.").startswith("Praemium is"))

    def test_wordpress_footer_is_removed(self):
        cleaned = clean_teaser("Anderson retires in November. The post Anderson retires appeared first on FAAA.")
        self.assertNotIn("appeared first on", cleaned)
        self.assertIn("Anderson retires in November", cleaned)

    def test_ordinary_leads_are_left_alone(self):
        for prose in (
            "The Australian Financial Complaints Authority (AFCA) is seeking feedback.",
            "Invesco Asia Pacific chief Andrew Lo will retire from the manager.",
            "Sequoia Financial Group, the ASX-listed owner of InterPrac, disclosed uncertainty.",
        ):
            self.assertEqual(clean_teaser(prose), prose)


class SummaryTests(unittest.TestCase):
    def test_summary_keeps_whole_sentences(self):
        teaser = "Total super assets hit $4.8 trillion. That marks a 9% rise. A third sentence follows here."
        summary = summarise_teaser("Super assets rise", teaser)
        self.assertTrue(summary.endswith((".", "…")))
        self.assertNotIn("A third sentence", summary)

    def test_long_summary_is_not_cut_mid_word(self):
        teaser = "Compliance " * 100
        summary = summarise_teaser("Compliance update", teaser, max_chars=120)
        self.assertLessEqual(len(summary), 121)
        self.assertTrue(summary.endswith("…"))

    def test_teaser_truncated_by_the_publisher_is_marked(self):
        summary = summarise_teaser("Retirement", "He will retire after 30 years and much of the last")
        self.assertTrue(summary.endswith("…"))

    def test_empty_teaser_is_safe(self):
        self.assertEqual(summarise_teaser("A title", ""), "")
        self.assertEqual(summarise_teaser("A title", None), "")


def _items(count, flag="KNOW", summary="A short summary sentence."):
    return [
        {"title": f"Item number {n}", "summary": summary, "link": f"https://a.test/{n}",
         "flag": flag, "confidence": 0.9, "source_name": "Test Source"}
        for n in range(count)
    ]


class WhatsAppFormatTests(unittest.TestCase):
    def test_short_digest_is_a_single_message(self):
        messages = format_whatsapp_digest(_items(2))
        self.assertEqual(len(messages), 1)
        self.assertIn("Industry Update Monitor", messages[0])

    def test_every_part_respects_the_length_cap(self):
        messages = format_whatsapp_digest(_items(40), per_flag_limit=40)
        self.assertGreater(len(messages), 1)
        for body in messages:
            self.assertLessEqual(len(body), MAX_BODY + 40)  # + part counter

    def test_a_split_section_reintroduces_its_heading(self):
        messages = format_whatsapp_digest(_items(40), per_flag_limit=40)
        for body in messages[1:]:
            self.assertIn("_(cont.)_", body.split("\n\n")[0] + body)

    def test_flags_are_ordered_act_then_know_then_note(self):
        items = _items(1, "NOTE") + _items(1, "ACT") + _items(1, "KNOW")
        combined = "\n".join(format_whatsapp_digest(items))
        self.assertLess(combined.index("ACT — action"), combined.index("KNOW — worth"))
        self.assertLess(combined.index("KNOW — worth"), combined.index("NOTE — background"))

    def test_confidence_is_hidden_on_note_items(self):
        note = format_whatsapp_digest(_items(1, "NOTE"))[0]
        act = format_whatsapp_digest(_items(1, "ACT"))[0]
        self.assertNotIn("confidence", note)
        self.assertIn("confidence", act)

    def test_publisher_markup_characters_cannot_break_formatting(self):
        items = [{"title": "A *bold* claim_here", "summary": "Text with *stars*",
                  "link": "https://a.test/1", "flag": "ACT", "confidence": 0.9}]
        body = format_whatsapp_digest(items)[0]
        self.assertNotIn("*bold*", body)
        self.assertEqual(body.count("*") % 2, 0)

    def test_empty_digest_says_so(self):
        self.assertIn("Nothing cleared the filters", format_whatsapp_digest([])[0])

    def test_per_flag_limit_is_reported(self):
        body = "\n".join(format_whatsapp_digest(_items(20), per_flag_limit=3))
        self.assertIn("top 3 of 20", body)


if __name__ == "__main__":
    unittest.main()
