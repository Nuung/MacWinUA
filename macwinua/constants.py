"""
Constants and configuration for MacWinUA library.
Contains all configuration values, API endpoints, and type definitions.
"""

from typing import Dict, List, Literal, Tuple

# API Configuration
API_URL_TEMPLATE = "https://versionhistory.googleapis.com/v1/chrome/platforms/{platform}/channels/stable/versions"
CACHE_VALIDITY_DAYS = 7
API_TIMEOUT_SECONDS = 10

# FALLBACK_VERSIONS are used if the API call fails.
FALLBACK_VERSIONS: List[str] = ["139", "138", "137"]
DEFAULT_VERSION = "139"

# Platform definitions
PLATFORMS = {
    "mac": [
        ("Mac OS X 10_15_7", "Macintosh; Intel Mac OS X 10_15_7"),
        ("Mac OS X 14_0", "Macintosh; Intel Mac OS X 14_0"),
    ],
    "win": [
        ("Windows NT 10.0; Win64; x64", "Windows NT 10.0; Win64; x64"),
    ],
}

# Default HTTP headers that are always included
DEFAULT_HEADERS: Dict[str, str] = {
    "sec-ch-ua-mobile": "?0",
    "Upgrade-Insecure-Requests": "1",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Type definitions for better type safety
PlatformType = Literal["mac", "win"]
# (platform, os_version, chrome_version, ua_string)
AgentTuple = Tuple[str, str, str, str]
SecUAMapping = Dict[str, str]
