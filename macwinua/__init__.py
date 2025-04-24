"""
MacWinUA: A library for generating realistic browser headers for macOS and Windows platforms
— always the freshest Chrome headers.
"""

from macwinua.ua import ChromeUA, get_chrome_headers, ua

__all__ = ["ua", "ChromeUA", "get_chrome_headers"]
__version__ = "0.1.0"
