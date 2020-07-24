"""
Exceptions thrown by the Gemini client library.
"""


class ClientError(Exception):
    """Base Gemini client error."""


class InvalidURLError(ClientError):
    """Raised when an invalid URL is requested."""


class UnknownProtocolError(ClientError):
    """Raised when a URL is requested with an unsupported protocol."""


class ParseError(ClientError):
    """Base error for any parsing errors."""


class HeaderParseError(ClientError):
    """
    Raised when the header line could not be parsed.

    This error could indicate:
        * Our parsing library is buggy (likely!).
        * The server of the host is buggy.
        * There's been a network error somehow.
    """


class CertError(ClientError):
    """Base error for certificate issues."""


class ExpiredCertError(CertError):
    """
    Raised when a certificate has expired and client will refuse to use it.
    """
