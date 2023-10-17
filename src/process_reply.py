import logging
import re

logger = logging.getLogger(__name__)

RE_SPOILER_DELIMITER = re.compile(r"(?<!\|)\|\|")

RE_USER = re.compile(r"(<@!?\d+>)")
RE_MESSAGE_LINK = re.compile(r"(<?https://discord\.com/channels/\d+/\d+/\d+>?)")
RE_EMOJI = re.compile(r"(<:\w{2,32}:\d+>)")

ALL_RE = re.compile(r"|".join(x.pattern for x in (RE_USER, RE_MESSAGE_LINK, RE_EMOJI)))

MAX_REPLY_TEXT_LENGTH = 75
VISUAL_LENGTH = {RE_USER: 1, RE_MESSAGE_LINK: 35, RE_EMOJI: 5}


def split_pattern(text: str, pattern: re.Pattern[str] = ALL_RE) -> list[str]:
    return list(filter(lambda x: x is not None, pattern.split(text)))


def trim_message(text: str, n: int = MAX_REPLY_TEXT_LENGTH) -> str:
    """Trim a string to (about) the given length while preserving certain discord objects."""
    l = 0
    ans = ""
    for i, part in enumerate(split_pattern(text)):
        if i % 2:
            for pattern, length in VISUAL_LENGTH.items():
                if pattern.match(part):
                    l += length
                    ans += part
                    break
        else:
            ans += part[: min(len(part), n - l)]
            l += len(part)
        if l >= n:
            break
    return ans


def fix_spoilers(text: str) -> str:
    """Attempt to preserve spoilers when message contents are cut to ``text``.

    Due to how markdown syntax works, this may fail on specific edge cases,
    and when interacting with other (potentially broken) syntax like code blocks.

    It works generally fine for our scope, erring on the side of caution,
    as most messages don't use very intricate markdown."""
    if len(RE_SPOILER_DELIMITER.findall(text)) % 2:
        return f"{text}||"
    return text


def process(text: str, n: int = MAX_REPLY_TEXT_LENGTH) -> str:
    ans = fix_spoilers(trim_message(text, n)).replace("\n", " ")
    logger.info("Processing reply\nOriginal: %s\nProcessed: %s", text, ans)
    return ans
