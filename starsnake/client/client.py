import enum
import logging
import ssl
import socket
from abc import ABC, abstractmethod
from contextlib import contextmanager
from os import path
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from . import exceptions


logger = logging.getLogger("starsnake")

GEMINI_DEFAULT_PORT = 1965

SSL_SELF_SIGNED_CERT_ERROR_CODE = 18


class Category(enum.Enum):
    UNKNOWN = 0

    INPUT = 1
    SUCCESS = 2
    REDIRECT = 3
    TEMPORARY_FAILURE = 4
    PERMANENT_FAILURE = 5
    CERTIFICATE_REQUIRED = 6


class Detail(enum.Enum):
    UNKNOWN = enum.auto()

    # Input details.
    INPUT = enum.auto()
    INPUT_SENSITIVE = enum.auto()

    # Success details.
    SUCCESS = enum.auto()

    # Redirect details.
    REDIRECT_TEMPORARY = enum.auto()
    REDIRECT_PERMANENT = enum.auto()

    # Temporary failure details.
    TEMPORARY_FAILURE = enum.auto()
    TEMPORARY_FAILURE_SERVER_UNAVAILABLE = enum.auto()
    TEMPORARY_FAILURE_CGI_ERROR = enum.auto()
    TEMPORARY_FAILURE_PROXY_ERROR = enum.auto()
    TEMPORARY_FAILURE_SLOW_DOWN = enum.auto()

    # Permanent failure details.
    PERMANENT_FAILURE = enum.auto()
    PERMANENT_FAILURE_NOT_FOUND = enum.auto()
    PERMANENT_FAILURE_GONE = enum.auto()
    PERMANENT_FAILURE_PROXY_REQUEST_REFUSED = enum.auto()
    PERMANENT_FAILURE_BAD_REQUEST = enum.auto()

    # Certificate required details.
    CERTIFICATE_REQUIRED = enum.auto()
    CERTIFICATE_REQUIRED_UNAUTHORISED = enum.auto()
    CERTIFICATE_REQUIRED_INVALID = enum.auto()


_CATEGORY_TO_DETAILS_MAP = {
    Category.INPUT: {0: Detail.INPUT, 1: Detail.INPUT_SENSITIVE},
    Category.SUCCESS: {0: Detail.SUCCESS},
    Category.REDIRECT: {0: Detail.REDIRECT_TEMPORARY, 1: Detail.REDIRECT_PERMANENT},
    Category.TEMPORARY_FAILURE: {
        0: Detail.TEMPORARY_FAILURE,
        1: Detail.TEMPORARY_FAILURE_SERVER_UNAVAILABLE,
        2: Detail.TEMPORARY_FAILURE_CGI_ERROR,
        3: Detail.TEMPORARY_FAILURE_CGI_ERROR,
        4: Detail.TEMPORARY_FAILURE_SLOW_DOWN,
    },
    Category.PERMANENT_FAILURE: {
        0: Detail.PERMANENT_FAILURE,
        1: Detail.PERMANENT_FAILURE_GONE,
        2: Detail.PERMANENT_FAILURE_GONE,
        3: Detail.PERMANENT_FAILURE_PROXY_REQUEST_REFUSED,
        9: Detail.PERMANENT_FAILURE_BAD_REQUEST,
    },
    Category.CERTIFICATE_REQUIRED: {
        0: Detail.CERTIFICATE_REQUIRED,
        1: Detail.CERTIFICATE_REQUIRED_UNAUTHORISED,
        2: Detail.CERTIFICATE_REQUIRED_INVALID,
    },
}


class HeaderLine:
    category: Category
    detail: Detail
    meta: str

    # Fields for compatibility with new status codes. Use these fields when the category or
    # detail are unknown.
    category_value: int
    detail_value: int

    def __init__(
        self,
        category: Category,
        category_value: int,
        detail: Detail,
        detail_value: int,
        meta: str,
    ) -> None:
        super().__init__()
        self.category = category
        self.category_value = category_value
        self.detail = detail
        self.detail_value = detail_value
        self.meta = meta


class SelfSignedCertStore(ABC):
    """Store for self-signed certificates."""

    @abstractmethod
    def load_cert(self, context: ssl.SSLContext, hostname: str) -> bool:
        """
        Load the certificate of the host into the context.
        :param context: the SSL context used to make requests, e.g. after wrapping a socket.
        :param hostname: a valid hostname.
        :return: True if a non-expired certificate was loaded into the context.
            False otherwise.
        """

    @abstractmethod
    def store_cert(self, hostname: str, pem_contents: str) -> None:
        """
        Store the certificate of the host.

        If the certificate exists, it is overwritten by this method.

        :param hostname: a valid hostname.
        :param pem_contents: the contents of the certificate, previously stored as a PEM file.
        :raises ExpiredCertError: raised when the certificate is expired.
        """


