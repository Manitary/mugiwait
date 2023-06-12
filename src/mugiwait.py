"""Mugiwait"""

import argparse
import logging
import os
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from typing import Type

import discord
from dotenv import load_dotenv

import mugiclient

logger = logging.getLogger(__name__)

LOG_DIR = "logs"


load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
client = mugiclient.Mugiwait(intents=intents)


@dataclass
class ParserArguments:
    """Arguments passed when running the bot."""

    log_dir: str
    debug: bool
    imgur: bool
    dev: bool


@client.event
async def on_ready() -> None:
    """Change status when going online."""
    logger.debug("Logging in...")
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="mugi waiting"
        )
    )
    logger.info("Activity changed to %s", client.activity)
    logger.info("Logged in as %s", client.user)
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message) -> None:
    """React to new messages."""
    logger.debug("Message detected")
    if not mugiclient.is_valid_message(message=message, client=client):
        return
    logger.info("Processing message: %s", message.content)
    url = mugiclient.MESSAGE_FUNCTION[client.asset_type](
        mugiclient.parse_message_text(message.content)
    )
    if not url:
        logger.info("Invalid message, could not retrieve URL")
        return
    logger.info("URL found: %s", url)
    hook = await mugiclient.get_webhook(
        channel=message.channel, hook_name=str(client.user)
    )
    logger.debug("Deleting message...")
    await message.delete()
    logger.debug("Message deleted. Sending message...")
    guild = await client.fetch_guild(message.guild.id)
    author = await guild.fetch_member(message.author.id)
    await hook.send(
        content=url,
        username=author.nick or author.name,
        avatar_url=message.author.display_avatar,
    )
    logger.debug("Message sent")
    return


def main(args: Type[ParserArguments]) -> None:
    """The main loop."""
    token = os.getenv("TOKEN_DEV") if args.dev else os.getenv("TOKEN")
    if not token:
        logger.error("Discord token not found. Cannot login.")
        return
    if args.imgur:
        client.asset_type = mugiclient.AssetType.IMGUR
    client.run(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False, help="run in debug mode"
    )
    parser.add_argument(
        "-l", "--log-dir", dest="log_dir", default=LOG_DIR, help="set the log directory"
    )
    parser.add_argument(
        "-i",
        "--imgur",
        action="store_true",
        default=False,
        help="use Imgur assets (default: Github)",
    )
    parser.add_argument(
        "--dev", action="store_true", default=False, help="run in developer mode"
    )
    args = parser.parse_args(namespace=ParserArguments)
    os.makedirs(args.log_dir, exist_ok=True)
    log_file = f"{args.log_dir}/mugiwait.log"
    logging.basicConfig(
        handlers=[
            TimedRotatingFileHandler(
                filename=log_file, when="midnight", backupCount=7, encoding="UTF-8"
            )
        ],
        format="%(asctime)s | %(module)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if args.debug else logging.INFO,
    )
    logging.getLogger("discord").setLevel(logging.WARNING)
    main(args=args)
