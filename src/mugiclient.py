import itertools
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import Path
from typing import TypedDict

import discord
from discord.ext.commands import Bot
from discord.utils import get as get_hook

import process_reply
from resources.commentfaces import COMMENTFACES_URL

type ValidChannel = (
    discord.VoiceChannel
    | discord.StageChannel
    | discord.TextChannel
    | discord.ForumChannel
    | discord.CategoryChannel
    | discord.Thread
    | discord.PartialMessageable
    | discord.abc.Messageable
)

logger = logging.getLogger(__name__)

RE_COMMENTFACE = {
    # #commentface hovertext
    "#": re.compile(
        r"(?P<open_spoiler>\|\|)?#(?P<commentface>[^\s\|]+)"
        r"(?P<close_spoiler>\|\|)?\s?(?P<hovertext>.*)",
        flags=re.DOTALL,
    ),
    # [overlay](#commentface "hovertext")
    "[": re.compile(
        r"(?P<open_spoiler>\|\|)?\[(?P<overlay>.*)\]"
        r"\(#(?P<commentface>[^\s]+)\s?\"?(?P<hovertext>[^\"]*)\"?\)(?P<close_spoiler>\|\|)?",
        flags=re.DOTALL,
    ),
}
AVATAR_PATH = Path("src/resources/mugiwait_avatar.png")
GITHUB_PREVIEW_URL = (
    "https://raw.githubusercontent.com/r-anime/"
    "comment-face-assets/master/{relative_path}"
)
SEASONS = ("winter", "spring", "summer", "fall")
YEAR_RANGE = range(datetime.now(UTC).year, 2021, -1)
SEASONS_LIST = [f"{year} {season}" for year in YEAR_RANGE for season in SEASONS[::-1]]


class MugiError(Exception):
    """Generic exception for mugi."""


class AssetType(Enum):
    """Which assets mugi is going to use."""

    GITHUB = auto()
    IMGUR = auto()
    FILE = auto()


def get_seasonal_commentfaces_paths() -> dict[str, Path]:
    """Return a dict commentface -> file path for seasonal commentfaces.

    Only use the most recent set of seasonal commentfaces."""
    for season in SEASONS_LIST:
        if paths := list(
            Path().glob(f"src/assets/source_seasonal_faces/{season}/source/*/*.*")
        ):
            return {path.parts[-2].lower(): path for path in paths}
    raise MugiError()


def get_commentfaces_paths() -> dict[str, Path]:
    """Return a dict commentface -> file path."""
    faces = {
        path.stem.lower(): path
        for path in itertools.chain(
            Path().glob(
                "src/assets/preview/*/*.*",
            ),
            Path().glob(
                "src/assets/source_seasonal_faces/hallOfFame/*/*.*",
            ),
        )
    }
    faces |= get_seasonal_commentfaces_paths()
    return faces


COMMENTFACES = get_commentfaces_paths()


@dataclass
class MugiMessage:
    """Contents of the message to send.

    content: text of the message
    file: discord file object, defined via file path"""

    content: str = ""
    file: discord.File | None = None


class PreparedMessage(TypedDict):
    content: str
    file: discord.File
    files: list[discord.File]
    username: str
    avatar_url: discord.Asset
    allowed_mentions: discord.AllowedMentions
    thread: discord.Thread


class QueueStatus(Enum):
    IDLE = auto()
    RUNNING = auto()


async def build_imgur_message(commentface: str, spoiler: bool = False) -> MugiMessage:
    """Return the contents of the message based on Imgur assets."""
    url = COMMENTFACES_URL.get(commentface.lower(), None)
    if not url:
        raise MugiError()
    logger.debug("URL found: %s", url)
    if spoiler:
        url = f"||{url}||"
    return MugiMessage(content=url)


async def build_github_message(commentface: str, spoiler: bool = False) -> MugiMessage:
    """Return the contents of the message based on Github assets."""
    commentface_path = COMMENTFACES.get(commentface.lower(), None)
    if not commentface_path:
        raise MugiError()
    logger.debug("Path found: %s", commentface_path)
    relative_path = "/".join(commentface_path.parts[2:])  # remove src/assets
    url = GITHUB_PREVIEW_URL.format(relative_path=relative_path).replace(" ", "%20")
    if spoiler:
        url = f"||{url}||"
    return MugiMessage(content=url)


async def build_file_message(commentface: str, spoiler: bool = False) -> MugiMessage:
    """Return the contents of the message based on local assets."""
    commentface_path = COMMENTFACES.get(commentface.lower(), None)
    if not commentface_path:
        raise MugiError()
    logger.debug("Path found: %s", commentface_path)
    return MugiMessage(file=discord.File(commentface_path, spoiler=spoiler))


BUILD_MESSAGE = {
    AssetType.GITHUB: build_github_message,
    AssetType.FILE: build_file_message,
    AssetType.IMGUR: build_imgur_message,
}


