"""Tests for the newcomer explanations: what is matched, and how it is worded."""

import json
import tempfile
import unittest
from pathlib import Path

from src.monitor import (
    GLOSSARY,
    TERMS_PER_ITEM,
    format_sweep,
    format_terms,
    item_terms,
    load_glossary,
    spellings_of,
    terms_in,
)


def _glossary():
    return [
        {"term": "ASIC", "means": "the corporate regulator.",
         "matters": "its actions change what an adviser does.", "check": "asic.gov.au"},
        {"term": "ART", "also": ["Administrative Review Tribunal"],
         "means": "the tribunal that reviews government decisions.", "check": "art.gov.au"},
        {"term": "best interests duty", "also": ["BID"],
         "means": "the duty to act in the client's best interests.",
         "check": "legislation.gov.au"},
        {"term": "Div 296", "means": "a proposed extra tax on very large super balances.",
         "check": "treasury.gov.au for the current status", "changing": True},
    ]


class MatchingTests(unittest.TestCase):
    def test_an_acronym_is_matched_on_its_own_capitals(self):
        self.assertEqual([t["term"] for t in terms_in("ASIC bans an adviser", _glossary())], ["ASIC"])

    def test_a_lower_case_word_is_not_the_acronym(self):
        # "the art of advice" is not the Administrative Review Tribunal.
        self.assertEqual(terms_in("the art of giving advice", _glossary()), [])

    def test_an_acronym_inside_a_word_is_not_a_match(self):
        self.assertEqual(terms_in("BASICS and PARTS", _glossary()), [])

    def test_a_written_out_name_matches_whatever_its_case(self):
        found = terms_in("the administrative review tribunal upheld it", _glossary())
        self.assertEqual([t["term"] for t in found], ["ART"])

    def test_a_phrase_matches_in_a_headline_that_capitalises_it(self):
        found = terms_in("Best Interests Duty under review", _glossary())
        self.assertEqual([t["term"] for t in found], ["best interests duty"])

    def test_nothing_is_returned_for_text_using_none_of_them(self):
        self.assertEqual(terms_in("markets drifted lower across the week", _glossary()), [])

    def test_matching_is_capped_so_one_item_cannot_bury_the_sheet(self):
        text = "ASIC ART best interests duty Div 296"
        self.assertEqual(len(terms_in(text, _glossary(), limit=2)), 2)

    def test_an_item_is_read_from_its_title_and_teaser(self):
        item = {"title": "Tribunal reviews a ban", "teaser": "ASIC had banned the adviser."}
        self.assertEqual([t["term"] for t in item_terms(item, _glossary())], ["ASIC"])


class WordingTests(unittest.TestCase):
    def test_a_settled_term_is_stated_plainly(self):
        block = "\n".join(format_terms([{"title": "ASIC acts"}], _glossary()))
        self.assertIn("- In plain English: the corporate regulator.", block)
        self.assertIn("- Check: asic.gov.au", block)

    def test_a_moving_target_is_marked_as_one(self):
        block = "\n".join(format_terms([{"title": "Div 296 debated"}], _glossary()))
        self.assertIn("- Possible meaning: a proposed extra tax", block)
        self.assertIn("- Needs confirmation: treasury.gov.au", block)
        self.assertNotIn("In plain English", block)

    def test_the_section_says_it_explains_the_word_not_the_item(self):
        block = "\n".join(format_terms([{"title": "ASIC acts"}], _glossary()))
        self.assertIn("nothing here is inferred", block)
        self.assertIn("the primary source is still the", block)

    def test_a_term_is_explained_once_however_many_items_used_it(self):
        items = [{"title": f"ASIC acts again {n}"} for n in range(5)]
        block = "\n".join(format_terms(items, _glossary()))
        self.assertEqual(block.count("### ASIC"), 1)
        self.assertIn("- Used by 5 items on this sheet.", block)

    def test_one_item_reads_as_one_item(self):
        block = "\n".join(format_terms([{"title": "ASIC acts"}], _glossary()))
        self.assertIn("- Used by 1 item on this sheet.", block)

    def test_no_section_at_all_when_nothing_matched(self):
        self.assertEqual(format_terms([{"title": "markets drifted lower"}], _glossary()), [])


class SweepIntegrationTests(unittest.TestCase):
    def _sheet(self):
        items = [{
            "title": "ASIC bans an adviser", "teaser": "The regulator acted.",
            "flag": "ACT", "source_name": "ifa", "link": "https://a.test/x",
        }]
        return format_sweep(items, glossary=_glossary())

    def test_the_item_names_its_terms(self):
        self.assertIn("      Terms: ASIC", self._sheet())

    def test_the_sheet_carries_the_explanations_before_the_record(self):
        sheet = self._sheet()
        self.assertLess(sheet.index("## Terms on this sheet"), sheet.index("## After the sweep"))


class MissingGlossaryTests(unittest.TestCase):
    def test_an_absent_file_leaves_the_sheet_working(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_glossary(Path(tmp) / "nope.json"), [])

    def test_an_unreadable_file_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "broken.json"
            broken.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_glossary(broken), [])

    def test_a_sheet_without_a_glossary_has_no_terms_section(self):
        items = [{"title": "ASIC bans an adviser", "flag": "ACT"}]
        self.assertNotIn("Terms on this sheet", format_sweep(items, glossary=[]))


class GlossaryFileTests(unittest.TestCase):
    """The shipped glossary is data, and wrong data is the failure mode here."""

    def setUp(self):
        self.terms = load_glossary()

    def test_the_shipped_glossary_loads(self):
        self.assertGreater(len(self.terms), 20)

    def test_every_entry_says_what_it_means_and_where_to_check(self):
        for entry in self.terms:
            with self.subTest(term=entry["term"]):
                self.assertTrue(entry.get("means"), entry["term"])
                self.assertTrue(entry.get("check"), entry["term"])

    def test_no_spelling_belongs_to_two_terms(self):
        seen = {}
        for entry in self.terms:
            for spelling in spellings_of(entry):
                self.assertNotIn(spelling.lower(), seen,
                                 f"{spelling} is claimed by {seen.get(spelling.lower())} too")
                seen[spelling.lower()] = entry["term"]

    def test_the_file_carries_its_own_note_about_what_it_is(self):
        note = json.loads(GLOSSARY.read_text(encoding="utf-8"))["note"]
        self.assertIn("not advice", note)

    def test_the_per_item_cap_is_a_real_cap(self):
        self.assertGreaterEqual(TERMS_PER_ITEM, 1)
        self.assertLessEqual(TERMS_PER_ITEM, 6)


if __name__ == "__main__":
    unittest.main()
