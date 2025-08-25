"""
MacWinUA: A library for generating realistic browser headers for macOS and Windows platforms
— always the freshest Chrome headers, updated automatically.
"""

from .exceptions import APIFetchError, CacheError, DataValidationError, UAError
from .ua import HeaderGenerator

# Backward compatibility alias
MacWinUA = HeaderGenerator

# Pre-initialized instance for convenient, direct use, as requested by users.
# This provides an easy-to-use, importable object for simple scripts and basic use cases.
ua = HeaderGenerator()


# Convenience functions that operate on the default `ua` instance.
# These are provided for users who prefer a functional approach.
def get_chrome_headers(*args, **kwargs):
    return ua.get_headers(*args, **kwargs)


def force_update(*args, **kwargs):
    return ua.force_update(*args, **kwargs)


__all__ = [
    "HeaderGenerator",
    "MacWinUA",
    "ua",  # Expose the convenient instance
    "get_chrome_headers",  # Expose the convenience function
    "force_update",  # Expose the convenience function
    "UAError",
    "APIFetchError",
    "CacheError",
    "DataValidationError",
]

__version__ = "0.5.250826"
