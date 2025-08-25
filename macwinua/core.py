"""
Core data processing components for MacWinUA library.
Handles caching, API fetching, and data management following SRP.
"""

import json
import time
import threading
from pathlib import Path
from typing import List, Optional
from urllib import request, error

from .constants import (
    API_URL,
    CACHE_VALIDITY_DAYS,
    API_TIMEOUT_SECONDS,
    SUPPORTED_VERSIONS,
    FALLBACK_VERSIONS,
    PLATFORMS,
    AgentTuple,
    SecUAMapping,
)
from .exceptions import CacheError, APIFetchError, DataValidationError


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


class VersionFetcher:
    """
    Fetches latest Chrome versions from Google API.
    Responsibility: API communication and response parsing
    """

    @staticmethod
    def fetch() -> List[str]:
        """Fetch latest Chrome versions from Google API."""
        try:
            req = request.Request(API_URL)
            req.add_header("User-Agent", "MacWinUA/1.0")

            with request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise APIFetchError(f"API returned status {response.status}")

                data = json.loads(response.read().decode("utf-8"))

                # Extract and filter versions
                versions = set()
                for item in data.get("versions", []):
                    version = item.get("version", "").split(".")[0]
                    if version in SUPPORTED_VERSIONS:
                        versions.add(version)

                if not versions:
                    raise APIFetchError("No supported versions found in API response")

                # Return sorted versions (latest first)
                return sorted(list(versions), key=int, reverse=True)

        except (error.URLError, error.HTTPError, TimeoutError) as e:
            raise APIFetchError(f"Network error: {e}") from e
        except json.JSONDecodeError as e:
            raise APIFetchError(f"Invalid JSON response: {e}") from e
        except Exception as e:
            raise APIFetchError(f"Unexpected API error: {e}") from e


class DataProvider:
    """
    Orchestrates data acquisition from cache and API.
    Responsibility: Data coordination and fallback logic
    """

    def __init__(self, cache_manager: CacheManager, version_fetcher: VersionFetcher):
        self.cache_manager = cache_manager
        self.version_fetcher = version_fetcher
        self._lock = threading.Lock()

    def get_versions(self, force_refresh: bool = False) -> List[str]:
        """Get Chrome versions with cache-first strategy."""
        if not force_refresh:
            # Try cache first
            try:
                cached_versions = self.cache_manager.load()
                if cached_versions:
                    return cached_versions
            except CacheError:
                # Cache error, continue to API
                pass

        # Try API
        try:
            api_versions = self.version_fetcher.fetch()
            # Save to cache for next time
            try:
                self.cache_manager.save(api_versions)
            except CacheError:
                # Cache save failed, but we have data from API
                pass
            return api_versions

        except APIFetchError:
            # API failed, use fallback
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
            sec_ua_map[version] = f'"Google Chrome";v="{version}", ' f'"Not/A)Brand";v="{version}", ' f'"Chromium";v="{version}"'

        return sec_ua_map


class DataManager:
    """
    High-level data management with singleton pattern.
    Responsibility: Coordinating all data operations and providing unified interface
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, cache_path: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, cache_path: Optional[Path] = None):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            # Initialize components
            if cache_path is None:
                cache_path = Path(__file__).parent / "macwinua_cache.json"

            self.cache_manager = CacheManager(cache_path)
            self.version_fetcher = VersionFetcher()
            self.data_provider = DataProvider(self.cache_manager, self.version_fetcher)
            self.ua_builder = UADataBuilder()

            # Load initial data
            self._load_data()
            self._initialized = True

    def _load_data(self):
        """Load and build all UA data."""
        versions = self.data_provider.get_versions()
        self._agents = self.ua_builder.build_agents(versions)
        self._sec_ua_map = self.ua_builder.build_sec_ua_map(versions)

    def get_agents(self) -> List[AgentTuple]:
        """Get all agent tuples."""
        return self._agents.copy()

    def get_sec_ua_map(self) -> SecUAMapping:
        """Get sec-ch-ua mapping."""
        return self._sec_ua_map.copy()

    def force_update(self) -> None:
        """Force refresh data from API."""
        with self._lock:
            versions = self.data_provider.get_versions(force_refresh=True)
            self._agents = self.ua_builder.build_agents(versions)
            self._sec_ua_map = self.ua_builder.build_sec_ua_map(versions)