class SelfSignedCertFileStore(SelfSignedCertStore):
    """Store for self-signed certificates with file-based store."""

    base_dir: Path

    def __init__(self, base_dir: str = "~/.starsnake/certs/") -> None:
        super().__init__()
        self.base_dir = Path(path.expanduser(base_dir))
        logger.debug(
            "initialising file-based self-signed certificate store with base dir %s",
            self.base_dir,
        )
        # Essentially `mkdir -p <absolute_base_dir>`
        self.base_dir.mkdir(exist_ok=True, parents=True)

    def load_cert(self, context: ssl.SSLContext, hostname: str) -> bool:
        cert_path = self._cert_path(hostname)
        if not cert_path.exists():
            return False

        logger.debug(
            "loading self-signed certificate for %s from %s", hostname, str(cert_path)
        )
        context.load_verify_locations(cafile=str(cert_path))

    def store_cert(self, hostname: str, pem_contents: str) -> None:
        cert_path = self._cert_path(hostname)
        logger.debug(
            "storing self-signed certificate for %s at %s", hostname, str(cert_path)
        )
        cert_path.write_text(pem_contents)

    def _cert_path(self, hostname: str) -> Path:
        return self.base_dir / f"{hostname}.pem"


def tls_context(
    tls_1_2_forbidden: bool = False, self_signed_cert_forbidden: bool = False,
) -> ssl.SSLContext:
    """
    Create an SSL/TLS context that matches Gemini requirements:
        * TLS 1.2 or better.
        * Self-signed certificates are accepted.
    """
    context = ssl.create_default_context()

    return context


def _send(secure_socket: ssl.SSLSocket, data: bytes):
    sent = 0
    while sent < len(data):
        completed = secure_socket.send(data[sent:])
        sent += completed


def _parse_header(line: bytes) -> Tuple[HeaderLine, bytes]:
    """
    Parse the header line of the received input.

    :param line:
    :return: a tuple of the parsed header and the remaining input that is not
        part of the header.
    """
    end_index = line.find(b"\r\n")
    header, remaining = line[:end_index], line[end_index + 2 :]

    if len(line) < 2:
        raise exceptions.HeaderParseError("header is too short")

    # Determine the status category.
    try:
        category_value = int(chr(line[0]))
    except ValueError:
        raise exceptions.HeaderParseError(
            f"status category '{chr(line[0])}' is not an integer"
        )

    try:
        category = Category(category_value)
    except ValueError:
        category = Category.UNKNOWN

    # Determine the status detail.
    try:
        detail_value = int(chr(line[1]))
    except ValueError:
        raise exceptions.HeaderParseError(
            f"status detail '{chr(line[1])}' is not an integer"
        )

    detail = _CATEGORY_TO_DETAILS_MAP[category].get(detail_value, Detail.UNKNOWN)

    # Determine the meta line, which is the rest of the line.
    meta = line[3:].decode()

    # TODO: further parsing of the meta line.

    return HeaderLine(category, category_value, detail, detail_value, meta), remaining


def _receive_response(
    secure_socket: ssl.SSLSocket,
) -> Tuple[HeaderLine, Optional[List[bytes]]]:
    line = secure_socket.recv(1029)
    header, remaining = _parse_header(line)

    if header.category == Category.SUCCESS:
        # Get response body.
        body = remaining
        next_payload = secure_socket.recv(4096)
        while len(next_payload) > 0:
            body += next_payload
            next_payload = secure_socket.recv(4096)

        return header, body.split(b"\n")

    return header, []


@contextmanager
def _wrap_socket_with_self_signed_certs(
    host: str, port: int, cert_store: SelfSignedCertStore
):
    logger.debug("making request to %s:%d", host, port)
    secure_sock = None
    context = tls_context()
    cert_store.load_cert(context, host)
    try:
        sock = socket.create_connection((host, port))
        secure_sock = context.wrap_socket(sock, server_hostname=host)
        yield secure_sock
    except ssl.SSLCertVerificationError as e:
        logger.debug(
            "request to %s:%d failed due to self-signed certificate", host, port
        )
        if e.verify_code == SSL_SELF_SIGNED_CERT_ERROR_CODE:
            certificate = ssl.get_server_certificate((host, port))
            cert_store.store_cert(host, certificate)

            logger.debug(
                "retrying request to %s:%d with self-signed certificate", host, port
            )
            yield _wrap_socket_with_self_signed_certs(host, port, cert_store)
        else:
            raise e
    finally:
        if secure_sock:
            secure_sock.close()


def sync_request(
    url: str, cert_store: SelfSignedCertStore = None
) -> Tuple[HeaderLine, Optional[List[bytes]]]:
    """Make a synchronous Gemini request."""

    if cert_store is None:
        cert_store = SelfSignedCertFileStore()

    parsed_url = urlparse(url)

    if not parsed_url.hostname:
        raise exceptions.InvalidURLError(f"Invalid URL: {url}")
    if parsed_url.scheme != "" and not parsed_url.scheme.lower() == "gemini":
        raise exceptions.UnknownProtocolError(f"Unknown protocol: {parsed_url.scheme}")

    host = parsed_url.hostname
    port = parsed_url.port or GEMINI_DEFAULT_PORT

    with _wrap_socket_with_self_signed_certs(host, port, cert_store) as secure_sock:
        _send(secure_sock, url.encode() + b"\r\n")
        return _receive_response(secure_sock)
