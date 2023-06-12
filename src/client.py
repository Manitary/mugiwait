import logging
from enum import Enum, auto
from pathlib import Path

import discord

from resources.commentfaces import COMMENTFACES_URL

logger = logging.getLogger(__name__)

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
