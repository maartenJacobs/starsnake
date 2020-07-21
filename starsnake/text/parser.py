import re
from collections import namedtuple
from dataclasses import dataclass
from typing import Union, List, Optional, Iterator


GEMINI_MIME_TYPE = "text/gemini"


_nobreak_whitespace_regex = "[ \t\f\v]"
_not_whitespace_regex = "[^ \t\f\v]"
_list_item_regex = re.compile(
    f"^(?P<list_start>{_nobreak_whitespace_regex}*[*]{_nobreak_whitespace_regex}+)"
)
_heading_regex = re.compile(
    f"^(?P<level>#+){_nobreak_whitespace_regex}*(?P<heading>[^\n]+)\n$"
)
_link_regex = re.compile(
    f"^{_nobreak_whitespace_regex}*"
    f"=>{_nobreak_whitespace_regex}*"
    f"(?P<url>{_not_whitespace_regex}+)"
    f"({_nobreak_whitespace_regex}+(?P<friendly_name>[^\n]+)?)?"
    f"\n$",
    re.VERBOSE,
)


@dataclass
class Link:
    url: bytes
    friendly_name: bytes


@dataclass
class HeadingLine:
    level: int
    heading: bytes


# item: bytes
ListItem = namedtuple("ListItem", ["item"])

# item: bytes
TextLine = namedtuple("TextLine", ["line"])

# blob: bytes
PreformattedText = namedtuple("PreformattedText", ["blob"])

LINE = Union[TextLine, Link, HeadingLine, ListItem, PreformattedText]


def _index(blob: bytes, needle: bytes, start: int) -> Optional[int]:
    try:
        return blob.index(needle, start)
    except ValueError:
        return None


def _stream_lines(blob: bytes) -> Iterator[bytes]:
    start = 0
    while (line_index := _index(blob, b"\n", start)) is not None:
        yield blob[start : line_index + 1]
        start = line_index + 1


def parse_gemini_text(blob: bytes) -> List[LINE]:
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
        if match := _heading_regex.match(line.decode()):
            heading_level = len(match.group("level"))
            heading = match.group("heading")
            parsed_lines.append(HeadingLine(heading_level, heading.encode("utf-8")))
            continue

        # List items are any lines that start with a list item indicator.
        if match := _list_item_regex.match(line.decode()):
            item_start = match.group("list_start")
            parsed_lines.append(ListItem(line[len(item_start) :]))
            continue

        if match := _link_regex.match(line.decode()):
            url = match.group("url").strip().encode("utf-8")
            friendly_name = (match.group("friendly_name") or "").strip().encode("utf-8")
            parsed_lines.append(Link(url, friendly_name))
            continue

        # No other matches; regular text line.
        parsed_lines.append(TextLine(line))

    return parsed_lines
