class UAError(Exception):
    """Default Exception"""

    pass


class UAUpdateError(UAError):
    """Exception raised when UA update fails."""

    pass


class UAValueError(UAError):
    """Exception raised when UA value is invalid."""

    pass


class UAInvalidError(UAError):
    """Exception raised when UA is invalid."""

    pass
