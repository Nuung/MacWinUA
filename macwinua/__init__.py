"""
MacWinUA: A library for generating realistic browser headers for macOS and Windows platforms
— always the freshest Chrome headers, updated automatically.
"""

from .ua import HeaderGenerator, get_chrome_headers, ua, force_update
from .exceptions import UAError, APIFetchError, CacheError, DataValidationError

# Backward compatibility alias
MacWinUA = HeaderGenerator

__all__ = [
    "ua",
    "HeaderGenerator",
    "MacWinUA",
    "get_chrome_headers",
    "force_update",
    "UAError",
    "APIFetchError",
    "CacheError",
    "DataValidationError",
]
__version__ = "0.6.0"
