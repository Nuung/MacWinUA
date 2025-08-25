"""
MacWinUA: A library for generating realistic browser headers for macOS and Windows platforms
— always the freshest Chrome headers, updated automatically.
"""

from .exceptions import APIFetchError, CacheError, DataValidationError, UAError
from .ua import HeaderGenerator

# Backward compatibility alias
MacWinUA = HeaderGenerator

__all__ = [
    "HeaderGenerator",
    "MacWinUA",
    "UAError",
    "APIFetchError",
    "CacheError",
    "DataValidationError",
]
__version__ = "0.5.250825"
