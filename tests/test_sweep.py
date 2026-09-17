"""Tests for the weekly sweep sheet: the reading order, and the record it keeps."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.monitor import (
    email_to_item,
    format_sweep,
    resolve_sweep_path,
    sweep_filename,
    write_sweep,
)


def _week():
    """A week as the digest leaves it: every flag, two publications, one newsletter."""
    return [
        {
            "title": "ASIC bans a former adviser for ten years",
            "teaser": "The regulator banned the adviser after a review of switching advice.",
            "link": "https://a.test/asic-bans-adviser",
            "created_at": "2026-09-11T00:00:00+00:00",
            "flag": "ACT",
            "confidence": 0.81,
            "source_name": "ifa",
            "intake": "rss",
        },
        {
            "title": "FAAA responds to the draft reforms",
            "teaser": "The association welcomed parts of the package and queried others.",
            "link": "https://b.test/faaa-responds",
            "created_at": "2026-09-12T00:00:00+00:00",
            "flag": "KNOW",
            "confidence": 0.55,
            "source_name": "Professional Planner",
            "intake": "rss",
        },
        {
            "title": "Macquarie technical update: contribution caps",
            "teaser": "The monthly technical note covers the indexed caps.",
            "link": "https://mail.google.com/mail/u/0/#inbox/abc123",
            "created_at": "2026-09-13T00:00:00+00:00",
            "flag": "ACT",
            "confidence": 0.7,
            "source_name": "Macquarie Technical Services",
            "intake": "email",
        },
        {
            "title": "The ASX closed the week down 0.4 per cent",
            "teaser": "Markets drifted lower across the week.",
            "link": "https://b.test/markets",
            "created_at": "2026-09-14T00:00:00+00:00",
            "flag": "NOTE",
            "confidence": 0.9,
            "source_name": "Professional Planner",
            "intake": "rss",
        },
    ]


class SweepOrderTests(unittest.TestCase):
    def test_flags_appear_in_reading_order(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        act = sheet.index("ACT — read at the source")
        know = sheet.index("KNOW — pick what is worth it")
        note = sheet.index("NOTE — only if time remains")
        self.assertLess(act, know)
        self.assertLess(know, note)

    def test_every_item_gets_one_box_and_one_useful_question(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        self.assertEqual(sheet.count("- [ ] "), 4)
        self.assertEqual(sheet.count("Useful? [ ] yes  [ ] no"), 4)

    def test_counts_each_flag_in_its_heading(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        self.assertIn("ACT — read at the source (2)", sheet)
        self.assertIn("KNOW — pick what is worth it (1)", sheet)
        self.assertIn("NOTE — only if time remains (1)", sheet)

    def test_an_empty_flag_says_so_rather_than_vanishing(self):
        sheet = format_sweep([item for item in _week() if item["flag"] == "ACT"])
        self.assertIn("KNOW — pick what is worth it (0)", sheet)
        self.assertIn("Nothing this week.", sheet)


class SweepItemTests(unittest.TestCase):
    def test_confidence_is_shown_on_act_and_know_but_not_note(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        self.assertIn("81% confident", sheet)
        self.assertIn("55% confident", sheet)
        # 0.9 on a NOTE means "confidently background"; shown, it reads as importance.
        self.assertNotIn("90% confident", sheet)

    def test_a_newsletter_is_not_offered_as_a_public_article(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        self.assertIn("In your inbox: https://mail.google.com/", sheet)

    def test_the_newsletter_intake_value_is_the_one_the_monitor_writes(self):
        # email_to_item writes "email". A sheet testing for anything else would
        # pass its own fixtures and never fire on a real digest.
        item = email_to_item({
            "sender": "Macquarie Technical Services <a@b.test>",
            "subject": "Technical update",
            "body": "The monthly note on the indexed caps.",
            "link": "https://mail.google.com/mail/u/0/#inbox/abc123",
        })
        self.assertEqual(item["intake"], "email")
        self.assertIn("In your inbox:", format_sweep([item]))

    def test_a_hand_written_summary_is_labelled_as_one(self):
        week = _week()
        week[0]["ai_summary"] = "ASIC banned the adviser; read the media release."
        week[0]["ai_source"] = "manual"
        sheet = format_sweep(week, when=date(2026, 9, 17))
        self.assertIn("Summarised by hand: ASIC banned the adviser", sheet)

    def test_a_dead_link_is_flagged_rather_than_wasting_the_trip(self):
        week = _week()
        week[0]["link_ok"] = False
        self.assertIn("did not resolve", format_sweep(week))


class SweepRecordTests(unittest.TestCase):
    def test_the_blanks_the_habit_needs_are_there(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        self.assertIn("Started: ____", sheet)
        self.assertIn("Minutes: ____", sheet)
        self.assertIn("Useful items: ____ of 4", sheet)
        self.assertIn("Sources that earned their place:", sheet)

    def test_the_source_table_counts_what_each_publication_gave(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        self.assertIn("| Professional Planner | 0 | 1 | 1 | 2 |", sheet)
        self.assertIn("| ifa | 1 | 0 | 0 | 1 |", sheet)

    def test_the_most_act_heavy_source_is_listed_first(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17))
        table = sheet[sheet.index("| Publication |"):]
        self.assertLess(table.index("| ifa |"), table.index("| Professional Planner |"))

    def test_the_digest_date_is_named_so_a_stale_sheet_shows(self):
        sheet = format_sweep(_week(), when=date(2026, 9, 17),
                             generated_at="2026-09-14T22:42:25+00:00")
        self.assertIn("4 items from the digest of 14 Sep 2026.", sheet)

    def test_an_unreadable_digest_date_is_left_out_rather_than_guessed(self):
        sheet = format_sweep(_week(), generated_at="not a date")
        self.assertIn("4 items.", sheet)


class SweepFileTests(unittest.TestCase):
    def test_a_directory_gets_a_sheet_named_for_the_day(self):
        self.assertEqual(sweep_filename(date(2026, 9, 17)), "sweep-2026-09-17.md")
        resolved = resolve_sweep_path("output", when=date(2026, 9, 17))
        self.assertEqual(resolved, Path("output/sweep-2026-09-17.md"))

    def test_an_explicit_filename_is_taken_as_given(self):
        self.assertEqual(resolve_sweep_path("output/catch-up.md"), Path("output/catch-up.md"))

    def test_it_refuses_to_write_over_a_sheet_that_may_hold_your_ticks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sweep.md"
            write_sweep(_week(), path)
            ticked = path.read_text(encoding="utf-8").replace("- [ ]", "- [x]", 1)
            path.write_text(ticked, encoding="utf-8")

            with self.assertRaises(FileExistsError):
                write_sweep(_week(), path)
            self.assertIn("- [x]", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
