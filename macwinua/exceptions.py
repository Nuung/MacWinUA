"""
Custom exceptions for MacWinUA library.
Provides specific exception types for different error scenarios.
"""


class UAError(Exception):
    """Base exception for all MacWinUA-related errors."""

    pass


class CacheError(UAError):
    """Raised when cache operations fail (read/write/corruption)."""

    pass


class APIFetchError(UAError):
    """Raised when API requests fail (network, timeout, invalid response)."""

    pass


class DataValidationError(UAError):
    """Raised when data validation fails (empty data, invalid format)."""

    pass
