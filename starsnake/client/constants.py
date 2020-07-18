import enum

LOGGER_NAME = "starsnake"

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
    """
    Detailed reason for the response.

    Use CATEGORY_TO_DETAILS_MAP to obtain the set of valid detail reasons for a category.
    If the detail reason is not in the set, use Detail.UNKNOWN and provide the received value
    to the caller. This provides forwards compatibility with new detail reasons.
    """

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


# Map of category -> detail.
CATEGORY_TO_DETAILS_MAP = {
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
