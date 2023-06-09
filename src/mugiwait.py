"""Mugiwait"""

from dataclasses import dataclass
import argparse
import logging
import os
from logging.handlers import TimedRotatingFileHandler

import discord
from dotenv import load_dotenv

import commentfaces

logger = logging.getLogger(__name__)

LOG_DIR = "logs"


@dataclass
class ParserArguments:
    """Arguments passed when running the bot."""

    log_dir: str
    debug: bool


PREFIX = "#"

load_dotenv()
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


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
    print("Logged in as %s", client.user)


@client.event
async def on_message(message: discord.Message) -> None:
    """React on messages."""
    logger.debug("Message detected")
    if message.author == client.user:
        logger.debug("Ignoring message from self")
        return
    if not message.content.startswith(PREFIX):
        logger.debug("Ignoring message without the right prefix")
        return
    logger.info("Processing message: %s", message.content)
    url = commentfaces.get_url(message.content[len(PREFIX) :])
    if not url:
        logger.info("Invalid message, could not retrieve URL")
        return
    logger.info("URL found: %s", url)
    logger.debug("Deleting message...")
    await message.delete()
    logger.debug("Message deleted. Sending message...")
    await message.channel.send(url)
    logger.debug("Message sent")
    return


def main() -> None:
    """The main loop."""
    token = os.getenv("TOKEN")
    if not token:
        logger.error("Discord token not found. Cannot login.")
        return
    client.run(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False, help="run in debug mode"
    )
    parser.add_argument(
        "-l", "--log-dir", dest="log_dir", default=LOG_DIR, help="set the log directory"
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

    main()
