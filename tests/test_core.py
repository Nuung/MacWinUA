"""
Tests for core data processing components of MacWinUA.
Tests cache management, API fetching, and data coordination.
"""

import json
import time
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from macwinua.constants import CACHE_VALIDITY_DAYS, FALLBACK_VERSIONS
from macwinua.core import (
    CacheManager,
    ApiVersionFetcher,
    DataProvider,
    UADataBuilder,
    DataManager,
    get_default_cache_path,
)
from macwinua.exceptions import APIFetchError, DataValidationError


# --- Fixtures ---
@pytest.fixture
def temp_cache_path(tmp_path):
    """Provides temporary cache file path."""
    return tmp_path / "test_cache.json"


@pytest.fixture
def cache_manager(temp_cache_path):
    """Provides CacheManager instance."""
    return CacheManager(temp_cache_path)


@pytest.fixture
def mock_api_fetcher():
    """Provides a mocked VersionSource."""
    fetcher = MagicMock()
    fetcher.fetch.return_value = ["140", "139"]
    return fetcher


@pytest.fixture
def data_provider(cache_manager, mock_api_fetcher):
    """Provides DataProvider instance."""
    return DataProvider(cache_manager, mock_api_fetcher)


# --- get_default_cache_path Test ---
def test_get_default_cache_path():
    """Should return a path within the user's home directory."""
    with patch("os.path.expanduser", return_value="/fake/home"):
        path = get_default_cache_path()
        assert str(path) == "/fake/home/.macwinua/macwinua_cache.json"


# --- CacheManager Tests ---
class TestCacheManager:
    """Tests for cache management functionality."""

    def test_is_valid_nonexistent_file(self, cache_manager):
        assert not cache_manager.is_valid()

    def test_is_valid_fresh_cache(self, cache_manager, temp_cache_path):
        cache_data = {"versions": ["139", "138"], "timestamp": time.time()}
        temp_cache_path.write_text(json.dumps(cache_data))
        assert cache_manager.is_valid()

    def test_is_valid_expired_cache(self, cache_manager, temp_cache_path):
        old_timestamp = time.time() - (CACHE_VALIDITY_DAYS + 1) * 24 * 60 * 60
        cache_data = {"versions": ["139", "138"], "timestamp": old_timestamp}
        temp_cache_path.write_text(json.dumps(cache_data))
        assert not cache_manager.is_valid()

    def test_save_and_load_success(self, cache_manager, temp_cache_path):
        versions = ["139", "138"]
        cache_manager.save(versions)
        assert temp_cache_path.exists()
        loaded_versions = cache_manager.load()
        assert loaded_versions == versions


# --- ApiVersionFetcher Tests ---
class TestApiVersionFetcher:
    @patch("urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"versions": [{"version": "140.1.2.3"}, {"version": "139.4.5.6"}]}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fetcher = ApiVersionFetcher()
        versions = fetcher.fetch()
        assert versions == ["140", "139"]

    @patch("urllib.request.urlopen")
    def test_fetch_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Network down")
        fetcher = ApiVersionFetcher()
        with pytest.raises(APIFetchError, match="Network error"):
            fetcher.fetch()


# --- DataProvider Tests ---
class TestDataProvider:
    def test_get_versions_from_cache(self, data_provider):
        data_provider.cache_manager.load = MagicMock(return_value=["139"])
        versions = data_provider.get_versions()
        assert versions == ["139"]
        data_provider.version_fetcher.fetch.assert_not_called()

    def test_get_versions_from_api(self, data_provider, mock_api_fetcher):
        data_provider.cache_manager.load = MagicMock(return_value=None)
        data_provider.cache_manager.save = MagicMock()
        versions = data_provider.get_versions()
        assert versions == mock_api_fetcher.fetch.return_value
        mock_api_fetcher.fetch.assert_called_once()
        data_provider.cache_manager.save.assert_called_once_with(versions)

    def test_get_versions_api_fail_uses_fallback(self, data_provider):
        data_provider.cache_manager.load = MagicMock(return_value=None)
        data_provider.version_fetcher.fetch.side_effect = APIFetchError("API down")
        versions = data_provider.get_versions()
        assert versions == FALLBACK_VERSIONS


# --- UADataBuilder Tests ---
class TestUADataBuilder:
    def test_build_agents_success(self):
        agents = UADataBuilder.build_agents(["139"])
        assert len(agents) > 0
        assert "Chrome/139" in agents[0][3]

    def test_build_agents_empty_raises_error(self):
        with pytest.raises(DataValidationError):
            UADataBuilder.build_agents([])


# --- DataManager Tests ---
class TestDataManager:
    """Tests for high-level data management."""

    def test_initialization_loads_data(self, temp_cache_path, mock_api_fetcher):
        """Should load data during initialization."""
        dm = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        agents = dm.get_agents()
        sec_ua_map = dm.get_sec_ua_map()

        mock_api_fetcher.fetch.assert_called_once()
        assert len(agents) > 0
        assert "140" in sec_ua_map

    def test_get_agents_returns_copy(self, temp_cache_path, mock_api_fetcher):
        """Should return copy of agents to prevent external modification."""
        dm = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        agents1 = dm.get_agents()
        agents2 = dm.get_agents()
        assert agents1 == agents2
        assert agents1 is not agents2

    def test_force_update_refreshes_data(self, temp_cache_path, mock_api_fetcher):
        """Should refresh data when force_update is called."""
        # __init__ calls fetch once
        dm = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        # force_update calls fetch a second time
        dm.force_update()
        # The test now correctly asserts that 2 calls were made
        assert mock_api_fetcher.fetch.call_count == 2
