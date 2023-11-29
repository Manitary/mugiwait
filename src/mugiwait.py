"""Mugiwait"""

import argparse
import logging
import os
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Type

import discord
from discord.ext import tasks
from dotenv import load_dotenv

import mugiclient

os.chdir(Path(__file__).parent.parent)

logger = logging.getLogger(__name__)


load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
client = mugiclient.Mugiwait(command_prefix="", intents=intents)


@dataclass
class ParserArguments:
    log_dir: str
    debug: bool
    imgur: bool
    github: bool
    dev: bool


@client.tree.command()
@discord.app_commands.autocomplete(commentface=mugiclient.get_commentfaces_suggestions)
@discord.app_commands.describe(commentface="Pick a commentface", text="Additional text")
async def mugi(
    interaction: discord.Interaction, commentface: str, text: str = ""
) -> None:
    """Slash command to send a commentface.

    Usage: ``/mugi commentface text``

    The commentface field supports autocompletion.
    The text field is optional.
    """
    if not interaction.user:
        logger.warning("Interaction user not found")
        return
    username = interaction.user.display_name
    avatar = interaction.user.display_avatar
    logger.info(
        "Command detected: commentface = %s, additional text = %s",
        commentface,
        text,
    )
    try:
        mugi_messages = await client.build_messages_from_command(
            commentface=commentface, text=text
        )
    except mugiclient.MugiError:
        logger.info("Could not build messages")
        await interaction.response.send_message(
            f"An unexpected error occurred. Perhaps commentface {commentface} does not exist?",
            ephemeral=True,
        )
        return
    if not interaction.channel:
        logger.warning("Interaction channel not found")
        return
    try:
        channel, thread = await mugiclient.get_channel_and_thread(
            channel=interaction.channel
        )
        hook = await mugiclient.get_webhook(channel=channel, hook_name=str(client.user))
    except mugiclient.MugiError:
        logger.info("Invalid channel/thread")
        return
    await interaction.response.defer()
    messages = [
        (
            hook,
            mugiclient.PreparedMessage(
                {
                    "content": mugi_message.content or discord.utils.MISSING,
                    "file": mugi_message.file or discord.utils.MISSING,
                    "files": discord.utils.MISSING,
                    "username": username,
                    "avatar_url": avatar,
                    "allowed_mentions": discord.AllowedMentions(everyone=False),
                    "thread": thread or discord.utils.MISSING,
                }
            ),
        )
        for mugi_message in mugi_messages
    ]
    logger.info("Adding command message to the queue")
    client.add_to_queue(messages)
    await interaction.delete_original_response()


@tasks.loop(seconds=1)
async def task_loop() -> None:
    await client.process_queue()


@client.listen()
async def on_ready() -> None:
    """Change status when going online."""
    await client.tree.sync()
    task_loop.start()
    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="mugi waiting"
        )
    )
    logger.info("Logged in as %s", client.user)
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message) -> None:
    """React to new messages.

    If the message is valid and can be translated into a commentface message,
    it is deleted and mugi sends the corresponding message via webhook."""
    if not mugiclient.is_valid_message(message=message, client=client):
        return
    username = message.author.display_name
    avatar = message.author.display_avatar
    logger.info(
        "Processing message: %s",
        message.content,
    )

    try:
        mugi_messages = await client.build_messages_from_message(
            message.content, message.reference
        )
    except mugiclient.MugiError:
        logger.info("Invalid message, could not build commentface")
        return

    try:
        channel, thread = await mugiclient.get_channel_and_thread(message.channel)
        hook = await mugiclient.get_webhook(channel=channel, hook_name=str(client.user))
    except mugiclient.MugiError:
        logger.info("Invalid channel/thread")
        return

    files: list[discord.File] = []
    if mugi_messages and message.attachments:
        for attachment in message.attachments:
            file = await attachment.to_file(
                use_cached=True, spoiler=attachment.is_spoiler()
            )
            files.append(file)

    new_username = username if "clyde" not in username else "c_l_y_d_e"
    messages = [
        (
            hook,
            mugiclient.PreparedMessage(
                {
                    "content": mugi_message.content or discord.utils.MISSING,
                    "file": mugi_message.file or discord.utils.MISSING,
                    "files": discord.utils.MISSING,
                    "username": new_username,
                    "avatar_url": avatar,
                    "allowed_mentions": discord.AllowedMentions(everyone=False),
                    "thread": thread or discord.utils.MISSING,
                }
            ),
        )
        for mugi_message in mugi_messages
    ]
    if files:
        messages.append(
            (
                hook,
                mugiclient.PreparedMessage(
                    {
                        "content": discord.utils.MISSING,
                        "file": discord.utils.MISSING,
                        "files": files,
                        "username": new_username,
                        "avatar_url": avatar,
                        "allowed_mentions": discord.utils.MISSING,
                        "thread": thread or discord.utils.MISSING,
                    }
                ),
            )
        )
    logger.info("Adding message(s) to the queue")
    client.add_to_queue(messages)
    await message.delete()
    return


@client.event
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    await on_message(after)


def run(args: Type[ParserArguments]) -> None:
    token = os.getenv("TOKEN_DEV") if args.dev else os.getenv("TOKEN")
    if not token:
        logger.info("Token not found; cannot log in")
        print("Token not found; cannot log in")
        return
    if args.imgur:
        logger.info("Using Imgur URLs")
        client.asset_type = mugiclient.AssetType.IMGUR
    if args.github:
        logger.info("Using Github URLs")
        client.asset_type = mugiclient.AssetType.GITHUB
    client.run(token)


def main() -> None:
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
    run(args=args)


def create_parser() -> argparse.ArgumentParser:
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
    main()
