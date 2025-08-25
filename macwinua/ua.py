"""
This is the main user-facing module of MacWinUA.
It provides the `MacWinUA` class for generating headers and a singleton `ua` instance.
"""

import functools
import random
import threading
from pathlib import Path
from typing import Dict, Optional

from .constants import DEFAULT_CHROME_VERSION, DEFAULT_HEADERS, PlatformType
from .core import APIFetcher, CacheManager, DataProvider
from .exceptions import UAError


def memoize(func):
    """A simple, thread-safe memoization decorator."""
    cache = {}
    lock = threading.RLock()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(sorted(kwargs.items()))
        with lock:
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

    # Add a cache_clear method to the decorated function
    wrapper.cache_clear = lambda: cache.clear()
    return wrapper


class HeaderGenerator:
    """Generates Chrome user-agent strings and headers based on provided data."""

    def __init__(self, data_provider: DataProvider):
        """Initializes with a data provider (Dependency Injection)."""
        self._data_provider = data_provider
        self._reload_data()

    def _reload_data(self):
        """Loads or reloads the data from the data provider."""
        ua_data = self._data_provider.get_data()
        self._agents = ua_data.get("agents", [])
        self._sec_ua = ua_data.get("sec_ua", {})
        if not self._agents or not self._sec_ua:
            raise UAError("Cannot initialize HeaderGenerator with empty data.")

    @property
    def chrome(self) -> str:
        return random.choice(self._agents)[3]

    @property
    def mac(self) -> str:
        return random.choice([a for a in self._agents if a[0] == "mac"])[3]

    @property
    def windows(self) -> str:
        return random.choice([a for a in self._agents if a[0] == "win"])[3]

    @property
    def latest(self) -> str:
        latest_ver = max(self._sec_ua.keys(), key=int)
        return random.choice([a for a in self._agents if a[2] == latest_ver])[3]

    @property
    def random(self) -> str:
        return self.chrome

    @memoize
    def get_headers(
        self,
        platform: Optional[PlatformType] = None,
        chrome_version: Optional[str] = None,
    ) -> Dict[str, str]:
        """Generates a complete dictionary of Chrome browser headers."""
        candidates = self._agents
        if platform:
            if platform not in ("mac", "win"):
                raise UAError("Platform must be 'mac' or 'win'.")
            candidates = [a for a in candidates if a[0] == platform]
        if chrome_version:
            if chrome_version not in self._sec_ua:
                available = ", ".join(sorted(self._sec_ua.keys(), key=int, reverse=True))
                raise UAError(f"Chrome version must be one of: {available}.")
            candidates = [a for a in candidates if a[2] == chrome_version]
        if not candidates:
            raise UAError("No matching user-agent found for the specified criteria.")

        p_label, _, ver, ua_str = random.choice(candidates)
        headers = {
            "User-Agent": ua_str,
            "sec-ch-ua": self._sec_ua.get(ver, self._sec_ua[DEFAULT_CHROME_VERSION]),
            "sec-ch-ua-platform": f'"{"macOS" if p_label == "mac" else "Windows"}"',
        }
        headers.update(DEFAULT_HEADERS)
        return headers


# --- Singleton Instantiation & Public Functions ---

_cache_path = Path(__file__).parent / "macwinua_cache.json"
_data_provider_singleton = DataProvider(CacheManager(_cache_path), APIFetcher())
ua = HeaderGenerator(data_provider=_data_provider_singleton)


def get_chrome_headers(**kwargs) -> Dict[str, str]:
    """A convenience function to get Chrome headers."""
    return ua.get_headers(**kwargs)


# In macwinua/ua.py


def force_update():
    """
    Forces a refresh of the UA data from the remote API, bypassing the cache.
    The new data will be used for all subsequent calls.
    """
    # This call refreshes the data inside the singleton provider instance.
    new_data = _data_provider_singleton.force_refresh()

    # CRITICAL FIX: Directly update the internal state of the `ua` singleton
    # to reflect the newly fetched data. This ensures atomicity and testability.
    ua._agents = new_data.get("agents", [])
    ua._sec_ua = new_data.get("sec_ua", {})
    if not ua._agents or not ua._sec_ua:
        raise UAError("Failed to reload with valid data after force update.")

    # Clear the memoization cache on the header generation method.
    if hasattr(ua.get_headers, "cache_clear"):
        ua.get_headers.cache_clear()
