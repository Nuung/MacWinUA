from typing import Literal, List, Tuple, Dict

# Store the latest Chrome user agents for macOS and Windows
# (platform_label, os_version, chrome_version, ua_string)
DEFAULT_CHROME_AGENTS: List[Tuple[str, str, str, str]] = [
    # macOS
    (
        "mac",
        "Mac OS X 10_15_7",
        "138",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    ),
    (
        "mac",
        "Mac OS X 13_5_2",
        "137",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    ),
    (
        "mac",
        "Mac OS X 14_0",
        "137",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.2.0 Safari/537.36",
    ),
    (
        "mac",
        "Mac OS X 13_4_1",
        "136",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.2.0 Safari/537.36",
    ),
    # Windows
    (
        "win",
        "Windows NT 10.0; Win64; x64",
        "138",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    ),
    (
        "win",
        "Windows NT 10.0; Win64; x64",
        "137",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    ),
    (
        "win",
        "Windows NT 10.0; Win64; x64",
        "136",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.2.0 Safari/537.36",
    ),
]

# Chrome's sec-ch-ua header values
DEFAULT_CHROME_SEC_UA: Dict[str, str] = {
    "138": '"Google Chrome";v="138", "Chromium";v="138", "Not.A/Brand";v="99"',
    "137": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="99"',
    "136": '"Google Chrome";v="136", "Chromium";v="136", "Not.A/Brand";v="99"',
}

# Default headers included with every request
DEFAULT_HEADERS: Dict[str, str] = {
    "sec-ch-ua-mobile": "?0",
    "Upgrade-Insecure-Requests": "1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
    "Accept-Language": "en-US,en;q=0.9",
}

# Default fallback Chrome version if preferred version is not available
DEFAULT_CHROME_VERSION = "138"

# Valid platform types
PlatformType = Literal["mac", "win"]
