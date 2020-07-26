"""
Tests for the curl-like tool.
"""
import logging
from unittest.mock import patch, call, MagicMock

from examples.curl.__main__ import execute_command, Command
from starsnake.client import HeaderLine, Category, Detail


# pylint: disable=redefined-builtin
@patch("examples.curl.__main__.input")
@patch("examples.curl.__main__.client.sync_request")
def test_input(sync_request: MagicMock, input: MagicMock):
    """Input response (status code 10) should trigger a prompt and a reply."""
    prompt = "What is your name?"
    response = "Tim The Enchanter"

    input_header = HeaderLine(Category.INPUT, 1, Detail.INPUT, 0, prompt)
    success_header = HeaderLine(Category.SUCCESS, 2, Detail.SUCCESS, 0, "")
    sync_request.side_effect = [
        (input_header, None),
        (success_header, b""),
    ]

    input.return_value = response
    execute_command(Command("gemini://input.dev/", logging.ERROR, False))
    input.assert_called_once_with(prompt)

    encoded_response = response.replace(" ", "%20")
    sync_request.assert_has_calls(
        [call("gemini://input.dev/"), call("gemini://input.dev/?" + encoded_response),]
    )
