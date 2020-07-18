import logging
import ssl
from abc import ABC, abstractmethod
from os import path
from pathlib import Path

from . import constants

logger = logging.getLogger(constants.LOGGER_NAME)


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
        return True

    def store_cert(self, hostname: str, pem_contents: str) -> None:
        cert_path = self._cert_path(hostname)
        logger.debug(
            "storing self-signed certificate for %s at %s", hostname, str(cert_path)
        )
        cert_path.write_text(pem_contents)

    def _cert_path(self, hostname: str) -> Path:
        return self.base_dir / f"{hostname}.pem"
