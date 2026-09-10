"""Tests for the manual AI round trip: briefing out, summaries back in."""

import json
import tempfile
import unittest
from pathlib import Path

from src.monitor import (
    BRIEF_PROMPT,
    export_json,
    format_briefing,
    import_summaries,
    parse_summaries,
    summary_ref,
    write_briefing,
)


def _items(count):
    return [
        {
            "title": f"ASIC bans director number {n}",
            "teaser": f"The regulator banned director {n} for ten years.",
            "link": f"https://a.test/asic-bans-director-{n}",
            "flag": "ACT",
            "confidence": 0.8,
            "source_name": "Test Source",
        }
        for n in range(count)
    ]


class RefTests(unittest.TestCase):
    def test_a_ref_is_stable_for_the_same_article(self):
        first = summary_ref("https://a.test/story?utm_source=news")
        second = summary_ref("https://a.test/story/")
        # Tracking noise and a trailing slash are not a different article.
        self.assertEqual(first, second)

    def test_different_articles_get_different_refs(self):
        self.assertNotEqual(summary_ref("https://a.test/one"), summary_ref("https://a.test/two"))

    def test_an_item_with_no_link_still_gets_a_ref(self):
        self.assertEqual(len(summary_ref("", "A headline with no link")), 6)


class BriefingTests(unittest.TestCase):
    def test_every_block_carries_the_safeguards_prompt(self):
        for block in format_briefing(_items(20), chunk_size=5):
            self.assertIn("summarise ONLY from the teaser given", block)
            self.assertIn(BRIEF_PROMPT.split("\n")[0], block)

    def test_items_are_chunked_without_being_split(self):
        blocks = format_briefing(_items(7), chunk_size=3)
        self.assertEqual(len(blocks), 3)
        self.assertEqual(sum(block.count("ID: ") for block in blocks), 7)

    def test_each_item_carries_its_teaser_and_link(self):
        block = format_briefing(_items(1))[0]
        self.assertIn("TEASER: The regulator banned director 0", block)
        self.assertIn("LINK: https://a.test/asic-bans-director-0", block)

    def test_an_item_with_no_teaser_says_so_rather_than_showing_nothing(self):
        block = format_briefing([{"title": "A headline", "link": "https://a.test/x"}])[0]
        self.assertIn("TEASER: (none)", block)

    def test_write_briefing_numbers_the_pastes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, blocks = write_briefing(_items(7), Path(tmp) / "briefing.md", chunk_size=3)
            text = path.read_text(encoding="utf-8")
        self.assertEqual(blocks, 3)
        self.assertIn("<!-- paste 1 of 3 -->", text)
        self.assertIn("<!-- paste 3 of 3 -->", text)


class ParseReplyTests(unittest.TestCase):
    """A chat window returns prose, bullets, bold and code fences."""

    def test_a_plain_line_is_read(self):
        parsed = parse_summaries("a1b2c3 | ACT | ASIC banned a director. | https://a.test/x")
        self.assertEqual(parsed, {"a1b2c3": "ASIC banned a director."})

    def test_bullets_bold_numbering_and_fences_are_tolerated(self):
        reply = (
            "Here you go:\n```\n"
            "- **a1b2c3** | ACT | First summary. | https://a.test/1\n"
            "2. b2c3d4 | KNOW | Second summary. | https://a.test/2\n"
            "> c3d4e5 | NOTE | Third summary.\n"
            "```\nLet me know if you want more detail."
        )
        parsed = parse_summaries(reply)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed["c3d4e5"], "Third summary.")

    def test_the_thin_teaser_answer_survives(self):
        parsed = parse_summaries("d4e5f6 | KNOW | thin — open source | https://a.test/3")
        self.assertEqual(parsed["d4e5f6"], "thin — open source")

    def test_surrounding_prose_is_not_mistaken_for_a_summary(self):
        parsed = parse_summaries("I read the items you sent | and here is my answer | below")
        self.assertEqual(parsed, {})


class ImportTests(unittest.TestCase):
    def _digest(self, tmp):
        path = Path(tmp) / "digest.json"
        export_json(_items(3), path, [{"name": "Test Source", "home": "https://a.test"}])
        return path, json.loads(path.read_text(encoding="utf-8"))

    def test_matched_summaries_are_stored_and_labelled_by_hand(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self._digest(tmp)
            ref = digest["items"][0]["ref"]
            reply = Path(tmp) / "reply.md"
            reply.write_text(f"{ref} | ACT | A summary written by hand. | https://a.test/x")

            matched, unmatched, total = import_summaries(reply, path)
            stored = json.loads(path.read_text(encoding="utf-8"))["items"][0]

        self.assertEqual((matched, unmatched, total), (1, [], 1))
        self.assertEqual(stored["ai_summary"], "A summary written by hand.")
        self.assertEqual(stored["ai_source"], "manual")
        self.assertIsNotNone(stored["ai_generated_at"])

    def test_an_unknown_id_is_reported_not_guessed_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self._digest(tmp)
            reply = Path(tmp) / "reply.md"
            reply.write_text("ffffff | ACT | A summary for an item not in this digest.")

            matched, unmatched, total = import_summaries(reply, path)
            items = json.loads(path.read_text(encoding="utf-8"))["items"]

        self.assertEqual((matched, unmatched, total), (0, ["ffffff"], 1))
        self.assertTrue(all(item["ai_summary"] is None for item in items))

    def test_a_hand_written_summary_survives_the_next_fetch(self):
        # Re-running --json every week used to be free; it must not silently
        # throw away the work of pasting a briefing into a web AI tool.
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self._digest(tmp)
            ref = digest["items"][0]["ref"]
            reply = Path(tmp) / "reply.md"
            reply.write_text(f"{ref} | ACT | Kept across a refetch. | https://a.test/x")
            import_summaries(reply, path)

            export_json(_items(3), path, None)
            after = json.loads(path.read_text(encoding="utf-8"))["items"][0]

        self.assertEqual(after["ai_summary"], "Kept across a refetch.")
        self.assertEqual(after["ai_source"], "manual")

    def test_an_item_that_left_the_digest_takes_its_summary_with_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self._digest(tmp)
            ref = digest["items"][0]["ref"]
            reply = Path(tmp) / "reply.md"
            reply.write_text(f"{ref} | ACT | Summary for an item that ages out. | https://a.test/x")
            import_summaries(reply, path)

            # Next week's digest no longer carries that story.
            export_json(_items(3)[1:], path, None)
            refs = [item["ref"] for item in json.loads(path.read_text(encoding="utf-8"))["items"]]

        self.assertNotIn(ref, refs)


if __name__ == "__main__":
    unittest.main()
