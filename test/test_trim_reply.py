from process_reply import (
    MAX_REPLY_TEXT_LENGTH,
    RE_EMOJI,
    RE_MESSAGE_LINK,
    VISUAL_LENGTH,
    trim_message,
)

SAMPLE_DISCORD_LINK = (
    "https://discord.com/channels/1041100416408100924/"
    "1041100416928198739/1163903523835097148"
)
SAMPLE_EMOJI = "<:mugiwait:1163890830956843048>"


def test_trim_no_special() -> None:
    message = "a" * MAX_REPLY_TEXT_LENGTH * 2
    expected = "a" * MAX_REPLY_TEXT_LENGTH
    real = trim_message(message)
    assert expected == real


def test_trim_with_discord_link() -> None:
    message = f"{SAMPLE_DISCORD_LINK} {'a' * MAX_REPLY_TEXT_LENGTH}"
    expected = (
        SAMPLE_DISCORD_LINK
        + " "
        + "a" * (MAX_REPLY_TEXT_LENGTH - VISUAL_LENGTH[RE_MESSAGE_LINK] - 1)
    )
    real = trim_message(message)
    assert expected == real


def test_trim_with_emoji() -> None:
    message = (
        "a" * (MAX_REPLY_TEXT_LENGTH - 10)
        + " "
        + SAMPLE_EMOJI
        + " "
        + "a" * MAX_REPLY_TEXT_LENGTH
    )
    expected = (
        "a" * (MAX_REPLY_TEXT_LENGTH - 10)
        + " "
        + SAMPLE_EMOJI
        + " "
        + "a" * (8 - VISUAL_LENGTH[RE_EMOJI])
    )
    real = trim_message(message)
    assert expected == real
