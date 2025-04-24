"""
MacWinUA: A library for generating realistic browser headers for macOS and Windows platforms
— always the freshest Chrome headers.
"""

import functools
import random
from typing import Dict, List, Optional, Tuple

# Store the latest Chrome user agents for macOS and Windows
# (platform_label, os_version, chrome_version, ua_string)
CHROME_AGENTS: List[Tuple[str, str, str, str]] = [
    # macOS
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
    (
        "mac",
        "Mac OS X 12_6_3",
        "135",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.1.0 Safari/537.36",
    ),
    # Windows
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
    (
        "win",
        "Windows NT 10.0; Win64; x64",
        "135",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    ),
]

# Chrome's sec-ch-ua header values
CHROME_SEC_UA: Dict[str, str] = {
    "137": '"Google Chrome";v="137", "Chromium";v="137", "Not.A/Brand";v="99"',
    "136": '"Google Chrome";v="136", "Chromium";v="136", "Not.A/Brand";v="99"',
    "135": '"Google Chrome";v="135", "Chromium";v="135", "Not.A/Brand";v="99"',
}


def memoize(func):
    """Simple memoization decorator to cache results."""
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(sorted(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    # Add cache clear functionality
    wrapper.clear_cache = cache.clear
    return wrapper


class ChromeUA:
    """
    Generate the latest Chrome user-agent strings and headers for macOS and Windows.
    Simplified API inspired by fake-useragent.
    """

    def __init__(self):
        """Initialize with default agents."""
        self._agents = CHROME_AGENTS
        self._sec_ua = CHROME_SEC_UA
        self._cache = {}

    @property
    def chrome(self) -> str:
        """Get a random Chrome user-agent string."""
        _, _, _, ua = random.choice(self._agents)
        return ua

    @property
    def mac(self) -> str:
        """Get a random macOS Chrome user-agent string."""
        mac_agents = [a for a in self._agents if a[0] == "mac"]
        _, _, _, ua = random.choice(mac_agents)
        return ua

    @property
    def windows(self) -> str:
        """Get a random Windows Chrome user-agent string."""
        win_agents = [a for a in self._agents if a[0] == "win"]
        _, _, _, ua = random.choice(win_agents)
        return ua

    @property
    def latest(self) -> str:
        """Get the latest Chrome version user-agent."""
        latest_ver = max(a[2] for a in self._agents)
        latest_agents = [a for a in self._agents if a[2] == latest_ver]
        _, _, _, ua = random.choice(latest_agents)
        return ua

    @property
    def random(self) -> str:
        """Alias for chrome property - get any random Chrome UA."""
        return self.chrome

    @memoize
    def get_headers(self, platform: Optional[str] = None, chrome_version: Optional[str] = None) -> Dict[str, str]:
        """
        Get complete Chrome browser headers.

        Args:
            platform: The platform to get headers for ('mac' or 'win', None for random)
            chrome_version: The Chrome version ('135', '136', '137', None for random)

        Returns:
            Dictionary of HTTP headers

        Raises:
            ValueError: If no matching user-agent found with the given criteria
        """
        candidates = self._agents

        if platform:
            platform = platform.lower()
            if platform not in ["mac", "win"]:
                raise ValueError("Platform must be 'mac' or 'win'")
            candidates = [a for a in candidates if a[0] == platform]

        if chrome_version:
            if chrome_version not in self._sec_ua:
                raise ValueError(f"Chrome version must be one of: {', '.join(self._sec_ua.keys())}")
            candidates = [a for a in candidates if a[2] == chrome_version]

        if not candidates:
            raise ValueError("No matching user-agent found.")

        platform_label, _, ver, ua = random.choice(candidates)
        sec_ch_ua = self._sec_ua.get(ver, self._sec_ua["135"])  # Fallback to 135
        platform_name = "macOS" if platform_label == "mac" else "Windows"

        return {
            "User-Agent": ua,
            "sec-ch-ua": sec_ch_ua,
            "sec-ch-ua-platform": f'"{platform_name}"',
            "sec-ch-ua-mobile": "?0",
        }

    def update(
        self,
        agents: Optional[List[Tuple[str, str, str, str]]] = None,
        sec_ua: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Update the user-agents and sec-ua values (for future automatic updates).

        Args:
            agents: New list of agents to replace the current ones
            sec_ua: New sec-ch-ua values to replace the current ones
        """
        if agents:
            self._agents = agents
        if sec_ua:
            self._sec_ua = sec_ua

        # Clear cache when data is updated
        if hasattr(self.get_headers, "clear_cache"):
            self.get_headers.clear_cache()


# Create a singleton instance for easy import
ua = ChromeUA()


# For backward compatibility and simple usage
def get_chrome_headers(platform: Optional[str] = None, chrome_version: Optional[str] = None) -> Dict[str, str]:
    """
    Generate Chrome browser headers for web requests.

    Args:
        platform: The operating system platform ('mac' or 'win')
        chrome_version: The Chrome version ('135', '136', or '137')

    Returns:
        Dictionary of HTTP headers
    """
    return ua.get_headers(platform, chrome_version)
