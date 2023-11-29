from typing import Generator
import discord

import pytest

from mugiclient import AssetType, Mugiwait


@pytest.fixture
def mugi() -> Generator[Mugiwait, None, None]:
    intents = discord.Intents.default()
    intents.message_content = True
    client = Mugiwait(command_prefix="", intents=intents)
    client.asset_type = AssetType.FILE
    yield client
