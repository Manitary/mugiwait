import logging
import re
from enum import Enum, auto
from pathlib import Path

import discord

from resources.commentfaces import COMMENTFACES_URL

logger = logging.getLogger(__name__)

RE_COMMENTFACE = re.compile(r"\[.*\]\(#([^\s]+).*\)")
AVATAR_PATH = Path("src/resources/mugiwait_avatar.png")
GITHUB_PREVIEW_URL = (
    "https://raw.githubusercontent.com/r-anime/"
    "comment-face-assets/master/preview/{type}/{commentface}"
)


class AssetType(Enum):
    GITHUB = auto()
    IMGUR = auto()


class Mugiwait(discord.Client):
    _asset_type: AssetType = AssetType.GITHUB

    @property
    def asset_type(self) -> AssetType:
        return self._asset_type

    @asset_type.setter
    def asset_type(self, value: AssetType) -> None:
        self._asset_type = value


# Commentface formats


def get_commentface_short(text: str) -> str:
    """Return the commentface code in ``#commentface`` format."""
    return text[1:]


def get_commentface_full(text: str) -> str:
    """Return the commentface code in ``[](#commentface)`` format."""
    if match := RE_COMMENTFACE.match(text):
        return match.group(1)
    return ""


PREFIXES = {
    "#": get_commentface_short,
    "[": get_commentface_full,
}


# Commentface retrieval


def get_url_imgur(commentface: str) -> str:
    """Return the Imgur URL matching the commentface code."""
    return COMMENTFACES_URL.get(commentface, "")


def get_url_github(commentface: str) -> str:
    """Return the Github URL matching the commentface code."""
    commentface_paths = list(Path().glob(f"src/assets/preview/*/{commentface}.*"))
    if not commentface_paths:
        logger.debug("Commentface %s not found", commentface)
        return ""
    if len(commentface_paths) > 1:
        logger.warning("%d valid paths found", len(commentface_paths))
    folder, commentface = commentface_paths[0].parts[-2:]
    url = GITHUB_PREVIEW_URL.format(type=folder, commentface=commentface)
    return url


MESSAGE_FUNCTION = {
    AssetType.GITHUB: get_url_github,
    AssetType.IMGUR: get_url_imgur,
}

# Other


def is_valid_message(message: discord.Message, client: discord.Client) -> bool:
    """Return whether the bot will further analyse the message contents."""
    if message.webhook_id:
        logger.debug("Ignoring webhook message")
        return False
    if message.author == client.user:
        logger.debug("Ignoring message from self")
        return False
    if not isinstance(message.channel, discord.TextChannel):
        logger.debug("Ignoring message from wrong channel type")
        return False
    if message.content[0] not in PREFIXES:
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


def get_commentface(assets: AssetType, text: str) -> str:
    """Return the commentface code from the text, using the assets of choice."""
    code = MESSAGE_FUNCTION[assets](PREFIXES[text[0]](text))
    logger.info("Extracted code: %s", code)
    return code
