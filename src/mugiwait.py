"""Mugiwait"""

import argparse
import logging
import os
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Type

import discord
from dotenv import load_dotenv

import mugiclient

os.chdir(Path(__file__).parent.parent)

logger = logging.getLogger(__name__)


load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
client = mugiclient.Mugiwait(intents=intents)


@dataclass
class ParserArguments:
    """Arguments passed when running mugi."""

    log_dir: str
    debug: bool
    imgur: bool
    github: bool
    dev: bool


@client.slash_command(name="mugi")
@discord.commands.option(
    "commentface",
    description="Pick a commentface",
    autocomplete=mugiclient.get_commentfaces,
)
@discord.commands.option(
    "text",
    description="Additional text",
)
async def autocomplete_example(
    ctx: discord.ApplicationContext, commentface: str, text: str = ""
) -> None:
    """Send a commentface."""
    if not mugiclient.is_valid_interaction(ctx.interaction):
        logger.debug("Invalid interaction.")
        return
    author: discord.Member = ctx.interaction.user
    channel: discord.TextChannel = ctx.interaction.channel
    try:
        channel, thread = await mugiclient.get_channel_and_thread(ctx.interaction)
    except mugiclient.MugiError:
        logger.debug("Invalid channel/thread")
        return
    username = author.nick or author.display_name
    logger.info(
        "Command detected. Commentface: %s. Additional text: %s. Sent by: %s",
        commentface,
        text,
        username,
    )
    path = mugiclient.COMMENTFACES.get(commentface, None)
    if not path:
        logger.debug("Invalid commentface: %s", commentface)
        await ctx.interaction.response.send_message(
            f"Commentface {commentface} not found", ephemeral=True
        )
        return
    logger.debug("Getting the hook...")
    hook = await mugiclient.get_webhook(channel=channel, hook_name=str(client.user))
    logger.debug("Sending message...")
    try:
        messages = await client.build_messages_from_command(
            commentface=commentface, text=text, path=path
        )
        logger.debug("Message(s) generated")
    except mugiclient.MugiError:
        logger.error("Could not build messages")
        await ctx.interaction.response.send_message(
            "An unexpected error occurred.", ephemeral=True
        )
        return
    await ctx.interaction.response.defer()
    for mugi_message in messages:
        logger.debug("Sending message: %s", mugi_message)
        await hook.send(
            content=mugi_message.content or discord.MISSING,
            file=mugi_message.file or discord.MISSING,
            username=username,
            avatar_url=author.display_avatar,
            allowed_mentions=discord.AllowedMentions(everyone=False),
            thread=thread or discord.MISSING,
        )
    await ctx.interaction.delete_original_response()


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
    if not mugiclient.is_valid_message(message=message, client=client):
        return
    logger.info("Processing message: %s", message.content)

    try:
        mugi_messages = await client.build_messages_from_message(message.content)
        logger.debug("Message(s) generated")
    except mugiclient.MugiError:
        logger.info("Invalid message, could not build commentface")
        return

    try:
        channel, thread = await mugiclient.get_channel_and_thread(message)
    except mugiclient.MugiError:
        logger.debug("Invalid channel/thread")
        return

    logger.debug("Getting the hook...")
    hook = await mugiclient.get_webhook(channel=channel, hook_name=str(client.user))

    logger.debug("Hook found. Deleting message...")
    await message.delete()

    logger.debug("Message deleted. Sending message(s)...")
    author = await message.guild.fetch_member(message.author.id)
    for mugi_message in mugi_messages:
        logger.debug("Sending message: %s", mugi_message)
        await hook.send(
            content=mugi_message.content or discord.MISSING,
            file=mugi_message.file or discord.MISSING,
            username=author.nick or author.display_name,
            avatar_url=message.author.display_avatar,
            allowed_mentions=discord.AllowedMentions(everyone=False),
            thread=thread or discord.MISSING,
        )
    logger.debug("Message(s) sent")
    return


def main(args: Type[ParserArguments]) -> None:
    """The main loop."""
    token = os.getenv("TOKEN_DEV") if args.dev else os.getenv("TOKEN")
    if not token:
        logger.error("Discord token not found. Cannot login.")
        return
    if args.imgur:
        logger.info("Using Imgur URLs")
        client.asset_type = mugiclient.AssetType.IMGUR
    if args.github:
        logger.info("Using Github URLs")
        client.asset_type = mugiclient.AssetType.GITHUB
    client.run(token)


def create_parser() -> argparse.ArgumentParser:
    """Return the parser used by the command."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dev", action="store_true", default=False, help="run in developer mode"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False, help="additional logging"
    )
    parser.add_argument(
        "-l",
        "--log-dir",
        metavar="L",
        dest="log_dir",
        default="logs",
        help="set the log directory",
    )
    asset_type = parser.add_mutually_exclusive_group()
    asset_type.add_argument(
        "-i",
        "--imgur",
        action="store_true",
        default=False,
        help="use Imgur assets (default: file upload)",
    )
    asset_type.add_argument(
        "-g",
        "--github",
        action="store_true",
        default=False,
        help="use Github assets (default: file upload)",
    )
    return parser


if __name__ == "__main__":
    args = create_parser().parse_args(namespace=ParserArguments)
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
