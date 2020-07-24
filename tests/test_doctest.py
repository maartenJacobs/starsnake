"""
Run doctests defined in the client library.
"""

import doctest
import sys
from typing import NoReturn

from starsnake.client import client
from starsnake.text import parser


def main() -> NoReturn:
    """
    Run doctests defined in the client library.
    """
    success = True
    for mod in [client, parser]:
        result = doctest.testmod(mod, optionflags=doctest.NORMALIZE_WHITESPACE)
        if result.failed:
            success = False

    if not success:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
