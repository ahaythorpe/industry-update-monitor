"""A summary, once written, has to reach the routes that are actually read."""

import json
import tempfile
import unittest
from pathlib import Path

from src.email_sender import _build_html_digest, _item_html, summary_origin
from src.monitor import attach_saved_summaries, export_json, import_summaries
from src.whatsapp_sender import _item_block


def _digest_with_summary(directory, summary="ASIC banned the adviser.", origin="manual"):
    path = Path(directory) / "digest.json"
    path.write_text(json.dumps({
        "items": [{
            "id": "https://a.test/asic-bans-adviser",
            "ref": "abc123",
            "title": "ASIC bans an adviser",
            "link": "https://a.test/asic-bans-adviser",
            "ai_summary": summary,
            "ai_source": origin,
            "ai_generated_at": "2026-09-17T00:00:00+00:00",
        }],
    }), encoding="utf-8")
    return path


class OriginTests(unittest.TestCase):
    def test_a_hand_written_summary_says_so(self):
        self.assertEqual(summary_origin("manual"), "Summarised by hand")

    def test_a_local_model_is_named(self):
        self.assertEqual(summary_origin("ollama:qwen3:8b"),
                         "Summarised by a local model (qwen3:8b)")

    def test_an_unrecorded_origin_is_admitted_rather_than_called_a_summary(self):
        # A bare "Summary" reads as the tool's own work, and this tool does not
        # write summaries.
        self.assertIn("origin not recorded", summary_origin(None))


class CarryOverTests(unittest.TestCase):
    def test_a_fresh_fetch_gets_its_summaries_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            digest = _digest_with_summary(tmp)
            fetched = [{"title": "ASIC bans an adviser",
                        "link": "https://a.test/asic-bans-adviser?utm_source=feed"}]
            self.assertEqual(attach_saved_summaries(fetched, digest), 1)
            self.assertEqual(fetched[0]["ai_summary"], "ASIC banned the adviser.")
            self.assertEqual(fetched[0]["ai_source"], "manual")

    def test_an_item_with_no_saved_summary_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            digest = _digest_with_summary(tmp)
            fetched = [{"title": "Something else", "link": "https://a.test/other"}]
            self.assertEqual(attach_saved_summaries(fetched, digest), 0)
            self.assertNotIn("ai_summary", fetched[0])

    def test_no_digest_yet_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(attach_saved_summaries([{"link": "https://a.test/x"}],
                                                    Path(tmp) / "nothing.json"), 0)


