import base64
import unittest

from src.gmail_reader import GmailAccessError, read_label


class FakeRequest:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class FakeMessages:
    def __init__(self, messages):
        self.messages = messages
        self.list_arguments = None
        self.get_arguments = []

    def list(self, **kwargs):
        self.list_arguments = kwargs
        return FakeRequest({"messages": [{"id": message["id"]} for message in self.messages]})

    def get(self, **kwargs):
        self.get_arguments.append(kwargs)
        message = next(item for item in self.messages if item["id"] == kwargs["id"])
        return FakeRequest(message)


class FakeUsers:
    def __init__(self, messages):
        self.message_resource = FakeMessages(messages)

    def messages(self):
        return self.message_resource


class FakeService:
    def __init__(self, messages):
        self.user_resource = FakeUsers(messages)

    def users(self):
        return self.user_resource


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


class GmailReaderTests(unittest.TestCase):
    def test_reads_only_requested_label_and_plain_text(self):
        message = {
            "id": "abc123",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Industry update"},
                    {"name": "From", "value": "news@example.com"},
                ],
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": encoded("Useful update.")}},
                    {"mimeType": "application/pdf", "filename": "attachment.pdf", "body": {"data": encoded("ignored")}},
                ],
            },
        }
        service = FakeService([message])

        emails = read_label(service, max_messages=1, newer_than_days=7)

        self.assertEqual(emails[0]["body"], "Useful update.")
        self.assertNotIn("ignored", emails[0]["body"])
        self.assertEqual(service.user_resource.message_resource.list_arguments["userId"], "me")
        self.assertEqual(service.user_resource.message_resource.list_arguments["q"], "label:industry-update-monitor newer_than:7d")
        self.assertEqual(service.user_resource.message_resource.get_arguments[0]["format"], "full")

    def test_rejects_other_label(self):
        with self.assertRaises(GmailAccessError):
            read_label(FakeService([]), label_name="inbox")

    def test_rejects_unbounded_limits(self):
        with self.assertRaises(GmailAccessError):
            read_label(FakeService([]), max_messages=51)
        with self.assertRaises(GmailAccessError):
            read_label(FakeService([]), newer_than_days=91)


if __name__ == "__main__":
    unittest.main()