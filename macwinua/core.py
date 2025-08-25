"""
This module handles the core logic of data provisioning for MacWinUA.
It is responsible for fetching, caching, and providing user-agent data
while adhering to the Single Responsibility Principle.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib import error, request

from .constants import API_URL, CACHE_VALIDITY_SECONDS, FALLBACK_CHROME_VERSIONS
from .exceptions import APIFetchError, CacheError, UAError

log = logging.getLogger(__name__)


class CacheManager:
    """Handles all file-based caching operations."""

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path

    def read(self) -> Optional[Dict]:
        """Reads and validates the cache file, raising CacheError on failure."""
        if not self.cache_path.exists():
            return None
        try:
            with self.cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # CRITICAL FIX: A missing timestamp is a cache miss, not a corruption error.
            if "timestamp" not in data:
                log.warning(f"Cache file at {self.cache_path} is missing a timestamp and will be ignored.")
                return None
            if time.time() - data.get("timestamp", 0) < CACHE_VALIDITY_SECONDS:
                return data
        except json.JSONDecodeError as e:
            raise CacheError(f"Cache file at {self.cache_path} is corrupted.") from e
        except IOError as e:
            raise CacheError(f"Failed to read cache file at {self.cache_path}.") from e
        return None  # Return None for expired cache

    def write(self, data: Dict):
        """Writes data to the cache file, raising CacheError on failure."""
        data["timestamp"] = time.time()
        try:
            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise CacheError(f"Failed to write to cache file at {self.cache_path}.") from e


class APIFetcher:
    """Fetches the latest version data from the remote API."""

    @staticmethod
    def fetch_versions() -> List[str]:
        """Fetches latest stable Chrome versions, raising APIFetchError on failure."""
        try:
            with request.urlopen(API_URL, timeout=5) as response:
                if response.status != 200:
                    raise APIFetchError(f"API request failed with status code: {response.status}")
                data = json.loads(response.read().decode("utf-8"))

                versions = {
                    item.get("version", "").split(".")[0]
                    for item in data.get("versions", [])
                    if item.get("version", "").split(".")[0].isdigit()
                }
                return sorted(list(versions), key=int, reverse=True)[:3]
        except (
            error.URLError,
            error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
        ) as e:
            raise APIFetchError("Failed to fetch or parse data from API.") from e


class DataProvider:
    """Orchestrates data acquisition and provides it to the application."""

    _instance = None
    _lock = threading.Lock()
    _data: Optional[Dict] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, cache_manager: CacheManager, api_fetcher: APIFetcher):
        self.cache_manager = cache_manager
        self.api_fetcher = api_fetcher

    def get_data(self) -> Dict:
        """Provides the user-agent data, loading it if not already present."""
        if self._data is None:
            with self._lock:
                if self._data is None:
                    self._data = self._load_data()
        return self._data

    def force_refresh(self) -> Dict:
        """Forces a refresh of the user-agent data from the API."""
        with self._lock:
            self._data = self._load_data(force_api_fetch=True)
        return self._data

    def _load_data(self, force_api_fetch: bool = False) -> Dict:
        """Core logic for loading data from cache, API, or fallback."""
        if not force_api_fetch:
            try:
                cached_data = self.cache_manager.read()
                if cached_data:
                    log.info("Loaded User-Agent data from cache.")
                    return self._generate_ua_data(cached_data["versions"])
            except CacheError as e:
                log.warning(f"Could not read cache: {e}")

        try:
            latest_versions = self.api_fetcher.fetch_versions()
            log.info(f"Fetched latest versions from API: {latest_versions}")
            self.cache_manager.write({"versions": latest_versions})
            return self._generate_ua_data(latest_versions)
        except (APIFetchError, CacheError) as e:
            log.warning(f"API fetch or cache write failed: {e}. Using fallback.")
            return self._generate_ua_data(FALLBACK_CHROME_VERSIONS)

    @staticmethod
    def _generate_ua_data(versions: List[str]) -> Dict:
        """Generates user-agent data from a list of versions."""
        if not versions:
            raise UAError("Cannot generate data from an empty version list.")
        agents = [
            (
                p,
                o,
                v,
                f"Mozilla/5.0 ({d}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36",
            )
            for v in versions
            for p, o, d in [
                ("mac", "Mac OS X 10_15_7", "Macintosh; Intel Mac OS X 10_15_7"),
                ("mac", "Mac OS X 14_0", "Macintosh; Intel Mac OS X 14_0"),
                ("win", "Windows NT 10.0; Win64; x64", "Windows NT 10.0; Win64; x64"),
            ]
        ]
        sec_ua = {v: f'"Google Chrome";v="{v}", "Not/A)Brand";v="{v}", "Chromium";v="{v}"' for v in versions}
        return {"agents": agents, "sec_ua": sec_ua}
