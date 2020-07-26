"""
Elements of the text/gemini format.
"""

from collections import namedtuple
from dataclasses import dataclass
from typing import Union


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

    def __post_init__(self):
        """Validate link."""
        if b"\n" in self.friendly_name:
            raise ValueError("link friendly name cannot contain newlines")
        if b"\n" in self.url:
            raise ValueError("link URL cannot contain newlines")
        if not self.url:
            raise ValueError("link URL is required")


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

    def __post_init__(self):
        """Validate heading line."""
        if self.level <= 0:
            raise ValueError("heading level must be greater than 0")
        if b"\n" in self.heading:
            raise ValueError("heading text cannot contain newlines")
        if not self.heading:
            raise ValueError("heading text is required")


# item: bytes
ListItem = namedtuple("ListItem", ["item"])

# item: bytes
TextLine = namedtuple("TextLine", ["line"])

# blob: bytes
PreformattedText = namedtuple("PreformattedText", ["blob"])

LINE = Union[TextLine, Link, HeadingLine, ListItem, PreformattedText]
