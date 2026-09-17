"""Tests for the manual AI round trip: briefing out, summaries back in."""

import json
import re
import tempfile
import unittest
from pathlib import Path

from src.monitor import (
    BRIEF_PROMPT,
    TOPIC_LABELS,
    export_json,
    filter_by_flag,
    filter_by_topic,
    format_briefing,
    group_items,
    import_summaries,
    parse_summaries,
    resolve_grouping,
    resolve_topics,
    slug,
    summary_ref,
    write_briefing,
    write_briefing_groups,
    BUNDLE_BOUNDARY,
    format_bundle_links,
    format_bundle_readme,
)


def _items(count):
    return [
        {
            "title": f"ASIC bans director number {n}",
            "teaser": f"The regulator banned director {n} for ten years.",
            "link": f"https://a.test/asic-bans-director-{n}",
            "created_at": "2026-09-14T00:00:00+00:00",
            "flag": "ACT",
            "confidence": 0.8,
            "source_name": "Test Source",
        }
        for n in range(count)
    ]


def _categorised():
    """One week's digest as the classifier leaves it: mixed categories."""
    categories = ["Compliance", "Compliance", "Regulation", "Key personnel movements", "General"]
    flags = ["ACT", "KNOW", "ACT", "NOTE", "KNOW"]
    items = _items(len(categories))
    for item, topic, flag in zip(items, categories, flags):
        item["topic"] = topic
        item["flag"] = flag
    return items


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

    def test_each_item_says_who_published_it_and_when(self):
        # Without these a masthead's own view reads the same as a regulator's,
        # and a stale poll reads as current.
        block = format_briefing(_items(1))[0]
        self.assertIn("SOURCE: Test Source", block)
        self.assertIn("DATE: 2026-09-14", block)

    def test_an_item_with_no_source_or_date_says_unknown(self):
        block = format_briefing([{"title": "A headline", "link": "https://a.test/x"}])[0]
        self.assertIn("SOURCE: (unknown)", block)
        self.assertIn("DATE: (unknown)", block)

    def test_the_fuller_teaser_is_preferred_over_the_display_one(self):
        # export_json writes both: the card shows the short one, the briefing
        # gets everything the feed gave us.
        block = format_briefing([{
            "title": "A headline",
            "link": "https://a.test/x",
            "teaser": "The short display version.",
            "brief_text": "The longer version the feed actually supplied, with the detail in it.",
        }])[0]
        self.assertIn("TEASER: The longer version the feed actually supplied", block)
        self.assertNotIn("The short display version.", block)

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


