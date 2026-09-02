"""Read-only Gmail adapter for the Industry Update Monitor label."""

import base64
from email.utils import parsedate_to_datetime


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
LABEL_NAME = "industry-update-monitor"


class GmailAccessError(ValueError):
    """Raised when Gmail access is not restricted to the configured dry run."""


def _decode_body(data):
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _text_from_payload(payload):
    """Extract text/plain parts only; attachments and linked pages are ignored."""
    if payload.get("mimeType", "") == "text/plain":
        return _decode_body(payload.get("body", {}).get("data"))
    return "\n".join(
        text
        for text in (_text_from_payload(part) for part in payload.get("parts", []))
        if text
    )


def _headers(message):
    return {
        item.get("name", "").lower(): item.get("value", "")
        for item in message.get("payload", {}).get("headers", [])
    }


def _message_to_email(message):
    headers = _headers(message)
    received = headers.get("date", "")
    try:
        received = parsedate_to_datetime(received).isoformat()
    except (TypeError, ValueError, OverflowError):
        pass
    message_id = message.get("id", "")
    return {
        "id": message_id,
        "subject": headers.get("subject", ""),
        "sender": headers.get("from", ""),
        "source": headers.get("from", "") or "Gmail",
        "received": received,
        "body": _text_from_payload(message.get("payload", {})),
        "link": f"https://mail.google.com/mail/u/0/#all/{message_id}",
    }


def read_label(service, label_name=LABEL_NAME, max_messages=5, newer_than_days=14):
    """Read recent plain-text messages from one Gmail label, without writes."""
    if label_name != LABEL_NAME:
        raise GmailAccessError(f"only the {LABEL_NAME!r} label is allowed")
    if max_messages < 1 or max_messages > 50:
        raise GmailAccessError("max_messages must be between 1 and 50")
    if newer_than_days < 1 or newer_than_days > 90:
        raise GmailAccessError("newer_than_days must be between 1 and 90")

    query = f"label:{label_name} newer_than:{newer_than_days}d"
    response = service.users().messages().list(
        userId="me", q=query, maxResults=max_messages
    ).execute()
    messages = []
    for item in response.get("messages", [])[:max_messages]:
        message = service.users().messages().get(
            userId="me", id=item["id"], format="full"
        ).execute()
        messages.append(_message_to_email(message))
    return messages


def build_gmail_service(credentials_path="credentials.json", token_path="token.json"):
    """Create a read-only Gmail client using a local OAuth desktop credential."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials = None
    try:
        credentials = Credentials.from_authorized_user_file(token_path, [GMAIL_READONLY_SCOPE])
    except FileNotFoundError:
        pass
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, [GMAIL_READONLY_SCOPE])
        credentials = flow.run_local_server(port=0)
    with open(token_path, "w") as token_file:
        token_file.write(credentials.to_json())
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)