import pytest

from mugiclient import Mugiwait


@pytest.mark.asyncio
async def test_valid_commentface_only(mugi: Mugiwait) -> None:
    user_message = "#anko"
    bot_message = await mugi.build_messages_from_message(user_message)
    assert len(bot_message) == 1
    assert bot_message[0].content == ""
    assert bot_message[0].file
    assert bot_message[0].file.filename == "anko.gif"
