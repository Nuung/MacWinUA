"""
Core data processing components for MacWinUA library.
Handles caching, API fetching, and data management following SRP.
"""

import json
import os
import time
import threading
from pathlib import Path
from typing import List, Optional, Protocol
from urllib import request, error

from .constants import (
    API_URL_TEMPLATE,
    CACHE_VALIDITY_DAYS,
    API_TIMEOUT_SECONDS,
    FALLBACK_VERSIONS,
    PLATFORMS,
    AgentTuple,
    SecUAMapping,
)
from .exceptions import CacheError, APIFetchError, DataValidationError


def get_default_cache_path() -> Path:
    """
    Gets the default, user-specific cache path using only the standard library.
    Creates a hidden directory in the user's home folder.
    """
    home_dir = os.path.expanduser("~")
    return Path(home_dir) / ".macwinua" / "macwinua_cache.json"


class CacheManager:
    """
    Manages file-based caching of Chrome version data.
    Responsibility: Cache operations (read, write, validation)
    """

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self._lock = threading.Lock()

    def is_valid(self) -> bool:
        """Check if cache file exists and is within validity period."""
        if not self.cache_path.exists():
            return False
        try:
            with self.cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            timestamp = data.get("timestamp", 0)
            age_days = (time.time() - timestamp) / (24 * 60 * 60)
            return age_days < CACHE_VALIDITY_DAYS
        except (json.JSONDecodeError, IOError, KeyError):
            return False

    def load(self) -> Optional[List[str]]:
        """Load Chrome versions from cache if valid."""
        if not self.is_valid():
            return None
        try:
            with self.cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            versions = data.get("versions", [])
            if not versions or not isinstance(versions, list):
                return None
            return versions
        except (json.JSONDecodeError, IOError, OSError) as e:
            raise CacheError(f"Failed to load cache: {e}") from e

    def save(self, versions: List[str]) -> None:
        """Save Chrome versions to cache with timestamp."""
        if not versions:
            raise DataValidationError("Cannot save empty versions list to cache")
        with self._lock:
            try:
                # Ensure parent directory exists
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_data = {"versions": versions, "timestamp": time.time()}
                with self.cache_path.open("w", encoding="utf-8") as f:
                    json.dump(cache_data, f, indent=2)
            except (IOError, OSError) as e:
                raise CacheError(f"Failed to save cache: {e}") from e


class VersionSource(Protocol):
    """Protocol for classes that can fetch Chrome versions."""

    def fetch(self) -> List[str]:
        ...


class ApiVersionFetcher:
    """
    Fetches latest Chrome versions from Google API.
    Responsibility: API communication and response parsing
    """

    def fetch(self) -> List[str]:
        """Fetch latest Chrome versions from Google API."""
        api_url = API_URL_TEMPLATE.format(platform="win")
        try:
            req = request.Request(api_url)
            req.add_header("User-Agent", "MacWinUA/2.0")

            with request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise APIFetchError(f"API returned status {response.status}")

                data = json.loads(response.read().decode("utf-8"))

                versions = set()
                for item in data.get("versions", []):
                    version_major = item.get("version", "").split(".")[0]
                    if version_major.isdigit():
                        versions.add(version_major)

                if not versions:
                    raise APIFetchError("No valid versions found in API response")

                return sorted(list(versions), key=int, reverse=True)

        except (error.URLError, error.HTTPError, TimeoutError) as e:
            raise APIFetchError(f"Network error: {e}") from e
        except json.JSONDecodeError as e:
            raise APIFetchError(f"Invalid JSON response: {e}") from e


class DataProvider:
    """
    Orchestrates data acquisition from cache and API.
    Responsibility: Data coordination and fallback logic
    """

    def __init__(self, cache_manager: CacheManager, version_fetcher: VersionSource):
        self.cache_manager = cache_manager
        self.version_fetcher = version_fetcher

    def get_versions(self, force_refresh: bool = False) -> List[str]:
        """Get Chrome versions with cache-first strategy."""
        if not force_refresh:
            try:
                cached_versions = self.cache_manager.load()
                if cached_versions:
                    return cached_versions
            except CacheError:
                pass  # Proceed to fetch from API

        try:
            api_versions = self.version_fetcher.fetch()
            try:
                self.cache_manager.save(api_versions)
            except CacheError:
                pass  # Non-critical error, proceed with API data
            return api_versions
        except APIFetchError:
            return FALLBACK_VERSIONS.copy()


class UADataBuilder:
    """
    Builds User-Agent data structures from Chrome versions.
    Responsibility: Data transformation and UA string generation
    """

    @staticmethod
    def build_agents(versions: List[str]) -> List[AgentTuple]:
        """Build list of agent tuples from Chrome versions."""
        if not versions:
            raise DataValidationError("Cannot build agents from empty versions list")
        agents = []
        for version in versions:
            for platform, platform_configs in PLATFORMS.items():
                for os_version, user_agent_os in platform_configs:
                    ua_string = (
                        f"Mozilla/5.0 ({user_agent_os}) "
                        f"AppleWebKit/537.36 (KHTML, like Gecko) "
                        f"Chrome/{version}.0.0.0 Safari/537.36"
                    )
                    agents.append((platform, os_version, version, ua_string))
        return agents

    @staticmethod
    def build_sec_ua_map(versions: List[str]) -> SecUAMapping:
        """Build sec-ch-ua header mapping from Chrome versions."""
        if not versions:
            raise DataValidationError("Cannot build sec-ua map from empty versions list")
        sec_ua_map = {}
        for version in versions:
            sec_ua_map[version] = f'"Google Chrome";v="{version}", "Not/A)Brand";v="99", "Chromium";v="{version}"'
        return sec_ua_map


class DataManager:
    """
    High-level data management. No longer a singleton.
    Responsibility: Coordinating all data operations and providing unified interface
    """

    _lock = threading.Lock()

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        version_fetcher: Optional[VersionSource] = None,
    ):
        self._cache_path = cache_path or get_default_cache_path()
        self._version_fetcher = version_fetcher or ApiVersionFetcher()

        self.cache_manager = CacheManager(self._cache_path)
        self.data_provider = DataProvider(self.cache_manager, self._version_fetcher)
        self.ua_builder = UADataBuilder()

        self._agents: List[AgentTuple] = []
        self._sec_ua_map: SecUAMapping = {}

        # Initial data load on instantiation
        self._load_data(force_refresh=False)

    def _load_data(self, force_refresh: bool):
        """Internal method to load or reload all data from the provider."""
        with self._lock:
            versions = self.data_provider.get_versions(force_refresh=force_refresh)
            self._agents = self.ua_builder.build_agents(versions)
            self._sec_ua_map = self.ua_builder.build_sec_ua_map(versions)

    def get_agents(self) -> List[AgentTuple]:
        """Get all agent tuples."""
        return self._agents.copy()

    def get_sec_ua_map(self) -> SecUAMapping:
        """Get sec-ch-ua mapping."""
        return self._sec_ua_map.copy()

    def force_update(self) -> None:
        """Force refresh data from API, bypassing the cache."""
        self._load_data(force_refresh=True)
