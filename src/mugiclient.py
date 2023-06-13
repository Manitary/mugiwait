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


# Commentface retrieval


def get_url_imgur(commentface: str) -> str:
    """Return the Imgur URL matching the commentface code."""
    return COMMENTFACES_URL.get(commentface, "")


IMAGES_PATHS = itertools.chain(
    (
        "src/assets/preview/*/{commentface}.*",
        "src/assets/source_seasonal_faces/hallOfFame/{commentface}.*",
        tuple(itertools.chain("src/assets/source_seasonal_faces/{season}/")),
    )
)


def get_seasonal_path(commentface: str) -> Path:
    """Return the path of a seasonal commentface.

    If not available, raise an exception.
    Only return the latest season."""
    for season in SEASONS_LIST:
        if path := list(
            Path().glob(
                f"src/assets/source_seasonal_faces/{season}/source/{commentface}/*.*"
            )
        ):
            return path[0]
    raise MugiError()


def get_url_github(commentface: str) -> str:
    """Return the Github URL matching the commentface code."""
    if commentface.startswith("seasonal"):
        try:
            commentface_paths = [get_seasonal_path(commentface)]
        except MugiError:
            logger.warning("Seasonal commentface %s not found", commentface)
            return ""
    else:
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
        logger.debug("Commentface %s not found", commentface)
        return ""
    if len(commentface_paths) > 1:
        logger.warning("%d valid paths found", len(commentface_paths))
    relative_path = "/".join(commentface_paths[0].parts[2:])  # remove src/assets
    url = GITHUB_PREVIEW_URL.format(relative_path=relative_path).replace(" ", "%20")
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


@dataclass
class ParsedMessage:
    commentface: str = ""
    overlay: str = ""
    hovertext: str = ""


def parse_code(assets: AssetType, text: str) -> ParsedMessage:
    """Return the commentface and other text matching the input."""
    prefix = text[0]
    match = RE_COMMENTFACE[prefix].match(text)
    if not match:
        logger.debug("No match found")
        return ParsedMessage()
    match_dict = match.groupdict()
    commentface = match_dict.get("commentface", "")
    if commentface:
        commentface = MESSAGE_FUNCTION[assets](commentface)
        logger.info("URL found: %s", commentface)
    overlay = match_dict.get("overlay", "")
    hovertext = match_dict.get("hovertext", "")
    message = ParsedMessage(
        commentface=commentface, overlay=overlay, hovertext=hovertext
    )
    logger.info("Message contents: %s", message)
    return message


def compose_messages(assets: AssetType, text: str) -> list[str]:
    """Return a list of message contents to send in the channel."""
    contents: list[str] = []
    parsed_text = parse_code(assets=assets, text=text)
    if not parsed_text.commentface:
        return contents
    contents.append(parsed_text.overlay)
    contents.append(parsed_text.commentface)
    contents.append(parsed_text.hovertext)
    return contents
