import argparse
import asyncio
import logging
import time
from functools import partial
from pathlib import Path
import random
from typing import Set, Optional, cast, Iterator, Tuple, List
from urllib.parse import ParseResult, urlparse

from starsnake import client
from starsnake.text import parser

logger = logging.getLogger("downloader")


class Command:
    """
    Curl command to execute.

    Only 1 command is supported: downloading all pages of a URL.
    """

    url: str

    # Logging level. Only DEBUG, INFO, WARNING and ERROR are supported.
    logging_level: int

    output_directory: Path

    num_of_workers: int

    def __init__(
        self, url: str, logging_level: int, output_directory: Path, num_of_workers: int
    ) -> None:
        super().__init__()

        assert logging_level in [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
        ]
        assert output_directory.exists()
        assert output_directory.is_dir()
        assert num_of_workers > 0

        self.url = url
        self.logging_level = logging_level
        self.output_directory = output_directory
        self.num_of_workers = num_of_workers


def _command_from_cli() -> Command:
    """
    Parse CLI arguments as a command.
    :return: parsed command.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Gemini URL to crawl and download")
    parser.add_argument(
        "output", nargs="?", default=".", help="Output directory for fetched pages"
    )
    parser.add_argument(
        "-v", "--verbosity", action="count", default=0, help="Increase output verbosity"
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=10,
        help="Number of concurrent jobs to fetch pages",
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
        url=args.url,
        logging_level=logging_level,
        output_directory=Path(args.output),
        num_of_workers=args.jobs,
    )


def _configure_logger(logging_level: int, logger: logging.Logger):
    """Configure a logger to use the logging level and our desired output format."""
    logger.setLevel(logging_level)
    ch = logging.StreamHandler()
    ch.setLevel(logging_level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class Counter:
    """Simple statistics collection."""

    def __init__(self) -> None:
        super().__init__()
        self.storage_count = 0

    def stored(self):
        self.storage_count += 1


class Storage:
    def __init__(self, base_dir: Path, counter: Counter) -> None:
        super().__init__()
        self.base_dir: Path = base_dir
        self.counter = counter

    def store(self, path: str, mime_type: str, contents: bytes):
        storage_path = self._url_path_to_storage_path(mime_type, path)
        self._ensure_storage_within_base(storage_path)
        self._create_parent_dirs(storage_path)
        self._store_file(contents, path, storage_path)

    def _store_file(self, contents: bytes, path: str, storage_path: Path):
        self.counter.stored()
        logger.info("storing '%s' in '%s'", path, storage_path)
        storage_path.write_bytes(contents)

    def _url_path_to_storage_path(self, mime_type: str, path: str) -> Path:
        parts = path.split("/")
        storage_path = self.base_dir
        for p in parts:
            storage_path /= p
        if len(parts) == 0 or "." not in parts[-1]:
            storage_path /= f"index.{self._extension_name(mime_type)}"
        return storage_path.absolute()

    def _ensure_storage_within_base(self, storage_path: Path):
        assert str(storage_path).startswith(str(self.base_dir))

    def _create_parent_dirs(self, storage_path: Path):
        storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _extension_name(self, mimetype: str) -> str:
        if mimetype == parser.GEMINI_MIME_TYPE:
            return "gmi"
        else:
            return "unknown"


class ResponseProcessor:
    """
    Process responses to store page and/or extract URLs for further requests.
    """

    def __init__(
        self,
        storage: Storage,
        target: ParseResult,
        queue: asyncio.Queue,
        counter: Counter,
    ) -> None:
        super().__init__()
        self.storage = storage
        self.target = target
        self.queue = queue
        self.counter = counter

    def process(
        self,
        from_url: ParseResult,
        header: client.HeaderLine,
        response: Optional[bytes],
    ):
        if header.category == client.Category.SUCCESS:
            self._process_success(
                from_url, self._mime_type_from_header(header), cast(bytes, response)
            )
        elif header.category == client.Category.REDIRECT:
            self._process_redirect(from_url, header.meta)
        else:
            logger.debug(
                "skipping response code %d from '%s'",
                header.status_code,
                from_url.path,
            )

    def _process_success(self, from_url: ParseResult, mime_type: str, response: bytes):
        """Store the page and try to retrieve further URLs."""
        logger.info("'%s' serves a page with mime type '%s'", from_url.path, mime_type)
        self.storage.store(from_url.path, mime_type, response)
        if mime_type == parser.GEMINI_MIME_TYPE:
            logger.debug("extracting links from '%s'", from_url.path)
            self._urls_from_response(from_url, response)

    def _process_redirect(self, from_url: ParseResult, redirect_url: str):
        """Follow the redirect if valid."""
        absolute_url = self._make_absolute(urlparse(redirect_url), from_url)
        if self._validate_absolute_url(absolute_url):
            self.queue.put_nowait(absolute_url.geturl())

    def _mime_type_from_header(self, header: client.HeaderLine) -> str:
        return header.meta.strip().split(";", maxsplit=1)[0]

    def _validate_absolute_url(self, url: ParseResult) -> bool:
        return url.geturl().startswith(self.target.geturl())

    def _make_absolute(self, url: ParseResult, from_url: ParseResult) -> ParseResult:
        if url.hostname:
            return url

        scheme = str(url.scheme or from_url.scheme)
        hostname = str(url.hostname or from_url.hostname)
        if url.path.startswith("/"):
            path = url.path
        else:
            base_path = self._strip_filename(from_url.path)
            if not base_path.endswith("/"):
                base_path += "/"
            path = base_path + url.path

        return ParseResult(scheme, hostname, path, "", "", "")

    def _strip_filename(self, path: str) -> str:
        parts = path.split("/")
        if parts and "." in parts[-1]:
            parts = parts[:-1]
        return "/".join(parts)

    def _is_link(self, line: parser.LINE):
        return isinstance(line, parser.Link)

    def _urls_from_response(self, from_url: ParseResult, response: bytes):
        lines = parser.parse_gemini_text(response)
        links = cast(
            Iterator[parser.Link],
            filter(lambda line: isinstance(line, parser.Link), lines),
        )
        for link in links:
            absolute_url = self._make_absolute(urlparse(link.url.decode()), from_url)
            if self._validate_absolute_url(absolute_url):
                logger.debug("adding URL %s to processing queue", absolute_url.geturl())
                self.queue.put_nowait(absolute_url.geturl())
            else:
                logger.debug(
                    "URL %s is not a valid URL (relative or within target)",
                    absolute_url.geturl(),
                )


class Requester:
    """Wrapper around `async_request` to reuse the certificate store."""

    def __init__(self) -> None:
        super().__init__()
        self.cert_store = client.SelfSignedCertFileStore()

    async def request(self, url: str) -> Tuple[client.HeaderLine, Optional[bytes]]:
        return await client.async_request(url, self.cert_store)


async def _worker(
    requester: Requester,
    processor: ResponseProcessor,
    visited: Set[str],
    queue: asyncio.Queue,
):
    while True:
        url = await queue.get()
        if url not in visited:
            try:
                header, response = await requester.request(url)
                processor.process(urlparse(url), header, response)
            except Exception:  # Do not let the worker die.
                logger.debug("processing of '%s' failed", url, exc_info=True)
            finally:
                visited.add(url)

            # Nice crawlers sleep a little.
            await asyncio.sleep(random.choice([0.1, 0.2, 0.3, 0.4, 0.5]))
        else:
            logger.debug("skipping previously requested URL %s", url)
        queue.task_done()


def _prepare_base_output_dir(output_directory: Path, target: ParseResult) -> Path:
    output_directory = output_directory.absolute()
    output_directory /= str(target.hostname)
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def _create_workers(
    num_of_workers: int,
    counter: Counter,
    queue: asyncio.Queue,
    storage: Storage,
    target: ParseResult,
) -> List[asyncio.Task]:
    requester = Requester()
    processor = ResponseProcessor(storage, target, queue, counter)
    visited: Set[str] = set()
    workers = [
        asyncio.create_task(_worker(requester, processor, visited, queue))
        for _ in range(num_of_workers)
    ]
    return workers


async def _execute_command(command: Command):
    """
    Execute the parsed command.
    :param command: command options including URL to crawl and download.
    :return: exit code
    """

    # Configure logging.
    configure_logger = partial(_configure_logger, command.logging_level)
    configure_logger(logger)
    configure_logger(logging.getLogger(client.constants.LOGGER_NAME))

    target = urlparse(command.url)
    assert target.hostname

    counter = Counter()

    output_directory = _prepare_base_output_dir(command.output_directory, target)
    storage = Storage(output_directory, counter)

    # Create pool of workers.
    queue: asyncio.Queue = asyncio.Queue()
    workers = _create_workers(command.num_of_workers, counter, queue, storage, target)

    # Push the first URL onto the queue and wait for the workers to finish.
    queue.put_nowait(command.url)
    started_at = time.monotonic()
    await queue.join()
    time_worked = time.monotonic() - started_at
    print(
        "downloaded %d pages from %s in %.2f seconds (including friendly request pauses)"
        % (counter.storage_count, command.url, time_worked)
    )

    # Cleanup our worker tasks.
    for worker in workers:
        worker.cancel()


if __name__ == "__main__":
    cmd = _command_from_cli()
    asyncio.run(_execute_command(cmd))
