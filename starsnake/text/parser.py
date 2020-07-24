"""
Parser for text/gemini documents.

>>> parse_gemini_text(b"# Welcome to Geminispace!\\n\\n=> users/ Users directory\\n")
[HeadingLine(level=1, heading=b'Welcome to Geminispace!'),
    TextLine(line=b''),
    Link(url=b'users/', friendly_name=b'Users directory')]
"""

import re
from collections import namedtuple
from dataclasses import dataclass
from typing import Union, List, Optional, Iterator


GEMINI_MIME_TYPE = "text/gemini"


NOBREAK_WHITESPACE_REGEX = "[ \t\f\v]"
NOT_WHITESPACE_REGEX = "[^ \t\f\v]"
LIST_ITEM_REGEX = re.compile(
    f"^(?P<list_start>{NOBREAK_WHITESPACE_REGEX}*[*]{NOBREAK_WHITESPACE_REGEX}+)"
)
HEADING_REGEX = re.compile(
    f"^(?P<level>#+){NOBREAK_WHITESPACE_REGEX}*(?P<heading>[^\n]+)\n$"
)
LINK_REGEX = re.compile(
    f"^{NOBREAK_WHITESPACE_REGEX}*"
    f"=>{NOBREAK_WHITESPACE_REGEX}*"
    f"(?P<url>{NOT_WHITESPACE_REGEX}+)"
    f"({NOBREAK_WHITESPACE_REGEX}+(?P<friendly_name>[^\n]+)?)?"
    f"\n$",
    re.VERBOSE,
)


@dataclass
class Link:
    """
    Link to a page on the web. The URL is mandatory but the friendly name is optional.

    Similar to a Markdown link, except the friendly part of the link is not necessary.
    For example, `[Hyper Kombucha Recipes](http://kom.bu.cha/hyper/)` is
    `=> http://kom.bu.cha/hyper/ Hyper Kombucha Recipes`. NB: in Markdown URLs can also be detected
    and rendered without additional formatting.

    The URL part can be relative or absolute.

    Represented as a dataclass to add documentation: links are the most essential part
    of the web.
    """

    url: bytes
    friendly_name: bytes


@dataclass
class HeadingLine:
    """
    Advanced text/gemini element specifying the header of new section.

    Levels are indicated by pound signs (or hashtags): the more pounds you put in,
    the higher the level.

    Represented as a dataclass because the `level` field is not bytes but int.
    """

    level: int
    heading: bytes


# item: bytes
ListItem = namedtuple("ListItem", ["item"])

# item: bytes
TextLine = namedtuple("TextLine", ["line"])

# blob: bytes
PreformattedText = namedtuple("PreformattedText", ["blob"])

LINE = Union[TextLine, Link, HeadingLine, ListItem, PreformattedText]


def _stream_lines(blob: bytes) -> Iterator[bytes]:
    """
    Split bytes into lines (newline (\\n) character) on demand.

    >>> iter = _stream_lines(b"foo\\nbar\\n")
    >>> next(iter)
    b'foo\\n'
    >>> next(iter)
    b'bar\\n'
    >>> next(iter)
    Traceback (most recent call last):
        ...
    StopIteration

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
        yield blob[start : line_index + 1]
        start = line_index + 1
        line_index = _index(b"\n")


def parse_gemini_text(blob: bytes) -> List[LINE]:
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
    :return: a list of line types.
    """

    parsed_lines: List[LINE] = []
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
                parsed_lines.append(PreformattedText(preformatting_blob))

        # Preformatting prevents parsing: just stuff into the blob.
        if preformatting:
            preformatting_blob += line
            continue

        # Headers are more advanced line types.
        match = HEADING_REGEX.match(line.decode())
        if match:
            heading_level = len(match.group("level"))
            heading = match.group("heading")
            parsed_lines.append(HeadingLine(heading_level, heading.encode("utf-8")))
            continue

        # List items are any lines that start with a list item indicator.
        match = LIST_ITEM_REGEX.match(line.decode())
        if match:
            item_start = match.group("list_start")
            parsed_lines.append(ListItem(line[len(item_start) :].strip(b"\n")))
            continue

        match = LINK_REGEX.match(line.decode())
        if match:
            url = match.group("url").strip().encode("utf-8")
            friendly_name = (match.group("friendly_name") or "").strip().encode("utf-8")
            parsed_lines.append(Link(url, friendly_name))
            continue

        # No other matches; regular text line.
        parsed_lines.append(TextLine(line.strip(b"\n")))

    return parsed_lines
