"""The link check asks whether a page exists and never opens it (SAFEGUARDS.md A)."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.monitor import check_link

SEEN = []


class _Site(BaseHTTPRequestHandler):
    def _answer(self):
        SEEN.append((self.command, self.path))
        if self.path == "/moved":
            self.send_response(301)
            self.send_header("Location", "/article")
        elif self.path == "/article":
            self.send_response(200)
        elif self.path == "/refuses-head":
            self.send_response(405)
        elif self.path == "/forbidden":
            self.send_response(403)
        elif self.path == "/gone":
            self.send_response(404)
        else:
            self.send_response(500)
        self.end_headers()
        if self.command == "GET":
            self.wfile.write(b"article text")

    do_HEAD = _answer
    do_GET = _answer

    def log_message(self, *args):
        pass


class LinkCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Site)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        SEEN.clear()

    def _no_page_opened(self):
        self.assertNotIn("GET", [method for method, _ in SEEN], SEEN)

    def test_a_live_page_is_ok_and_never_opened(self):
        result = check_link(f"{self.base}/article")
        self.assertTrue(result["ok"])
        self._no_page_opened()

    def test_a_redirect_is_followed_without_opening_the_page(self):
        result = check_link(f"{self.base}/moved")
        self.assertTrue(result["ok"])
        self.assertTrue(result["url"].endswith("/article"))
        self._no_page_opened()

    def test_a_site_refusing_head_is_left_unchecked_not_opened(self):
        for path in ("/refuses-head", "/forbidden"):
            result = check_link(f"{self.base}{path}")
            self.assertIsNone(result["ok"], path)
        self._no_page_opened()

    def test_only_not_found_counts_as_dead(self):
        self.assertIs(check_link(f"{self.base}/gone")["ok"], False)
        self._no_page_opened()

    def test_no_answer_is_unchecked(self):
        self.assertIsNone(check_link("http://127.0.0.1:9/nothing", timeout=2)["ok"])
