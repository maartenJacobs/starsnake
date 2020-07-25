"""
Tests for text/gemini parser and formatter.
"""

from hypothesis import infer, given

from starsnake.text import parse_gemini_text


@given(text=infer)
def test_parsing_does_not_raise_errors(text: bytes):
    """Parsing text should not fail spectacularly."""
    parse_gemini_text(text)
