"""A failed WhatsApp send has to say what to do about it."""

import json
import unittest

from src.whatsapp_sender import explain_twilio_error


class TwilioErrorTests(unittest.TestCase):
    def test_the_closed_window_is_explained_as_the_sandbox_rule(self):
        # The one that will actually happen: a weekly digest sent more than
        # 24 hours after the phone last messaged the sandbox.
        body = json.dumps({"code": 63016, "message": "Failed to send freeform message"})
        message = explain_twilio_error(400, body)
        self.assertIn("24-hour window", message)
        self.assertIn("every 72 hours", message)
        self.assertIn("63016", message)

    def test_bad_credentials_point_at_the_two_values_to_recopy(self):
        message = explain_twilio_error(401, json.dumps({"code": 20003, "message": "Authenticate"}))
        self.assertIn("TWILIO_ACCOUNT_SID", message)
        self.assertIn("TWILIO_AUTH_TOKEN", message)

    def test_an_unknown_code_still_reports_twilios_own_message(self):
        body = json.dumps({"code": 99999, "message": "Something new went wrong"})
        message = explain_twilio_error(400, body)
        self.assertIn("Something new went wrong", message)
        self.assertIn("99999", message)

    def test_a_non_json_response_is_shown_rather_than_swallowed(self):
        message = explain_twilio_error(502, "<html>Bad Gateway</html>")
        self.assertIn("Bad Gateway", message)
        self.assertIn("502", message)


if __name__ == "__main__":
    unittest.main()
