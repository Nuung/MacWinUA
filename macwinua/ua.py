"""
Main user interface for MacWinUA library.
Provides HeaderGenerator class and a default instance for easy usage.
"""

import random
from typing import Dict, List, Optional

from .constants import DEFAULT_HEADERS, PlatformType, AgentTuple
from .core import DataManager
from .exceptions import UAError


class HeaderGenerator:
    """
    Generates Chrome browser headers with realistic User-Agent strings.
    Main user-facing class that provides simple API for header generation.
    """

    def __init__(self, data_manager: Optional[DataManager] = None):
        """Initialize with data manager (dependency injection for testing)."""
        self._data_manager = data_manager or DataManager()

    def _get_matching_agents(
        self,
        platform: Optional[PlatformType] = None,
        chrome_version: Optional[str] = None,
    ) -> List[AgentTuple]:
        """Get agents matching the specified criteria."""
        agents = self._data_manager.get_agents()

        # Filter by platform
        if platform is not None:
            if platform not in ("mac", "win"):
                raise UAError("Platform must be 'mac' or 'win'")
            agents = [agent for agent in agents if agent[0] == platform]

        # Filter by Chrome version
        if chrome_version is not None:
            sec_ua_map = self._data_manager.get_sec_ua_map()
            if chrome_version not in sec_ua_map:
                available = ", ".join(sorted(sec_ua_map.keys(), key=int, reverse=True))
                raise UAError(f"Chrome version must be one of: {available}")
            agents = [agent for agent in agents if agent[2] == chrome_version]

        if not agents:
            raise UAError("No matching user-agent found for specified criteria")

        return agents

    @property
    def chrome(self) -> str:
        """Get a random Chrome User-Agent string."""
        agents = self._data_manager.get_agents()
        if not agents:
            raise UAError("No user agents available")
        return random.choice(agents)[3]

    @property
    def mac(self) -> str:
        """Get a random macOS Chrome User-Agent string."""
        agents = self._get_matching_agents(platform="mac")
        return random.choice(agents)[3]

    @property
    def windows(self) -> str:
        """Get a random Windows Chrome User-Agent string."""
        agents = self._get_matching_agents(platform="win")
        return random.choice(agents)[3]

    @property
    def latest(self) -> str:
        """Get User-Agent from the latest Chrome version available."""
        sec_ua_map = self._data_manager.get_sec_ua_map()
        if not sec_ua_map:
            return self.chrome

        latest_version = max(sec_ua_map.keys(), key=int)
        agents = self._get_matching_agents(chrome_version=latest_version)
        return random.choice(agents)[3]

    @property
    def random(self) -> str:
        """Alias for chrome property - get a random Chrome UA string."""
        return self.chrome

    def get_headers(
        self,
        platform: Optional[PlatformType] = None,
        chrome_version: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Generate complete HTTP headers for Chrome browser.

        Args:
            platform: Target platform ('mac' or 'win')
            chrome_version: Specific Chrome version to use
            extra_headers: Additional headers to include

        Returns:
            Complete dictionary of HTTP headers

        Raises:
            UAError: If parameters are invalid or no matching agents found
        """
        matching_agents = self._get_matching_agents(platform, chrome_version)
        platform_key, _, version, ua_string = random.choice(matching_agents)

        sec_ua_map = self._data_manager.get_sec_ua_map()
        sec_ua_value = sec_ua_map.get(version, "")

        platform_name = "macOS" if platform_key == "mac" else "Windows"

        headers = {
            "User-Agent": ua_string,
            "sec-ch-ua": sec_ua_value,
            "sec-ch-ua-platform": f'"{platform_name}"',
        }

        headers.update(DEFAULT_HEADERS)
        if extra_headers:
            headers.update(extra_headers)

        return headers

    def force_update(self) -> None:
        """Force refresh Chrome version data from API, bypassing cache."""
        self._data_manager.force_update()


# Default instance for convenient, backward-compatible access
ua = HeaderGenerator()


def get_chrome_headers(**kwargs) -> Dict[str, str]:
    """
    Convenience function to get Chrome headers using default instance.
    """
    return ua.get_headers(**kwargs)


def force_update() -> None:
    """
    Force refresh Chrome version data from API for the default instance.
    """
    ua.force_update()
