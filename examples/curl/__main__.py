"""
Simple curl-like script to fetch Gemini pages.

Usage: cd examples && PYTHONPATH=.. python -m curl --help
"""

import argparse
import logging
import sys
from functools import partial
from typing import Set, Tuple, Optional, cast

from starsnake import client


logger = logging.getLogger("curl")


class RedirectCycleError(Exception):
    """Raised when the client has been redirected to a page that previously redirected."""


class TooManyRedirectsError(Exception):
    """Raised when the client has followed more redirects than Python can handle."""


# pylint: disable=too-few-public-methods
class Command:
    """
    Curl command to execute.

    Only 1 command is supported: making a request.
    """

    url: str

    # Logging level. Only DEBUG, INFO, WARNING and ERROR are supported.
    logging_level: int

    follow_redirects: bool

    def __init__(self, url: str, logging_level: int, follow_redirects: bool) -> None:
        super().__init__()

        assert logging_level in [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
        ]

        self.url = url
        self.logging_level = logging_level
        self.follow_redirects = follow_redirects


def _command_from_cli() -> Command:
    """
    Parse CLI arguments as a command.
    :return: parsed command.
    """

    parser = argparse.ArgumentParser(prog="curl")
    parser.add_argument("url", help="Gemini URL to fetch")
    parser.add_argument(
        "-v", "--verbosity", action="count", default=0, help="Increase output verbosity"
    )
    parser.add_argument(
        "-L", "--location", action="store_const", const=True, help="Follow redirects"
    )
    args = parser.parse_args()

    if args.verbosity == 0:
        # Default verbosity.
        logging_level = logging.ERROR
    elif args.verbosity == 1:
        logging_level = logging.WARNING
    elif args.verbosity == 2:
        logging_level = logging.INFO
    else:  # >= 3
        logging_level = logging.DEBUG

    return Command(
        url=args.url, logging_level=logging_level, follow_redirects=bool(args.location)
    )


def _make_request(
    url: str, follow_redirects: bool, prev_redirects: Set[str]
) -> Tuple[client.HeaderLine, Optional[bytes]]:
    """
    Fetch the page at url, optionally following redirects whilst preventing redirect chains.

    Malicious pages that keep redirecting are limited by `os.getrecursionlimit()`. For a simple
    curl-like script this is better than an infinite redirect but consider using an explicit
    redirect limit instead.

    :param url: Gemini URL to fetch.
    :param follow_redirects: make additional requests until response is not redirect.
    :param prev_redirects: previous redirects state. This is used to prevent infinite redirects.
    :return: fetched page
    :raises RedirectCycleError: client was redirected to page that previously resulted in a
        redirect.
    :raises TooManyRedirectsError: client was redirected too many times.
    """

    header, response = client.sync_request(url)
    if follow_redirects and header.category == client.Category.REDIRECT:
        new_url = header.meta
        if new_url in prev_redirects:
            raise RedirectCycleError(
                f"redirected to {new_url} that previously redirected"
            )

        logger.debug("following redirect to %s", header.meta)
        prev_redirects.add(new_url)

        try:
            return _make_request(new_url, follow_redirects, prev_redirects)
        except RecursionError:
            raise TooManyRedirectsError(
                f"followed too many ({len(prev_redirects)}) redirects"
            )

    logger.info("followed %d redirects to end up at %s", len(prev_redirects), url)
    return header, response


def _configure_logger(logging_level: int, logger: logging.Logger):
    """Configure a logger to use the logging level and our desired output format."""
    # pylint: disable=redefined-outer-name
    logger.setLevel(logging_level)
    handler = logging.StreamHandler()
    handler.setLevel(logging_level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def _execute_command(command: Command) -> int:
    """
    Execute the parsed command.
    :param command: command options including URL to fetch.
    :return: exit code
    """

    # Configure logging.
    configure_logger = partial(_configure_logger, command.logging_level)
    configure_logger(logger)
    configure_logger(logging.getLogger(client.constants.LOGGER_NAME))

    # Make the request.
    header, response = _make_request(command.url, cmd.follow_redirects, set())

    if header.category == client.Category.SUCCESS:
        print(cast(bytes, response).decode())
    elif header.category == client.Category.INPUT:
        input(header.meta)
        # TODO: feed answer back via next request.
    elif header.category == client.Category.REDIRECT:
        print(f"redirect to {header.meta}")
    elif header.category == client.Category.TEMPORARY_FAILURE:
        print(f"temporary failure: {header.detail}")
    elif header.category == client.Category.PERMANENT_FAILURE:
        print(f"permanent failure: {header.detail}")
    elif header.category == client.Category.CERTIFICATE_REQUIRED:
        print("certificate appears to be required?")
    else:
        print(f"unknown response: {header.category_value}{header.detail_value}")
        return 1

    return 0


if __name__ == "__main__":
    # pylint: disable=invalid-name
    cmd = _command_from_cli()
    exit_code = _execute_command(cmd)
    sys.exit(exit_code)
