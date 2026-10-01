"""Telegram: one short weekly briefing (since 1 Oct 2026); extras can be focused."""

from src.telegram_sender import MAX_BODY, PUBLIC_DASHBOARD, TOP_STORIES, format_telegram_digest, tailor


def _item(n, flag="ACT", topic="Super & tax", summary="• What happened here. • **A key fact.** • A third point."):
    return {"title": f"Story {n} <b>", "link": f"https://a.test/{n}", "source_name": "ifa",
            "flag": flag, "topic": topic, "summary": "Teaser", "ai_summary": summary,
            "ai_source": "ollama:qwen3:8b"}


def test_the_briefing_names_the_top_stories_and_counts_the_rest():
    message, chosen = format_telegram_digest([_item(n, "KNOW") for n in range(80)] + [_item(99)])
    assert len(message) <= MAX_BODY
    assert len(chosen) == 81
    assert message.index("Story 99") < message.index("Story 0 ")  # Act now first
    assert message.count("<a href=\"https://a.test/") == TOP_STORIES
    assert f"<b>{81 - TOP_STORIES} more (1 act now):</b>" not in message
    assert f"<b>{81 - TOP_STORIES} more:</b>" in message
    assert "🔴 <b>Act now</b>" in message and "🟠 <b>Worth knowing</b>" in message
    assert f'href="{PUBLIC_DASHBOARD}"' in message


def test_each_story_is_its_headline_and_what_happened():
    message, _ = format_telegram_digest([_item(1)])
    assert "\n   What happened here." in message
    assert "A key fact" not in message  # the rest is on the dashboard


def test_a_story_the_model_could_not_read_says_so_and_ranks_below_one_it_did():
    message, _ = format_telegram_digest([_item(1, summary=""), _item(2)])
    assert "Not summarised: open the source." in message
    assert message.index("Story 2 ") < message.index("Story 1 ")


def test_act_now_stories_left_out_are_counted_separately():
    message, _ = format_telegram_digest([_item(n) for n in range(TOP_STORIES + 3)])
    assert "<b>3 more (3 act now):</b>" in message


def test_titles_are_escaped_and_linked():
    message, _ = format_telegram_digest([_item(1)])
    assert "Story 1 &lt;b&gt;" in message
    assert 'href="https://a.test/1"' in message
    assert "attached" not in message


def test_a_word_of_the_week_is_explained_from_the_glossary():
    message, _ = format_telegram_digest([_item(1, summary="• ASIC issued a stop order.")])
    assert "📖 <b>ASIC" in message


def test_an_extra_send_is_focused_on_urgency_and_category():
    items = [_item(1, "KNOW", "Super & tax"), _item(2, "ACT", "Super & tax"), _item(3, "KNOW", "Insurance")]
    assert [i["title"] for i in tailor(items, "KNOW", "super & tax")] == ["Story 1 <b>"]
    message, chosen = format_telegram_digest(items, "KNOW", "Super & tax")
    assert len(chosen) == 1 and "Advice Monitor: extra</b>" in message and "Only: KNOW · Super &amp; tax" in message


def test_nothing_matching_says_so():
    message, chosen = format_telegram_digest([_item(1, "ACT")], "NOTE")
    assert chosen == [] and "Nothing matched" in message


def test_preview_mode_without_settings(monkeypatch, capsys):
    from src import telegram_sender
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram_sender.send_telegram_digest([_item(1)]) is False
    assert "Preview" in capsys.readouterr().out


def test_a_quiet_week_says_nothing_needs_action():
    message, _ = format_telegram_digest([_item(1, "KNOW")])
    assert "Nothing this week changes what you must do." in message


def test_another_dashboard_address_can_be_given():
    message, _ = format_telegram_digest([_item(1)], dashboard="https://monitor.example/")
    assert 'href="https://monitor.example/"' in message


def test_labels_are_plain_words():
    message, _ = format_telegram_digest([_item(1, "ACT"), _item(2, "NOTE")])
    assert "1 act now · 1 background" in message
    assert "ACT —" not in message
