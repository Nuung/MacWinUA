"""
This module contains constants used throughout the MacWinUA library.
These values configure the library's behavior regarding data fetching,
caching, and fallback mechanisms.
"""

from typing import Dict, List, Literal

API_URL = "https://versionhistory.googleapis.com/v1/chrome/platforms/win/channels/stable/versions"
CACHE_VALIDITY_SECONDS = 7 * 24 * 60 * 60  # 7 days
FALLBACK_CHROME_VERSIONS: List[str] = ["139", "138", "137"]
DEFAULT_CHROME_VERSION: str = "139"

DEFAULT_HEADERS: Dict[str, str] = {
    "sec-ch-ua-mobile": "?0",
    "Upgrade-Insecure-Requests": "1",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        + "image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

PlatformType = Literal["mac", "win"]
