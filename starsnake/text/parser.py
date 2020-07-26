"""
Parser for text/gemini documents.

>>> parse_gemini_text(b"# Welcome to Geminispace!\\n\\n=> users/ Users directory\\n")
[HeadingLine(level=1, heading=b'Welcome to Geminispace!'),
    TextLine(line=b''),
    Link(url=b'users/', friendly_name=b'Users directory')]
"""
import logging
import re
from typing import List, Optional, Iterator

from .constants import LOGGER_NAME
from . import elements

logger = logging.getLogger(LOGGER_NAME)


NOBREAK_WHITESPACE_REGEX = "[ \t\f\v]"
NOT_WHITESPACE_REGEX = "[^ \t\f\v]"
LIST_ITEM_REGEX = re.compile(
    f"^(?P<list_start>{NOBREAK_WHITESPACE_REGEX}*[*]{NOBREAK_WHITESPACE_REGEX}+)"
)
HEADING_REGEX = re.compile(
    f"^(?P<level>#+){NOBREAK_WHITESPACE_REGEX}*(?P<heading>[^\n]+)$"
)
LINK_REGEX = re.compile(
    f"^{NOBREAK_WHITESPACE_REGEX}*"
    f"=>{NOBREAK_WHITESPACE_REGEX}*"
    f"(?P<url>{NOT_WHITESPACE_REGEX}+)"
    f"({NOBREAK_WHITESPACE_REGEX}+(?P<friendly_name>[^\n]+)?)?"
    f"$",
    re.VERBOSE,
)


def _stream_lines(blob: bytes) -> Iterator[bytes]:
    """
    Split bytes into lines (newline (\\n) character) on demand.

    >>> iter = _stream_lines(b"foo\\nbar\\n")
    >>> next(iter)
    b'foo'
    >>> next(iter)
    b'bar'
    >>> next(iter)
    Traceback (most recent call last):
        ...
    StopIteration

    >>> iter = _stream_lines(b"\\x00")
    >>> next(iter)
    b'\\x00'

    :param blob: the bytes to split.
    :return: a generated list of lines.
    """

    start = 0

    def _index(needle: bytes) -> Optional[int]:
        try:
            return blob.index(needle, start)
        except ValueError:
            return None

    line_index = _index(b"\n")
    while line_index is not None:
        yield blob[start:line_index]
        start = line_index + 1
        line_index = _index(b"\n")

    # Deal with blobs that do not end in a newline.
    if start < len(blob):
        yield blob[start:]


def parse_gemini_text(blob: bytes, encoding: str = "utf-8") -> List[elements.LINE]:
    """
    Parse Gemini text as a list of line types.

    The `LINE` type is a union of all possible line types.

    >>> parse_gemini_text(b"# Welcome to Geminispace!\\n"
    ...   b"\\n=> users/ Users directory\\n"
    ...   b"* List item 1\\n")
    [HeadingLine(level=1, heading=b'Welcome to Geminispace!'),
        TextLine(line=b''),
        Link(url=b'users/', friendly_name=b'Users directory'),
        ListItem(item=b'List item 1')]

    :param blob: the gemini text as bytes.
    :param encoding: the encoding of the text.
    :return: a list of line types.
    """

    # Special case: no text at all.
    if not blob:
        return []

    parsed_lines: List[elements.LINE] = []
    preformatting: bool = False
    preformatting_blob = b""
    for line in _stream_lines(blob):
        # Handle preformatted trigger.
        if line[:3] == b"```":
            preformatting = not preformatting
            if preformatting:
                # Reset our little blob
                preformatting_blob = b""
            else:
                parsed_lines.append(elements.PreformattedText(preformatting_blob))

        # Preformatting prevents parsing: just stuff into the blob.
        if preformatting:
            preformatting_blob += line
            continue

        try:
            decoded_line: str = line.decode(encoding=encoding)
        except UnicodeDecodeError:
            logger.warning("failed to decode line as %s", encoding)
            decoded_line = ""

        # Headers are more advanced line types.
        match = HEADING_REGEX.match(decoded_line)
        if match:
            heading_level = len(match.group("level"))
            heading = match.group("heading")
            parsed_lines.append(
                elements.HeadingLine(heading_level, heading.encode("utf-8"))
            )
            continue

        # List items are any lines that start with a list item indicator.
        match = LIST_ITEM_REGEX.match(decoded_line)
        if match:
            item_start = match.group("list_start")
            parsed_lines.append(elements.ListItem(line[len(item_start) :].strip()))
            continue

        match = LINK_REGEX.match(decoded_line)
        if match:
            url = match.group("url").strip().encode("utf-8")
            friendly_name = (match.group("friendly_name") or "").strip().encode("utf-8")
            parsed_lines.append(elements.Link(url, friendly_name))
            continue

        # No other matches; regular text line.
        parsed_lines.append(elements.TextLine(line.strip()))

    return parsed_lines
