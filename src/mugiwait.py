"""Mugiwait"""

import logging
import os

import discord
from dotenv import load_dotenv

from src.tools import get_url

logger = logging.getLogger(__name__)

PREFIX = "#"

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready() -> None:
    """Change status when going online."""
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="mugi waiting"
        )
    )
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message) -> None:
    """React on messages."""
    if message.author == client.user:
        return
    if message.content.startswith(PREFIX):
        url = get_url(message.content[len(PREFIX) :])
        if url:
            await message.delete()
            await message.channel.send(url)
    return


def main() -> None:
    """The main loop."""
    token = os.getenv("TOKEN")
    if not token:
        return
    client.run(token)


if __name__ == "__main__":
    # Read TOKEN=[token] from a .env file
    main()
