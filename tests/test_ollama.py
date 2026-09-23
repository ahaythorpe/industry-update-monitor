"""Tests for the local-model path: offline, against a fake Ollama on localhost."""

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.monitor import (
    OllamaUnavailable,
    ollama_generate,
    summarise_with_ollama,
)


class _Handler(BaseHTTPRequestHandler):
    """Stands in for `ollama serve`. Records what it was asked for."""

    status = 200
    reply = "abc123 | ACT | The regulator banned an adviser. | https://a.test/x"
    seen = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        _Handler.seen.append(json.loads(body))
        payload = json.dumps({"response": _Handler.reply}).encode()
        self.send_response(_Handler.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass  # keep the test output quiet


def _items(count):
    return [
        {
            "ref": f"{n:06x}",
            "title": f"ASIC bans director number {n}",
            "brief_text": f"The regulator banned director {n} for ten years.",
            "link": f"https://a.test/asic-bans-{n}",
            "source_name": "Test Source",
            "created_at": "2026-09-14T00:00:00+00:00",
            "flag": "ACT",
        }
        for n in range(count)
    ]


class FakeOllamaTests(unittest.TestCase):
    def setUp(self):
        _Handler.status = 200
        _Handler.reply = "abc123 | ACT | The regulator banned an adviser. | https://a.test/x"
        _Handler.seen = []
        self.server = HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.host = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_the_model_is_asked_for_one_whole_answer_at_temperature_zero(self):
        ollama_generate("a prompt", model="test-model", host=self.host)
        sent = _Handler.seen[0]
        self.assertEqual(sent["model"], "test-model")
        self.assertIs(sent["stream"], False)
        self.assertEqual(sent["options"]["temperature"], 0)
        self.assertIs(sent["think"], False)
        self.assertEqual(sent["prompt"], "a prompt")

    def test_one_request_per_paste_and_the_replies_come_back_joined(self):
        reply = summarise_with_ollama(_items(4), model="test-model", host=self.host, chunk_size=2)
        self.assertEqual(len(_Handler.seen), 2)
        self.assertEqual(reply.count("abc123 |"), 2)

    def test_a_later_failure_keeps_the_pastes_that_came_back(self):
        from src.monitor import OllamaPartial

        original = _Handler.do_POST

        def fail_second(handler):
            if len(_Handler.seen) >= 1:
                handler.rfile.read(int(handler.headers["Content-Length"]))
                _Handler.seen.append({})
                handler.send_response(500)
                handler.send_header("Content-Length", "0")
                handler.end_headers()
                return
            original(handler)

        _Handler.do_POST = fail_second
        try:
            with self.assertRaises(OllamaPartial) as caught:
                summarise_with_ollama(_items(4), model="test-model", host=self.host, chunk_size=2)
        finally:
            _Handler.do_POST = original
        self.assertEqual(caught.exception.partial.count("abc123 |"), 1)

    def test_the_prompt_carries_the_items_and_their_links(self):
        summarise_with_ollama(_items(1), model="test-model", host=self.host)
        prompt = _Handler.seen[0]["prompt"]
        self.assertIn("ID: 000000", prompt)
        self.assertIn("LINK: https://a.test/asic-bans-0", prompt)
        self.assertIn("summarise ONLY from the teaser given", prompt)

    def test_a_missing_model_says_how_to_pull_it(self):
        _Handler.status = 404
        with self.assertRaises(OllamaUnavailable) as caught:
            ollama_generate("a prompt", model="not-pulled", host=self.host)
        self.assertIn("ollama pull not-pulled", str(caught.exception))

    def test_another_refusal_is_reported_with_its_status(self):
        _Handler.status = 500
        with self.assertRaises(OllamaUnavailable) as caught:
            ollama_generate("a prompt", host=self.host)
        self.assertIn("500", str(caught.exception))


class WithoutOllamaTests(unittest.TestCase):
    def test_nothing_listening_says_how_to_start_it(self):
        # Port 1 is reserved and never listening.
        with self.assertRaises(OllamaUnavailable) as caught:
            ollama_generate("a prompt", host="http://127.0.0.1:1")
        self.assertIn("ollama serve", str(caught.exception))

    def test_it_refuses_to_send_items_off_this_machine(self):
        # The whole argument for this feature is that nothing leaves the laptop.
        for host in ["https://api.example.com", "http://192.168.1.50:11434"]:
            with self.subTest(host=host):
                with self.assertRaises(OllamaUnavailable) as caught:
                    ollama_generate("a prompt", host=host)
                self.assertIn("this machine only", str(caught.exception))

    def test_localhost_spellings_are_all_accepted(self):
        for host in ["http://localhost:11434", "http://127.0.0.1:11434"]:
            with self.subTest(host=host):
                # Refused for not listening, never for the host being remote.
                with self.assertRaises(OllamaUnavailable) as caught:
                    ollama_generate("a prompt", host=host.replace("11434", "1"))
                self.assertNotIn("this machine only", str(caught.exception))


class CapTests(unittest.TestCase):
    def test_a_run_past_the_paste_cap_stops_before_it_starts(self):
        with self.assertRaises(OllamaUnavailable) as caught:
            summarise_with_ollama(_items(40), host="http://127.0.0.1:1",
                                  chunk_size=1, max_blocks=3)
        self.assertIn("past the 3-paste cap", str(caught.exception))
        self.assertIn("--flags ACT,KNOW", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
