import argparse
import logging
import sys
from typing import List, cast

from starsnake import client


class Command:
    """
    Curl command to execute.

    Only 1 command is supported: making a request.
    """

    url: str

    # Logging level. Only DEBUG, INFO, WARNING and ERROR are supported.
    logging_level: int

    def __init__(self, url: str, logging_level: int) -> None:
        super().__init__()

        assert logging_level in [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
        ]

        self.url = url
        self.logging_level = logging_level


def _command_from_cli() -> Command:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Gemini URL to fetch")
    parser.add_argument(
        "-v", "--verbosity", action="count", default=0, help="Increase output verbosity"
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

    return Command(url=args.url, logging_level=logging_level,)


def _execute_command(command: Command) -> int:
    # Configure logging.
    logger = logging.getLogger(client.constants.LOGGER_NAME)
    logger.setLevel(command.logging_level)
    ch = logging.StreamHandler()
    ch.setLevel(command.logging_level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Make the request.
    header, response = client.sync_request(command.url)

    if header.category == client.Category.SUCCESS:
        print(b"\n".join(cast(List[bytes], response)).decode())
    elif header.category == client.Category.INPUT:
        answer = input(header.meta)
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

    return 0


if __name__ == "__main__":
    cmd = _command_from_cli()
    ret = _execute_command(cmd)
    sys.exit(ret)
