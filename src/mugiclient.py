import itertools
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

import discord

from resources.commentfaces import COMMENTFACES_URL

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


@dataclass
class MugiMessage:
    """Contents of the message to be sent.

    content: text of the message
    file: file path (Path or str) of the file to send"""

    content: str = ""
    file: discord.File | None = None

    @property
    def contents(self) -> dict[str, str | discord.File | None]:
        """Return the contents as dictionary."""
        # dict keys must match ``discord.Webhook.send`` arguments
        data = {
            "content": self.content,
            "file": self.file,
        }
        return {k: v for k, v in data.items() if v}


def build_imgur_message(commentface: str) -> MugiMessage:
    """Return the contents of the message based on Imgur assets."""
    return MugiMessage(content=COMMENTFACES_URL.get(commentface, ""))


def build_github_message(commentface: str) -> MugiMessage:
    """Return the contents of the message based on Github assets."""
    commentface_path = get_commentface_file_path(commentface)
    if not commentface_path:
        return MugiMessage()
    relative_path = "/".join(commentface_path.parts[2:])  # remove src/assets
    url = GITHUB_PREVIEW_URL.format(relative_path=relative_path).replace(" ", "%20")
    return MugiMessage(content=url)


def build_file_message(commentface: str) -> MugiMessage | None:
    """Return the contents of the message based on local assets."""
    commentface_path = get_commentface_file_path(commentface)
    if not commentface_path:
        return None
    return MugiMessage(file=discord.File(commentface_path))


BUILD_MESSAGE = {
    AssetType.GITHUB: build_github_message,
    AssetType.FILE: build_file_message,
    AssetType.IMGUR: build_imgur_message,
}


class Mugiwait(discord.Client):
    """Mugified discord client.

    Attributes:
    * ``_asset_type``

        The type of asset to use during the session.

    Defaults to FILE, can be changed to IMGUR or GITHUB with optional arguments
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

    def build_messages_from_message(self, text: str) -> list[MugiMessage]:
        """Return a list of message contents to send and replace the processed input text."""
        messages: list[MugiMessage] = []
        prefix = text[0]
        match = RE_COMMENTFACE[prefix].match(text)
        if not match:
            logger.debug("No match found")
            return messages
        match_dict = match.groupdict()
        commentface = match_dict.get("commentface", "")
        if not commentface:
            logger.debug("No commentface found")
            return messages

        commentface_message = BUILD_MESSAGE[self.asset_type](commentface)
        if not commentface_message:
            logger.debug("No commentface found")
            return messages

        overlay = match_dict.get("overlay", "")
        commentface_message.content = overlay
        messages.append(commentface_message)

        if hovertext := match_dict.get("hovertext", ""):
            messages.append(MugiMessage(content=hovertext))

        return messages


def get_seasonal_path(commentface: str) -> Path:
    """Return the path of a seasonal commentface.

    If not available, raise an exception.

    Only return the latest possible season."""
    for season in SEASONS_LIST:
        if path := list(
            Path().glob(
                f"src/assets/source_seasonal_faces/{season}/source/{commentface}/*.*"
            )
        ):
            return path[0]
    raise MugiError()


def get_commentface_file_path(commentface: str) -> Path | None:
    """Return the asset file path for the given commentface code, if it exists."""
    if commentface.startswith("seasonal"):
        try:
            return get_seasonal_path(commentface)
        except MugiError:
            logger.warning("Seasonal commentface %s not found", commentface)
            return None
    commentface_paths = list(
        itertools.chain(
            Path().glob(
                f"src/assets/preview/*/{commentface}.*",
            ),
            Path().glob(
                f"src/assets/source_seasonal_faces/hallOfFame/*/{commentface}.*",
            ),
        )
    )
    if not commentface_paths:
        logger.info("Commentface %s not found", commentface)
        return None
    if len(commentface_paths) > 1:
        logger.warning("%d valid paths found", len(commentface_paths))
    return commentface_paths[0]


def is_valid_message(message: discord.Message, client: discord.Client) -> bool:
    """Return whether mugi will further analyse the message contents."""
    if message.webhook_id:
        logger.debug("Ignoring webhook message")
        return False
    if message.author == client.user:
        logger.debug("Ignoring message from self")
        return False
    if not isinstance(message.channel, discord.TextChannel):
        logger.debug("Ignoring message from wrong channel type")
        return False
    if not message.content or message.content[0] not in RE_COMMENTFACE:
        logger.debug("Ignoring message without the right prefix")
        return False
    if not message.guild:
        logger.debug("The message does not have a guild (?)")
        return False
    return True


async def get_webhook(channel: discord.TextChannel, hook_name: str) -> discord.Webhook:
    """Return the webhook with given name; create one if it does not exist."""
    hook_reason = "mugi"
    while not (hook := discord.utils.get(await channel.webhooks(), name=hook_name)):
        with AVATAR_PATH.open("rb") as f:
            await channel.create_webhook(
                name=hook_name, reason=hook_reason, avatar=f.read()
            )

    return hook
