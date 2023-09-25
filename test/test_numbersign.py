import pytest

from mugiclient import MugiError, Mugiwait


@pytest.mark.asyncio
async def test_commentface_only(mugi: Mugiwait) -> None:
    user_message = "#anko"
    bot_message = await mugi.build_messages_from_message(user_message)
    assert len(bot_message) == 1
    assert bot_message[0].content == ""
    assert bot_message[0].file
    assert bot_message[0].file.filename == "anko.gif"


@pytest.mark.asyncio
async def test_commentface_with_hovertext(mugi: Mugiwait) -> None:
    user_message = "#anko test"
    bot_message = await mugi.build_messages_from_message(user_message)
    assert len(bot_message) == 2
    assert bot_message[0].content == ""
    assert bot_message[0].file
    assert bot_message[0].file.filename == "anko.gif"
    assert bot_message[1].content == "test"
    assert bot_message[1].file is None


@pytest.mark.asyncio
async def test_invalid_commentface(mugi: Mugiwait) -> None:
    user_message = "#aanko"
    with pytest.raises(MugiError):
        await mugi.build_messages_from_message(user_message)


@pytest.mark.asyncio
async def test_hovertext_with_newline(mugi: Mugiwait) -> None:
    user_message = "#anko message\nwith\nnewlines"
    bot_message = await mugi.build_messages_from_message(user_message)
    assert len(bot_message) == 2
    assert bot_message[0].content == ""
    assert bot_message[1].content == "message\nwith\nnewlines"


@pytest.mark.asyncio
async def test_spoiler_commentface(mugi: Mugiwait) -> None:
    user_message = "||#anko||"
    bot_message = await mugi.build_messages_from_message(user_message)
    assert len(bot_message) == 1
    assert bot_message[0].content == ""
    assert bot_message[0].file
    assert bot_message[0].file.spoiler


@pytest.mark.asyncio
async def test_spoiler_commentface_with_hovertext(mugi: Mugiwait) -> None:
    user_message = "||#anko test||"
    bot_message = await mugi.build_messages_from_message(user_message)
    assert len(bot_message) == 2
    assert bot_message[0].content == ""
    assert bot_message[0].file
    assert bot_message[0].file.spoiler
    assert bot_message[1].content == "||test||"


@pytest.mark.asyncio
async def test_spoiler_commentface_but_not_hovertext(mugi: Mugiwait) -> None:
    user_message = "||#anko|| test"
    bot_message = await mugi.build_messages_from_message(user_message)
    assert len(bot_message) == 2
    assert bot_message[0].content == ""
    assert bot_message[0].file
    assert bot_message[0].file.spoiler
    assert bot_message[1].content == "||test||"
