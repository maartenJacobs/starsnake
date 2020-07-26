"""
Format text/gemini elements as encoded bytes.
"""

from functools import singledispatch
from typing import List

from .elements import LINE, TextLine, PreformattedText, HeadingLine, Link, ListItem


def format_gemini_text(lines: List[LINE]) -> bytes:
    """
    Format text/gemini elements.

    :param lines: text/gemini lines.
    :return: line formatted as bytes.
    """
    return b"".join(map(_format_line, lines))


@singledispatch
def _format_line(line: TextLine) -> bytes:
    """
    Format the line as bytes.

    Note that this is the base function, arbitrarily chosen as the first instance of the generic
    function. Doctests and documentation describes behaviour for all line types instead of only
    text lines.

    >>> _format_line(TextLine(b"Is this acceptable?"))
    b'Is this acceptable?\\n'

    >>> _format_line(TextLine(b"     Is    this    acceptable?        "))
    b'     Is    this    acceptable?        \\n'

    :param line: a text/gemini line.
    :return: line formatted as bytes.
    """
    return line.line + b"\n"


@_format_line.register
def _(line: PreformattedText) -> bytes:
    return b"```\n" + line.blob + b"```\n"


@_format_line.register
def _1(line: HeadingLine) -> bytes:
    return b"#" * line.level + b" " + line.heading + b"\n"


@_format_line.register
def _2(line: Link) -> bytes:
    output = b"=> " + line.url
    if line.friendly_name:
        output += b" " + line.friendly_name
    return output + b"\n"


@_format_line.register
def _3(line: ListItem) -> bytes:
    return b"* " + line.item + b"\n"
