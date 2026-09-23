"""Telegram: one weekly message plus the newsletter file; extras can be focused."""

from src.telegram_sender import MAX_BODY, format_telegram_digest, newsletter_file, tailor


def _item(n, flag="ACT", topic="Super & tax", summary="A one-line summary."):
    return {"title": f"Story {n} <b>", "link": f"https://a.test/{n}", "source_name": "ifa",
            "flag": flag, "topic": topic, "summary": "Teaser", "ai_summary": summary,
            "ai_source": "ollama:qwen3:8b"}


def test_the_weekly_newsletter_is_one_message_under_the_cap():
    message, chosen = format_telegram_digest([_item(n, "KNOW") for n in range(80)] + [_item(99)])
    assert len(message) <= MAX_BODY
    assert len(chosen) == 81
    assert message.index("Story 99") < message.index("Story 0 ")  # ACT first
    assert "more in the attached newsletter" in message
    assert "weekly newsletter" in message


def test_titles_are_escaped_and_linked():
    message, _ = format_telegram_digest([_item(1)])
    assert "Story 1 &lt;b&gt;" in message
    assert 'href="https://a.test/1"' in message
    assert "full newsletter is attached" in message


def test_an_extra_send_is_focused_on_urgency_and_category():
    items = [_item(1, "KNOW", "Super & tax"), _item(2, "ACT", "Super & tax"), _item(3, "KNOW", "Insurance")]
    assert [i["title"] for i in tailor(items, "KNOW", "super & tax")] == ["Story 1 <b>"]
    message, chosen = format_telegram_digest(items, "KNOW", "Super & tax")
    assert len(chosen) == 1 and "extra update" in message and "Only: KNOW · Super &amp; tax" in message


def test_nothing_matching_says_so():
    message, chosen = format_telegram_digest([_item(1, "ACT")], "NOTE")
    assert chosen == [] and "Nothing matched" in message


def test_the_attached_file_is_the_email_newsletter():
    assert b"Sources this week" in newsletter_file([_item(1)])


def test_preview_mode_without_settings(monkeypatch, capsys):
    from src import telegram_sender
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram_sender.send_telegram_digest([_item(1)]) is False
    assert "Preview" in capsys.readouterr().out