class Mugiwait(Bot):
    """Mugified discord client.

    Attributes:
    * ``_asset_type``

        The type of asset to use during the session.

    Default: FILE. It can be changed to IMGUR or GITHUB with optional arguments
    when launching mugi (-i and -g, respectively).

    Accessed via the ``asset_type`` property.

    Methods:
    * ``build_messages_from_message``

        Process the contents of a valid message to extract commentface code and additional text.

        Return a list of messages to send based on parsed contents and asset type of choice.
    """

    _asset_type: AssetType = AssetType.FILE
    _message_queue: list[tuple[discord.Webhook, PreparedMessage]] = []
    queue_status: QueueStatus = QueueStatus.IDLE

    @property
    def asset_type(self) -> AssetType:
        """The type of asset to use for the session."""
        return self._asset_type

    @asset_type.setter
    def asset_type(self, value: AssetType) -> None:
        self._asset_type = value

    async def get_reference_contents(
        self,
        reply: discord.MessageReference | None = None,
        max_length: int = process_reply.MAX_REPLY_TEXT_LENGTH,
    ) -> str:
        if not reply:
            return ""
        if not reply.message_id:
            return reply.jump_url
        channel = self.get_channel(reply.channel_id)
        if not channel:
            return reply.jump_url
        try:
            message = await channel.fetch_message(reply.message_id)
            assert isinstance(message, discord.Message)
        except (AttributeError, AssertionError):
            return reply.jump_url
        ans = f"{message.author.display_name}: {reply.jump_url}"

        if message.content:
            ans += "\n> " + process_reply.process(message.content, max_length)

        return ans

    async def build_messages_from_message(
        self, text: str, reply: discord.MessageReference | None = None
    ) -> list[MugiMessage]:
        """Return a list of message contents to send and replace the processed input text."""
        reference = await self.get_reference_contents(reply) if reply else ""
        messages: list[MugiMessage] = []
        spoiler = text.startswith("||")
        prefix = text[0 + 2 * spoiler]
        match = RE_COMMENTFACE[prefix].match(text)
        if not match:
            logger.debug("No match found")
            raise MugiError()

        match_dict = match.groupdict()
        commentface = match_dict.get("commentface", "")
        if not commentface:
            logger.debug("No commentface found")
            raise MugiError()

        try:
            commentface_message = await BUILD_MESSAGE[self.asset_type](
                commentface, spoiler
            )
        except MugiError as e:
            logger.info("Invalid commentface: %s", commentface)
            raise e

        overlay = match_dict.get("overlay", "")
        if spoiler and overlay:
            overlay = apply_spoiler_to_text(overlay)
        if reply:
            overlay = f"> {reference}" + (f"\n{overlay}" if overlay else "")
        if self.asset_type == AssetType.FILE:
            commentface_message.content = overlay
        elif overlay:
            messages.append(MugiMessage(content=overlay))
        messages.append(commentface_message)

        hovertext = match_dict.get("hovertext", "")
        if spoiler and hovertext:
            hovertext = apply_spoiler_to_text(hovertext)
        if hovertext:
            messages.append(MugiMessage(content=hovertext))

        return messages

    async def build_messages_from_command(
        self, commentface: str, text: str
    ) -> list[MugiMessage]:
        """Return a list of message contents to send in response to a valid slash command."""
        path = COMMENTFACES.get(commentface.lower(), None)
        if not path:
            logger.info("Invalid commentface: %s", commentface)
            raise MugiError()
        if self.asset_type == AssetType.FILE:
            return [MugiMessage(content=text, file=discord.File(path))]
        messages: list[MugiMessage] = []
        try:
            commentface_message = await BUILD_MESSAGE[self.asset_type](commentface)
            messages.append(commentface_message)
        except MugiError as e:
            logger.error(
                "Invalid commentfaces should have been already excluded by this point"
            )
            raise e
        if text:
            messages.append(MugiMessage(content=text))
        return messages

    async def process_queue(self) -> None:
        if self.queue_status == QueueStatus.RUNNING:
            return
        if not self._message_queue:
            return
        self.queue_status = QueueStatus.RUNNING
        logger.info("Processing queue")
        while self._message_queue:
            hook, message = self._message_queue.pop(0)
            logger.info(
                "Sending message: %s",
                {k: v for k, v in message.items() if k != "username"},
            )
            await hook.send(**message)
        logger.info("Queue processed")
        self.queue_status = QueueStatus.IDLE

    def add_to_queue(
        self, messages: list[tuple[discord.Webhook, PreparedMessage]]
    ) -> None:
        self._message_queue.extend(messages)


async def get_channel_and_thread(
    channel: ValidChannel,
) -> tuple[
    ValidChannel,
    discord.Thread | None,
]:
    """Return the text channel and thread."""
    try:  # Thread
        parent_channel = channel.parent
        return parent_channel, channel
    except AttributeError:  # Not thread
        return channel, None


async def get_webhook(
    channel: ValidChannel,
    hook_name: str,
) -> discord.Webhook:
    """Return the channel webhook with given name; create one if it does not exist.

    Raise MugiError if the channel does not support webhooks."""
    try:
        while not (hook := get_hook(await channel.webhooks(), name=hook_name)):
            hook_reason = "mugi"
            with AVATAR_PATH.open("rb") as f:
                await channel.create_webhook(
                    name=hook_name, reason=hook_reason, avatar=f.read()
                )
    except AttributeError as e:
        raise MugiError from e

    return hook


async def get_commentfaces_suggestions(
    interaction: discord.Interaction, current: str
) -> list[discord.app_commands.Choice[str]]:
    """Returns a list of commentfaces that start with the characters entered so far."""
    return [
        discord.app_commands.Choice(name=commentface, value=commentface)
        for commentface in COMMENTFACES
        if commentface.startswith(current.lower())
    ]


def is_valid_message(message: discord.Message, client: discord.Client) -> bool:
    """Return whether mugi will further analyse the message contents."""
    if message.webhook_id:
        logger.debug("Ignoring webhook message")
        return False
    if message.author == client.user:
        logger.debug("Ignoring message from self")
        return False
    if not message.content or (
        all(not message.content.startswith(x) for x in RE_COMMENTFACE)
        and all(not message.content.startswith(f"||{x}") for x in RE_COMMENTFACE)
    ):
        logger.debug("Ignoring message without the right prefix")
        return False
    return True


def apply_spoiler_to_text(text: str) -> str:
    text = text.replace("||", "").strip()
    if not text:
        return ""
    return f"||{text}||"
