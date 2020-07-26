"""
Tests for text/gemini parser and formatter.
"""
from typing import cast

import pytest
from hypothesis import infer, given, strategies as st

from starsnake.text import parse_gemini_text, format_gemini_text
from starsnake.text.elements import Link, HeadingLine


@given(text=infer)
def test_parsing_does_not_raise_errors(text: bytes):
    """Parsing text should not fail spectacularly."""
    parse_gemini_text(text)


def test_empty_contents():
    """
    Parsing and formatting empty text returns empty text.
    """
    assert b"" == format_gemini_text(parse_gemini_text(b""))


@given(text=st.binary(min_size=1))
def test_parse_then_format(text: bytes):
    """
    Parsing and formatting text gives you the same text without preceding and trailing whitespace.
    """

    expected = b"".join(
        map(lambda line: cast(bytes, line).strip() + b"\n", text.split(b"\n"))
    )
    if expected and expected[-1] != ord("\n"):
        expected += b"\n"

    print(text, format_gemini_text(parse_gemini_text(text)))
    assert expected == format_gemini_text(parse_gemini_text(text))


class TestGeminiElements:
    """Test validation and construction of text/gemini elements."""

    valid_contents = st.binary().filter(lambda blob: b"\n" not in blob)
    valid_contents_ne = st.binary(min_size=1).filter(lambda blob: b"\n" not in blob)

    @given(contents=valid_contents)
    def test_formatted_elements_accept_no_newlines(self, contents: bytes):
        """Line separators are for formatting so are not accepted as contents of elements."""
        for content_index in range(len(contents) + 1):
            # Splice in a newline.
            invalid_contents = (
                contents[:content_index] + b"\n" + contents[content_index:]
            )

            with pytest.raises(ValueError, match="link URL cannot contain newlines"):
                Link(invalid_contents, b"")
            with pytest.raises(
                ValueError, match="link friendly name cannot contain newlines"
            ):
                Link(b"docs/", invalid_contents)

    @given(url=valid_contents_ne, friendly_name=valid_contents)
    def test_valid_links(self, url: bytes, friendly_name: bytes):
        """Valid links have a non-empty URL and any friendly name."""
        link = Link(url, friendly_name)
        assert link.url == url
        assert link.friendly_name == friendly_name

    def test_link_url_is_required(self):
        """Links ensure URLs are non-empty."""
        with pytest.raises(ValueError, match="link URL is required"):
            Link(b"", b"")

    @given(invalid_level=st.integers(max_value=0))
    def test_heading_with_invalid_level(self, invalid_level: int):
        """Heading lines ensure the level makes sense."""
        with pytest.raises(ValueError, match="heading level must be greater than 0"):
            HeadingLine(invalid_level, b"Blog post # 5")

    @given(valid_level=st.integers(min_value=1))
    def test_heading_text_is_required(self, valid_level: int):
        """Heading lines ensure there is a heading to display."""
        with pytest.raises(ValueError, match="heading text is required"):
            HeadingLine(valid_level, b"")
