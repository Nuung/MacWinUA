"""
MacWinUA: A library for generating realistic browser headers for macOS and Windows platforms
— always the freshest Chrome headers.
"""

import functools
import random
import threading
from typing import Dict, List, Literal, Optional, Tuple, Union

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

# Default headers included with every request
DEFAULT_HEADERS: Dict[str, str] = {
    "sec-ch-ua-mobile": "?0",
    "Upgrade-Insecure-Requests": "1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
    "Accept-Language": "en-US,en;q=0.9",
}

# Default fallback Chrome version if preferred version is not available
DEFAULT_CHROME_VERSION = "135"

# Valid platform types
PlatformType = Literal["mac", "win"]


def memoize(func):
    """
    Thread-safe memoization decorator to cache results.

    Implements a simple cache using a dict protected by a lock for thread safety.
    """
    cache = {}
    lock = threading.RLock()  # Reentrant lock for thread safety

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create a safe cache key
        try:
            sorted_kwargs = sorted(kwargs.items())
            key = str(args) + str(sorted_kwargs)
        except Exception:
            return func(*args, **kwargs)

        with lock:
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

    def clear_cache():
        with lock:
            cache.clear()

    wrapper.clear_cache = clear_cache
    return wrapper


class ChromeUA:
    """
    Generate the latest Chrome user-agent strings and headers for macOS and Windows.
    Simplified API inspired by fake-useragent.
    """

    def __init__(self):
        """Initialize with default agents."""
        self._agents = CHROME_AGENTS.copy()
        self._sec_ua = CHROME_SEC_UA.copy()
        self._lock = threading.RLock()  # For thread-safe operations

        # Validate initial data
        self._validate_agents()
        self._validate_sec_ua()
        self._validate_cross_consistency()

    def _validate_agents(self):
        """Validate the structure of agent tuples."""
        if not isinstance(self._agents, list):
            raise TypeError("Agents must be a list")

        for idx, agent in enumerate(self._agents):
            if not isinstance(agent, tuple) or len(agent) != 4:
                raise ValueError(f"Agent at index {idx} must be a 4-element tuple")

            platform, os_ver, chrome_ver, ua_str = agent

            if not all(isinstance(x, str) for x in (platform, os_ver, chrome_ver, ua_str)):
                raise TypeError(f"All elements in agent tuple at index {idx} must be strings")

            if platform not in ["mac", "win"]:
                raise ValueError(f"Platform at index {idx} must be 'mac' or 'win', got '{platform}'")

    def _validate_sec_ua(self):
        """Validate sec-ch-ua dictionary."""
        if not isinstance(self._sec_ua, dict):
            raise TypeError("sec_ua must be a dictionary")

        if not self._sec_ua:
            raise ValueError("sec_ua dictionary cannot be empty")

        # Ensure that at least the default version exists
        if DEFAULT_CHROME_VERSION not in self._sec_ua:
            raise KeyError(f"Default Chrome version '{DEFAULT_CHROME_VERSION}' must exist in sec_ua dictionary")

    def _validate_cross_consistency(self):
        """Validate consistency between agents and sec_ua dictionaries."""
        versions_in_agents = {a[2] for a in self._agents}
        versions_in_sec_ua = set(self._sec_ua.keys())
        missing = versions_in_agents - versions_in_sec_ua
        if missing:
            raise ValueError(f"sec_ua is missing entries for Chrome versions: {', '.join(sorted(missing))}")

    def _get_random_agent(self, agents):
        """
        Get a random agent from the list, raising IndexError if empty.

        Args:
            agents: List of agent tuples

        Returns:
            Random agent tuple from the list

        Raises:
            IndexError: If the agents list is empty
        """
        if not agents:
            raise IndexError("No agents available")

        try:
            return random.choice(agents)
        except (TypeError, IndexError) as e:
            raise IndexError(f"Failed to select random agent: {str(e)}") from e

    @property
    def chrome(self) -> str:
        """Get a random Chrome user-agent string."""
        with self._lock:
            _, _, _, ua = self._get_random_agent(self._agents)
            return ua

    @property
    def mac(self) -> str:
        """Get a random macOS Chrome user-agent string."""
        with self._lock:
            mac_agents = [a for a in self._agents if a[0] == "mac"]
            _, _, _, ua = self._get_random_agent(mac_agents)
            return ua

    @property
    def windows(self) -> str:
        """Get a random Windows Chrome user-agent string."""
        with self._lock:
            win_agents = [a for a in self._agents if a[0] == "win"]
            _, _, _, ua = self._get_random_agent(win_agents)
            return ua

    @property
    def latest(self) -> str:
        """Get the latest Chrome version user-agent."""
        with self._lock:
            if not self._agents:
                raise IndexError("No agents available")

            try:
                latest_ver = max(a[2] for a in self._agents)
                latest_agents = [a for a in self._agents if a[2] == latest_ver]
                _, _, _, ua = self._get_random_agent(latest_agents)
                return ua
            except ValueError as e:
                raise ValueError("Cannot determine latest version from empty agents list") from e

    @property
    def random(self) -> str:
        """Alias for chrome property - get any random Chrome UA."""
        return self.chrome

    @property
    def available_versions(self) -> List[str]:
        """Get all available Chrome versions."""
        with self._lock:
            return sorted(set(agent[2] for agent in self._agents))

    @property
    def available_platforms(self) -> List[str]:
        """Get all available platforms."""
        with self._lock:
            return sorted(set(agent[0] for agent in self._agents))

    @property
    def available_os_versions(self) -> Dict[str, List[str]]:
        """Get all available OS versions grouped by platform."""
        with self._lock:
            result: Dict[str, List[str]] = {}
            for platform, os_ver, _, _ in self._agents:
                if platform not in result:
                    result[platform] = []
                if os_ver not in result[platform]:
                    result[platform].append(os_ver)
            return result

    @memoize
    def get_headers(
        self,
        platform: Optional[Union[PlatformType, str]] = None,
        chrome_version: Optional[str] = None,
        os_version: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Get complete Chrome browser headers.

        Args:
            platform: The platform to get headers for ('mac' or 'win', None for random)
            chrome_version: The Chrome version ('135', '136', '137', None for random)
            os_version: Specific OS version to use (e.g., 'Mac OS X 14_0', 'Windows NT 10.0; Win64; x64')
            extra_headers: Additional headers to include in the response

        Returns:
            Dictionary of HTTP headers

        Raises:
            ValueError: If no matching user-agent found with the given criteria
        """
        with self._lock:
            # Make a copy to avoid modifying the original
            candidates = list(self._agents)

            if not candidates:
                raise ValueError("No matching user-agent found.")

            if platform:
                try:
                    platform = str(platform).lower()
                    if platform not in ["mac", "win"]:
                        raise ValueError("Platform must be 'mac' or 'win'")
                    candidates = [a for a in candidates if a[0] == platform]
                except (AttributeError, TypeError) as e:
                    raise ValueError(f"Invalid platform type: {str(e)}") from e

            if chrome_version:
                try:
                    chrome_version = str(chrome_version)
                    if chrome_version not in self._sec_ua:
                        available_versions = ", ".join(sorted(self._sec_ua.keys()))
                        raise ValueError(f"Chrome version must be one of: {available_versions}")
                    candidates = [a for a in candidates if a[2] == chrome_version]
                except (AttributeError, TypeError) as e:
                    raise ValueError(f"Invalid chrome_version type: {str(e)}") from e

            if os_version:
                try:
                    os_version = str(os_version)
                    candidates = [a for a in candidates if a[1] == os_version]
                except (AttributeError, TypeError) as e:
                    raise ValueError(f"Invalid os_version type: {str(e)}") from e

            if not candidates:
                filter_desc = []
                if platform:
                    filter_desc.append(f"platform '{platform}'")
                if chrome_version:
                    filter_desc.append(f"Chrome version '{chrome_version}'")
                if os_version:
                    filter_desc.append(f"OS version '{os_version}'")

                if filter_desc:
                    raise ValueError(f"No matching user-agent found for {' and '.join(filter_desc)}.")
                else:
                    raise ValueError("No matching user-agent found.")

            try:
                platform_label, _, ver, ua = random.choice(candidates)

                # Use get() with default to prevent KeyError
                default_sec_ua = self._sec_ua.get(DEFAULT_CHROME_VERSION, next(iter(self._sec_ua.values())))
                sec_ch_ua = self._sec_ua.get(ver, default_sec_ua)

                platform_name = "macOS" if platform_label == "mac" else "Windows"

                headers = {
                    "User-Agent": ua,
                    "sec-ch-ua": sec_ch_ua,
                    "sec-ch-ua-platform": f'"{platform_name}"',
                }

                # Add default headers
                headers.update(DEFAULT_HEADERS)

                # Add any extra headers if provided
                if extra_headers:
                    headers.update(extra_headers)

                return headers
            except Exception as e:
                raise ValueError(f"Failed to generate headers: {str(e)}") from e

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

        Raises:
            TypeError: If agents or sec_ua are not of the correct type
            ValueError: If agents or sec_ua contain invalid structures
        """
        with self._lock:
            # Store original values to revert if validation fails
            original_agents = self._agents.copy()
            original_sec_ua = self._sec_ua.copy()

            try:
                if agents is not None:
                    if not isinstance(agents, list):
                        raise TypeError("agents must be a list or None")
                    # Make a copy to avoid external modification
                    self._agents = agents.copy()
                    self._validate_agents()

                if sec_ua is not None:
                    if not isinstance(sec_ua, dict):
                        raise TypeError("sec_ua must be a dictionary or None")
                    # Make a copy to avoid external modification
                    self._sec_ua = sec_ua.copy()
                    self._validate_sec_ua()

                # Validate cross-consistency after both updates
                if agents is not None or sec_ua is not None:
                    self._validate_cross_consistency()

                # Clear cache when data is updated
                if hasattr(self.get_headers, "clear_cache"):
                    self.get_headers.clear_cache()

            except Exception as e:
                # Revert to original values if any validation fails
                self._agents = original_agents
                self._sec_ua = original_sec_ua
                raise e


# Create a singleton instance for easy import
ua = ChromeUA()


def get_chrome_headers(
    platform: Optional[Union[PlatformType, str]] = None,
    chrome_version: Optional[str] = None,
    os_version: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Generate Chrome browser headers for web requests.

    Args:
        platform: The operating system platform ('mac' or 'win')
        chrome_version: The Chrome version ('135', '136', or '137')
        os_version: Specific OS version to use (e.g., 'Mac OS X 14_0')
        extra_headers: Additional headers to include in the response

    Returns:
        Dictionary of HTTP headers

    Raises:
        ValueError: If no matching user-agent found with the given criteria
    """
    return ua.get_headers(platform, chrome_version, os_version, extra_headers)
