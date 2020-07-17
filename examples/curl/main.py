import logging
import sys
from typing import List, cast

from starsnake import client


if len(sys.argv) < 2:
    print("Usage: PYTHONPATH=. python main.py gemini_url")
    print(
        "Example: PYTHONPATH=. python main.py gemini://gemini.circumlunar.space/docs/tls-tutorial.gmi"
    )
    sys.exit(1)


# Configure logging.
logger = logging.getLogger("starsnake")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


url = sys.argv[1]

header, response = client.sync_request(url)

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
