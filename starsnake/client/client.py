import logging
import ssl
import socket
from contextlib import contextmanager
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from . import constants
from . import exceptions
from . import tofu


logger = logging.getLogger("starsnake")


class HeaderLine:
    category: constants.Category
    detail: constants.Detail
    meta: str

    # Fields for compatibility with new status codes. Use these fields when the category or
    # detail are unknown.
    category_value: int
    detail_value: int

    def __init__(
        self,
        category: constants.Category,
        category_value: int,
        detail: constants.Detail,
        detail_value: int,
        meta: str,
    ) -> None:
        super().__init__()
        self.category = category
        self.category_value = category_value
        self.detail = detail
        self.detail_value = detail_value
        self.meta = meta


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
        category = constants.Category(category_value)
    except ValueError:
        category = constants.Category.UNKNOWN

    # Determine the status detail.
    try:
        detail_value = int(chr(line[1]))
    except ValueError:
        raise exceptions.HeaderParseError(
            f"status detail '{chr(line[1])}' is not an integer"
        )

    detail = constants.CATEGORY_TO_DETAILS_MAP[category].get(
        detail_value, constants.Detail.UNKNOWN
    )

    # Determine the meta line, which is the rest of the line.
    meta = line[3:].decode()

    # TODO: further parsing of the meta line.

    return HeaderLine(category, category_value, detail, detail_value, meta), remaining


def _receive_response(
    secure_socket: ssl.SSLSocket,
) -> Tuple[HeaderLine, Optional[List[bytes]]]:
    line = secure_socket.recv(1029)
    header, remaining = _parse_header(line)

    if header.category == constants.Category.SUCCESS:
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
    host: str, port: int, cert_store: tofu.SelfSignedCertStore
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
        if e.verify_code == constants.SSL_SELF_SIGNED_CERT_ERROR_CODE:
            certificate = ssl.get_server_certificate((host, port))
            cert_store.store_cert(host, certificate)

            logger.debug(
                "retrying request to %s:%d with self-signed certificate", host, port
            )
            with _wrap_socket_with_self_signed_certs(host, port, cert_store) as secure_sock:
                yield secure_sock
        else:
            raise e
    finally:
        if secure_sock:
            secure_sock.close()


def sync_request(
    url: str, cert_store: tofu.SelfSignedCertStore = None
) -> Tuple[HeaderLine, Optional[List[bytes]]]:
    """Make a synchronous Gemini request."""

    if cert_store is None:
        cert_store = tofu.SelfSignedCertFileStore()

    parsed_url = urlparse(url)

    if not parsed_url.hostname:
        raise exceptions.InvalidURLError(f"Invalid URL: {url}")
    if parsed_url.scheme != "" and not parsed_url.scheme.lower() == "gemini":
        raise exceptions.UnknownProtocolError(f"Unknown protocol: {parsed_url.scheme}")

    host = parsed_url.hostname
    port = parsed_url.port or constants.GEMINI_DEFAULT_PORT

    with _wrap_socket_with_self_signed_certs(host, port, cert_store) as secure_sock:
        _send(secure_sock, url.encode() + b"\r\n")
        return _receive_response(secure_sock)