class DeliveryTests(unittest.TestCase):
    """IMPROVEMENTS.md item 4: the dashboard had it, the read routes did not."""

    def _item(self, origin="manual"):
        return {
            "title": "ASIC bans an adviser", "summary": "The publisher's teaser.",
            "ai_summary": "ASIC banned the adviser for ten years.", "ai_source": origin,
            "link": "https://a.test/x", "source_name": "ifa", "flag": "ACT",
            "confidence": 0.8,
        }

    def test_the_email_carries_the_summary_and_says_who_wrote_it(self):
        markup = _item_html(self._item(), "act")
        self.assertIn("ASIC banned the adviser for ten years.", markup)
        self.assertIn("Summarised by hand", markup)
        # Decluttered 23 Sep 2026: with a summary, the teaser is left out of
        # the email; the article button is one tap away.
        self.assertNotIn("The publisher&#x27;s teaser.", markup)

    def test_dot_points_become_a_list_with_the_key_fact_bold(self):
        item = self._item("ollama:qwen3:8b")
        item["ai_summary"] = "• **ASIC banned** the adviser. • Advisers should **check** their AFSL."
        markup = _item_html(item, "act")
        self.assertEqual(markup.count("<li"), 2)
        self.assertIn("<b>ASIC banned</b>", markup)

    def test_no_summary_shows_the_teaser(self):
        item = self._item()
        del item["ai_summary"]
        self.assertIn("The publisher&#x27;s teaser.", _item_html(item, "act"))

    def test_the_email_names_the_local_model(self):
        markup = _item_html(self._item("ollama:qwen3:8b"), "act")
        self.assertIn("Summarised by a local model (qwen3:8b)", markup)

    def test_every_story_in_the_newsletter_shows_its_dot_points(self):
        # 23 Sep 2026: KNOW and NOTE stories were one line each, so reading the
        # week meant opening every article. Now each carries its summary.
        act = self._item()
        know = dict(self._item(), flag="KNOW", title="Super fund merges",
                    ai_summary="• **Two funds** merge in March. • Members move on **1 July**.")
        page = _build_html_digest({"ACT": [act], "KNOW": [know], "NOTE": []})
        self.assertIn("<b>Two funds</b> merge in March.", page)
        self.assertIn("Members move on <b>1 July</b>.", page)
        self.assertIn("ASIC banned the adviser for ten years.", page)

    def test_only_act_stories_say_to_check_the_source(self):
        self.assertIn("Check the source before acting.", _item_html(self._item(), "act"))
        know = dict(self._item(), flag="KNOW")
        self.assertNotIn("Check the source", _item_html(know, "know"))

    def test_category_rows_jump_to_their_section(self):
        page = _build_html_digest({"ACT": [dict(self._item(), topic="Super & tax")], "KNOW": [], "NOTE": []},
                                  interactive=True)
        self.assertIn('href="#cat-super-tax"', page)
        self.assertIn('id="cat-super-tax"', page)

    def test_stories_the_model_could_not_read_are_listed_apart(self):
        teaser_only = dict(self._item(), title="Riskinfo story", body_source="feed_summary")
        thin = dict(self._item(), title="Thin story", ai_summary="• Thin story. Open the source.")
        read = dict(self._item(), title="Read fine", body_source="feed_content")
        page = _build_html_digest({"ACT": [teaser_only, thin, read], "KNOW": [], "NOTE": []})
        section = page[page.index("Read these yourself (2)"):]
        self.assertIn("Riskinfo story", section[:2000])
        self.assertIn("only shares a teaser", section[:2000])
        self.assertIn("Too little text", section[:2000])
        self.assertNotIn("Read fine →", page)

    def test_an_acronym_in_a_story_is_explained_in_a_box(self):
        item = dict(self._item(), title="Treasury opens CSLR levy consultation")
        markup = _item_html(item, "act")
        self.assertIn("CSLR (Compensation Scheme of Last Resort)", markup)
        self.assertIn("📖", markup)

    def test_the_jargon_buster_lists_each_term_once(self):
        one = dict(self._item(), title="CSLR levy rises")
        two = dict(self._item(), title="FAAA responds to CSLR levy")
        page = _build_html_digest({"ACT": [one, two], "KNOW": [], "NOTE": []})
        buster = page[page.index("Jargon buster"):]
        self.assertEqual(buster.count("<b>CSLR (Compensation Scheme of Last Resort)</b>"), 1)
        self.assertIn("FAAA (Financial Advice Association Australia)", buster)

    def test_the_email_is_a_short_alert_once_the_dashboard_is_online(self):
        import os
        from unittest import mock
        from src.email_sender import build_email
        act = dict(self._item(), topic="Regulation")
        know = dict(self._item(), flag="KNOW", title="Super fund merges", topic="Super & tax")
        grouped = {"ACT": [act], "KNOW": [know], "NOTE": []}
        with mock.patch.dict(os.environ, {"DASHBOARD_URL": "https://monitor.example/"}):
            short = build_email(grouped)
        with mock.patch.dict(os.environ, {"DASHBOARD_URL": ""}):
            full = build_email(grouped)
        self.assertIn("Open this week on the dashboard", short)
        self.assertIn("ASIC bans an adviser", short)
        self.assertNotIn("Super fund merges", short)  # only Act now is listed
        self.assertIn("💰 Super &amp; tax 1", short)
        self.assertIn("Super fund merges", full)
        self.assertNotIn("Open this week on the dashboard", full)

    def test_the_whatsapp_message_carries_it_too(self):
        body = _item_block(1, self._item())
        self.assertIn("ASIC banned the adviser for ten years.", body)
        self.assertIn("Summarised by hand", body)
        self.assertIn("The publisher's teaser.", body)

    def test_an_item_without_a_summary_is_unchanged(self):
        item = self._item()
        del item["ai_summary"], item["ai_source"]
        self.assertNotIn("Summarised", _item_html(item, "act"))
        self.assertNotIn("Summarised", _item_block(1, item))


class ImportOriginTests(unittest.TestCase):
    def test_the_importer_records_who_wrote_the_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            digest = Path(tmp) / "digest.json"
            export_json([{"title": "ASIC bans an adviser", "link": "https://a.test/x",
                          "summary": "teaser", "flag": "ACT"}], digest)
            ref = json.loads(digest.read_text())["items"][0]["ref"]
            reply = Path(tmp) / "reply.md"
            reply.write_text(f"{ref} | ACT | A model wrote this. | https://a.test/x")

            import_summaries(reply, digest, origin="ollama:qwen3:8b")
            item = json.loads(digest.read_text())["items"][0]
            self.assertEqual(item["ai_source"], "ollama:qwen3:8b")
            self.assertEqual(item["ai_summary"], "A model wrote this.")

    def test_a_hand_paste_is_still_labelled_manual_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            digest = Path(tmp) / "digest.json"
            export_json([{"title": "ASIC bans an adviser", "link": "https://a.test/x",
                          "summary": "teaser", "flag": "ACT"}], digest)
            ref = json.loads(digest.read_text())["items"][0]["ref"]
            reply = Path(tmp) / "reply.md"
            reply.write_text(f"{ref} | ACT | I wrote this myself. | https://a.test/x")

            import_summaries(reply, digest)
            self.assertEqual(json.loads(digest.read_text())["items"][0]["ai_source"], "manual")


if __name__ == "__main__":
    unittest.main()


class NewsletterTests(unittest.TestCase):
    def test_every_article_in_the_sources_list_has_its_own_visit_link(self):
        from src.email_sender import _build_html_digest
        items = [
            {"title": "One", "link": "https://a.test/1", "source_name": "ifa", "flag": "ACT"},
            {"title": "Two", "link": "https://a.test/2", "source_name": "ifa", "flag": "KNOW"},
        ]
        markup = _build_html_digest({"ACT": items[:1], "KNOW": items[1:], "NOTE": []})
        self.assertIn("Sources this week", markup)
        self.assertEqual(markup.count("Visit →"), 2)
        self.assertIn('href="https://a.test/2"', markup)
