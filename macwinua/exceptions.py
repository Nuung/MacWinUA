"""
This module defines custom exceptions for the MacWinUA library, allowing for
granular error handling by the end-user.
"""


class UAError(Exception):
    """Base exception for all library-specific errors."""

    pass


class APIFetchError(UAError):
    """Raised when there is an error fetching data from the remote API."""

    pass


class CacheError(UAError):
    """Raised when there is an error reading from or writing to the cache file."""

    pass
