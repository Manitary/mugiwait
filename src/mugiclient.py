import itertools
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

import discord
from discord.utils import get as get_hook

from resources.commentfaces import COMMENTFACES_URL

ValidChannel = (
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
    "#": re.compile(r"#(?P<commentface>[^\s]+)\s?(?P<hovertext>.*)"),
    # [overlay](#commentface "hovertext")
    "[": re.compile(
        r"\[(?P<overlay>.*)\]\(#(?P<commentface>[^\s]+)\s?\"?(?P<hovertext>[^\"]*)\"?\)"
    ),
}
AVATAR_PATH = Path("src/resources/mugiwait_avatar.png")
GITHUB_PREVIEW_URL = (
    "https://raw.githubusercontent.com/r-anime/"
    "comment-face-assets/master/{relative_path}"
)
SEASONS = ("winter", "spring", "summer", "fall")
YEAR_RANGE = range(datetime.utcnow().year, 2021, -1)
SEASONS_LIST = [f"{year} {season}" for year in YEAR_RANGE for season in SEASONS[::-1]]


class MugiError(Exception):
    """Generic exception for mugi."""


class AssetType(Enum):
    """Which assets mugi is going to use."""

    GITHUB = auto()
    IMGUR = auto()
    FILE = auto()


def get_seasonal_faces() -> dict[str, Path]:
    """Return a dict commentface -> file path for seasonal commentfaces.

    Only use the most recent set of seasonal commentfaces."""
    for season in SEASONS_LIST:
        if paths := list(
            Path().glob(f"src/assets/source_seasonal_faces/{season}/source/*/*.*")
        ):
            return {path.parts[-2].lower(): path for path in paths}
    raise MugiError()


def get_comment_faces() -> dict[str, Path]:
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
    faces |= get_seasonal_faces()
    return faces


COMMENTFACES = get_comment_faces()


@dataclass
class MugiMessage:
    """Contents of the message to be sent.

    content: text of the message
    file: file path (Path or str) of the file to send"""

    content: str = ""
    file: discord.File | None = None


async def build_imgur_message(commentface: str) -> MugiMessage:
    """Return the contents of the message based on Imgur assets."""
    url = COMMENTFACES_URL.get(commentface.lower(), None)
    if not url:
        raise MugiError()
    logger.debug("URL found: %s", url)
    return MugiMessage(content=url)


async def build_github_message(commentface: str) -> MugiMessage:
    """Return the contents of the message based on Github assets."""
    commentface_path = COMMENTFACES.get(commentface.lower(), None)
    if not commentface_path:
        raise MugiError()
    logger.debug("Path found: %s", commentface_path)
    relative_path = "/".join(commentface_path.parts[2:])  # remove src/assets
    url = GITHUB_PREVIEW_URL.format(relative_path=relative_path).replace(" ", "%20")
    return MugiMessage(content=url)


async def build_file_message(commentface: str) -> MugiMessage:
    """Return the contents of the message based on local assets."""
    commentface_path = COMMENTFACES.get(commentface.lower(), None)
    if not commentface_path:
        raise MugiError()
    logger.debug("Path found: %s", commentface_path)
    return MugiMessage(file=discord.File(commentface_path))


BUILD_MESSAGE = {
    AssetType.GITHUB: build_github_message,
    AssetType.FILE: build_file_message,
    AssetType.IMGUR: build_imgur_message,
}


class Mugiwait(discord.Bot):
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

    @property
    def asset_type(self) -> AssetType:
        """The type of asset to use for the session."""
        return self._asset_type

    @asset_type.setter
    def asset_type(self, value: AssetType) -> None:
        self._asset_type = value

    async def build_messages_from_message(self, text: str) -> list[MugiMessage]:
        """Return a list of message contents to send and replace the processed input text."""
        messages: list[MugiMessage] = []
        prefix = text[0]
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
            commentface_message = await BUILD_MESSAGE[self.asset_type](commentface)
        except MugiError as e:
            logger.debug("No commentface found")
            raise e

        overlay = match_dict.get("overlay", "")
        if self.asset_type == AssetType.FILE:
            commentface_message.content = overlay
        elif overlay:
            messages.append(MugiMessage(content=overlay))
        messages.append(commentface_message)

        if hovertext := match_dict.get("hovertext", ""):
            messages.append(MugiMessage(content=hovertext))

        return messages

    async def build_messages_from_command(
        self, commentface: str, text: str
    ) -> list[MugiMessage]:
        """Return a list of message contents to send in response to a valid slash command."""
        path = COMMENTFACES.get(commentface.lower(), None)
        if not path:
            logger.debug("Invalid commentface: %s", commentface)
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


async def get_channel_and_thread(
    channel: ValidChannel,
) -> tuple[ValidChannel, discord.Thread | None,]:
    """Retrieve the text channel and thread, if possible."""
    try:  # Thread
        parent_channel = channel.parent
        return parent_channel, channel
    except AttributeError:  # Not thread
        return channel, None


async def get_webhook(
    channel: ValidChannel,
    hook_name: str,
) -> discord.Webhook:
    """Return the webhook with given name; create one if it does not exist."""
    try:
        while not (hook := get_hook(await channel.webhooks(), name=hook_name)):
            hook_reason = "mugi"
            with AVATAR_PATH.open("rb") as f:
                await channel.create_webhook(
                    name=hook_name, reason=hook_reason, avatar=f.read()
                )
    except AttributeError as e:  # The channel does not support webhooks
        raise MugiError from e

    return hook


async def get_commentfaces(ctx: discord.AutocompleteContext) -> list[str]:
    """Returns a list of commentfaces that begin with the characters entered so far."""
    return [
        commentface
        for commentface in COMMENTFACES
        if commentface.startswith(ctx.value.lower())
    ]


def is_valid_message(message: discord.Message, client: discord.Client) -> bool:
    """Return whether mugi will further analyse the message contents."""
    if message.webhook_id:
        logger.debug("Ignoring webhook message")
        return False
    if message.author == client.user:
        logger.debug("Ignoring message from self")
        return False
    if not message.content or message.content[0] not in RE_COMMENTFACE:
        logger.debug("Ignoring message without the right prefix")
        return False
    if not message.guild:
        logger.debug("The message does not have a guild (?)")
        return False
    return True


def is_valid_interaction(interaction: discord.Interaction) -> bool:
    """Return False if the slash command interaction is malformed."""
    if not interaction.user:
        logger.warning("Sender of the command not found")
        return False
    if not isinstance(interaction.user, discord.Member):
        logger.warning(
            "Sender of the command is not a server member: %s", interaction.user
        )
        return False
    return True