class CategoryTests(unittest.TestCase):
    """Briefing by category: the gap that made a paste mix unrelated subjects."""

    def test_a_category_is_matched_however_it_is_typed(self):
        resolved, unknown = resolve_topics(["compliance", " SUPER & TAX "])
        self.assertEqual(resolved, ["Compliance", "Super & tax"])
        self.assertEqual(unknown, [])

    def test_a_misspelled_category_is_reported_not_silently_dropped(self):
        resolved, unknown = resolve_topics(["Compliance", "Complience"])
        self.assertEqual((resolved, unknown), (["Compliance"], ["Complience"]))

    def test_the_classifier_fallback_label_can_be_asked_for_by_name(self):
        # "General" is not a rule, it is what topic_for returns when no rule
        # scores, so it would otherwise be the one category nobody could brief.
        self.assertIn("General", TOPIC_LABELS)
        self.assertEqual(resolve_topics(["General"])[0], ["General"])

    def test_filtering_keeps_only_the_categories_asked_for(self):
        kept = filter_by_topic(_categorised(), ["Compliance", "Regulation"])
        self.assertEqual([item["topic"] for item in kept], ["Compliance", "Compliance", "Regulation"])

    def test_an_item_with_no_category_filters_as_industry(self):
        kept = filter_by_topic([{"title": "Uncategorised", "link": "https://a.test/x"}], ["General"])
        self.assertEqual(len(kept), 1)

    def test_filtering_keeps_only_the_flags_asked_for(self):
        kept = filter_by_flag(_categorised(), {"KNOW"})
        self.assertEqual([item["flag"] for item in kept], ["KNOW", "KNOW"])

    def test_grouping_follows_the_classifiers_own_label_order(self):
        labels = [label for label, _, _ in group_items(_categorised(), ("topic",))]
        self.assertEqual(labels, ["Compliance", "Regulation", "Key personnel movements", "General"])

    def test_grouping_by_flag_runs_act_first(self):
        labels = [label for label, _, _ in group_items(_categorised(), ("flag",))]
        self.assertEqual(labels, ["ACT", "KNOW", "NOTE"])

    def test_grouping_by_both_nests_in_the_order_asked_for(self):
        # The point of the whole feature: "the KNOW items in Compliance".
        groups = group_items(_categorised(), ("topic", "flag"))
        self.assertEqual(
            [(label, name) for label, name, _ in groups],
            [("Compliance · ACT", "compliance-act"),
             ("Compliance · KNOW", "compliance-know"),
             ("Regulation · ACT", "regulation-act"),
             ("Key personnel movements · NOTE", "key-personnel-movements-note"),
             ("General · KNOW", "general-know")],
        )
        self.assertTrue(all(len(items) == 1 for _, _, items in groups))

    def test_the_reverse_order_groups_the_other_way_round(self):
        groups = group_items(_categorised(), ("flag", "topic"))
        self.assertEqual(groups[0][:2], ("ACT · Compliance", "act-compliance"))

    def test_a_combination_with_nothing_in_it_is_absent_not_empty(self):
        labels = [label for label, _, _ in group_items(_categorised(), ("topic", "flag"))]
        self.assertNotIn("Compliance · NOTE", labels)
        self.assertNotIn("Insurance · ACT", labels)

    def test_no_grouping_is_one_group_of_everything(self):
        groups = group_items(_categorised(), ())
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0][2]), 5)

    def test_a_grouping_is_read_in_the_order_given(self):
        self.assertEqual(resolve_grouping("topic,flag"), (("topic", "flag"), []))
        self.assertEqual(resolve_grouping("flag, topic"), (("flag", "topic"), []))
        self.assertEqual(resolve_grouping("TOPIC"), (("topic",), []))

    def test_an_unsupported_grouping_is_reported(self):
        self.assertEqual(resolve_grouping("topic,source"), (("topic",), ["source"]))

    def test_a_label_becomes_a_safe_filename(self):
        self.assertEqual(slug("Super & tax"), "super-tax")
        self.assertEqual(slug("Key personnel movements"), "key-personnel-movements")

    def test_one_file_per_group_each_holding_only_its_own_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = write_briefing_groups(Path(tmp) / "briefing", _categorised(), ("topic",))
            names = sorted(path.name for _, path, _, _ in written)
            compliance = next(path for label, path, _, _ in written if label == "Compliance")
            text = compliance.read_text(encoding="utf-8")

        self.assertEqual(names, ["compliance.md", "general.md", "key-personnel-movements.md", "regulation.md"])
        self.assertEqual(text.count("ID: "), 2)

    def test_a_split_paste_still_carries_the_safeguards_prompt(self):
        # The round trip is unchanged: only the grouping of pastes differs.
        with tempfile.TemporaryDirectory() as tmp:
            written = write_briefing_groups(Path(tmp) / "briefing", _categorised(), ("topic",))
            text = next(path for label, path, _, _ in written if label == "Regulation").read_text()

        self.assertIn("summarise ONLY from the teaser given", text)
        self.assertIn("<!-- Regulation — paste 1 of 1 -->", text)

    def test_a_group_too_big_for_one_paste_is_still_chunked(self):
        items = _items(7)
        for item in items:
            item["topic"] = "Compliance"
        with tempfile.TemporaryDirectory() as tmp:
            written = write_briefing_groups(Path(tmp) / "briefing", items, ("topic",), chunk_size=3)
            label, path, blocks, count = written[0]
            text = path.read_text(encoding="utf-8")

        self.assertEqual((label, blocks, count), ("Compliance", 3, 7))
        self.assertIn("<!-- Compliance — paste 3 of 3 -->", text)
        self.assertEqual(text.count("ID: "), 7)

    def test_summaries_from_a_split_briefing_import_like_any_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            digest_path = Path(tmp) / "digest.json"
            export_json(_categorised(), digest_path, None)
            digest = json.loads(digest_path.read_text(encoding="utf-8"))

            written = write_briefing_groups(Path(tmp) / "briefing", digest["items"], ("topic", "flag"))
            brief = next(path for label, path, _, _ in written if label == "Regulation · ACT")
            ref = re.search(r"ID: ([0-9a-f]{6})", brief.read_text(encoding="utf-8")).group(1)

            reply = Path(tmp) / "reply.md"
            reply.write_text(f"{ref} | ACT | From the Regulation paste. | https://a.test/x")
            matched, unmatched, total = import_summaries(reply, digest_path)
            stored = [i for i in json.loads(digest_path.read_text())["items"] if i["ref"] == ref][0]

        self.assertEqual((matched, unmatched, total), (1, [], 1))
        self.assertEqual(stored["ai_summary"], "From the Regulation paste.")
        self.assertEqual(stored["ai_source"], "manual")


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


class BundleFilesTests(unittest.TestCase):
    """IMPROVEMENTS.md item 12 — a download an AI tool can be handed as-is."""

    def test_group_write_leaves_an_entry_point_in_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "briefing"
            write_briefing_groups(directory, _items(4), ["flag"])

            readme = (directory / "README.md").read_text(encoding="utf-8")
            links = (directory / "links.md").read_text(encoding="utf-8")

            # Which digest, how much of it, and what to do with it.
            self.assertIn("Briefing bundle", readme)
            self.assertIn("4 items", readme)
            self.assertIn("--import-summaries", readme)
            # The boundary is stated in the bundle, not only in the repo.
            self.assertIn(BUNDLE_BOUNDARY, readme)
            self.assertIn("act.md", readme)

            # Every item once, with its link.
            for item in _items(4):
                self.assertIn(item["link"], links)

    def test_a_newsletter_link_is_labelled_not_offered_as_an_article(self):
        item = _items(1)[0]
        item["intake"] = "email"
        item["link"] = "https://mail.google.com/mail/u/0/#inbox/abc123"

        links = format_bundle_links([item])

        self.assertIn("opens in your own mailbox", links)
        self.assertNotIn("- Link: https://mail.google.com", links)

    def test_a_feed_item_is_offered_as_a_link(self):
        links = format_bundle_links(_items(1))

        self.assertIn("- Link: https://a.test/asic-bans-director-0", links)
        self.assertNotIn("mailbox", links)

    def test_readme_counts_files_and_pastes_it_was_given(self):
        written = [("ACT", Path("act.md"), 2, 9), ("KNOW", Path("know.md"), 1, 3)]

        readme = format_bundle_readme(written, "2026-09-14T00:00:00+00:00")

        self.assertIn("# Briefing bundle — 2026-09-14", readme)
        self.assertIn("12 items across 2 files, 3 pastes", readme)
