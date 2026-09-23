"""The Telegram newsletter: split between articles, summaries labelled."""

from src.telegram_sender import MAX_BODY, format_telegram_digest


def _item(n, flag="ACT", summary=None):
    return {"title": f"Story {n} <b>", "link": f"https://a.test/{n}", "source_name": "ifa",
            "flag": flag, "summary": "Teaser " * 40, "ai_summary": summary, "ai_source": "ollama:qwen3:8b"}


def test_long_digest_splits_under_the_cap_and_numbers_the_parts():
    messages = format_telegram_digest([_item(n) for n in range(60)])
    assert len(messages) > 1
    assert all(len(m) <= 4096 for m in messages)
    assert messages[-1].endswith(f"({len(messages)} of {len(messages)})</i>")


def test_summary_is_labelled_and_titles_are_escaped():
    [message] = format_telegram_digest([_item(1, summary="ASIC banned an adviser.")])
    assert "ASIC banned an adviser." in message
    assert "Summarised by a local model (qwen3:8b)" in message
    assert "Story 1 &lt;b&gt;" in message
    assert 'href="https://a.test/1"' in message


def test_preview_mode_without_settings(monkeypatch, capsys):
    from src import telegram_sender
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram_sender.send_telegram_digest([_item(1)]) is False
    assert "Preview" in capsys.readouterr().out
