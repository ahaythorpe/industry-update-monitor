"""A summary, once written, has to reach the routes that are actually read."""

import json
import tempfile
import unittest
from pathlib import Path

from src.email_sender import _item_html, summary_origin
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
        # The publisher's own words stay, so the two can be compared.
        self.assertIn("The publisher&#x27;s teaser.", markup)

    def test_the_email_names_the_local_model(self):
        markup = _item_html(self._item("ollama:qwen3:8b"), "act")
        self.assertIn("Summarised by a local model (qwen3:8b)", markup)

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
