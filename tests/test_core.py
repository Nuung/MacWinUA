"""
Tests for core data processing components of MacWinUA.
Tests cache management, API fetching, and data coordination.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from macwinua.constants import CACHE_VALIDITY_DAYS, FALLBACK_VERSIONS
from macwinua.core import (
    ApiVersionFetcher,
    CacheManager,
    DataManager,
    DataProvider,
    UADataBuilder,
    get_default_cache_path,
)
from macwinua.exceptions import APIFetchError, CacheError, DataValidationError


# --- Fixtures ---
@pytest.fixture
def temp_cache_path(tmp_path: Path) -> Path:
    """Provides temporary cache file path."""
    return tmp_path / "test_cache.json"


@pytest.fixture
def cache_manager(temp_cache_path: Path) -> CacheManager:
    """Provides CacheManager instance."""
    return CacheManager(temp_cache_path)


@pytest.fixture
def mock_api_fetcher() -> MagicMock:
    """Provides a mocked VersionSource."""
    fetcher = MagicMock()
    fetcher.fetch.return_value = ["140", "139"]
    return fetcher


# --- get_default_cache_path Test ---
def test_get_default_cache_path():
    """Should return a path within the user's home directory."""
    with patch("os.path.expanduser", return_value="/fake/home"):
        path = get_default_cache_path()
        assert str(path) == "/fake/home/.macwinua/macwinua_cache.json"


# --- CacheManager Tests ---
class TestCacheManager:
    """Tests for cache management functionality."""

    def test_is_valid_nonexistent_file(self, cache_manager: CacheManager):
        assert not cache_manager.is_valid()

    def test_is_valid_fresh_cache(self, cache_manager: CacheManager, temp_cache_path: Path):
        cache_data = {"versions": ["139", "138"], "timestamp": time.time()}
        temp_cache_path.write_text(json.dumps(cache_data))
        assert cache_manager.is_valid()

    def test_is_valid_expired_cache(self, cache_manager: CacheManager, temp_cache_path: Path):
        old_timestamp = time.time() - (CACHE_VALIDITY_DAYS + 1) * 24 * 60 * 60
        cache_data = {"versions": ["139", "138"], "timestamp": old_timestamp}
        temp_cache_path.write_text(json.dumps(cache_data))
        assert not cache_manager.is_valid()

    def test_is_valid_corrupted_json(self, cache_manager: CacheManager, temp_cache_path: Path):
        temp_cache_path.write_text("not a valid json")
        assert not cache_manager.is_valid()

    def test_load_returns_none_when_cache_is_corrupted(self, cache_manager: CacheManager, temp_cache_path: Path):
        """
        Tests that load() returns None if the cache file is corrupted.
        A corrupted file is considered an invalid cache, not an error condition,
        allowing the DataProvider to fall back to the API.
        """
        # Arrange: Create a file with a valid timestamp but corrupted content
        valid_timestamp_cache = {"versions": ["139"], "timestamp": time.time()}
        temp_cache_path.write_text(json.dumps(valid_timestamp_cache))
        temp_cache_path.write_text("{corrupted_json")  # Overwrite with corrupt data

        # Act & Assert: load() should handle the corruption gracefully and return None
        assert cache_manager.load() is None

    def test_save_and_load_success(self, cache_manager: CacheManager, temp_cache_path: Path):
        versions = ["139", "138"]
        cache_manager.save(versions)
        assert temp_cache_path.exists()
        loaded_versions = cache_manager.load()
        assert loaded_versions == versions

    def test_save_empty_versions_raises_error(self, cache_manager: CacheManager):
        with pytest.raises(DataValidationError):
            cache_manager.save([])

    @patch("pathlib.Path.open")
    def test_save_raises_cache_error_on_io_error(self, mock_open, cache_manager: CacheManager):
        mock_open.side_effect = IOError("Permission denied")
        with pytest.raises(CacheError, match="Failed to save cache"):
            cache_manager.save(["139"])


# --- ApiVersionFetcher Tests ---
class TestApiVersionFetcher:
    """Tests for API fetching functionality."""

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

    @patch("urllib.request.urlopen")
    def test_fetch_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError("url", 500, "Server Error", {}, None)
        fetcher = ApiVersionFetcher()
        with pytest.raises(APIFetchError, match="Network error"):
            fetcher.fetch()

    @patch("urllib.request.urlopen")
    def test_fetch_non_200_status(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fetcher = ApiVersionFetcher()
        with pytest.raises(APIFetchError, match="API returned status 404"):
            fetcher.fetch()

    @patch("urllib.request.urlopen")
    def test_fetch_invalid_json_response(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"this is not json"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fetcher = ApiVersionFetcher()
        with pytest.raises(APIFetchError, match="Invalid JSON response"):
            fetcher.fetch()

    @patch("urllib.request.urlopen")
    def test_fetch_no_versions_in_response(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"data": "empty"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        fetcher = ApiVersionFetcher()
        with pytest.raises(APIFetchError, match="No valid versions found"):
            fetcher.fetch()


# --- DataProvider Tests ---
class TestDataProvider:
    """Tests for data coordination and fallback logic."""

    def test_get_versions_from_valid_cache(self, cache_manager: CacheManager, mock_api_fetcher):
        cache_manager.save(["139", "138"])
        provider = DataProvider(cache_manager, mock_api_fetcher)
        versions = provider.get_versions()
        assert versions == ["139", "138"]
        mock_api_fetcher.fetch.assert_not_called()

    def test_get_versions_from_api_when_cache_invalid(self, cache_manager: CacheManager, mock_api_fetcher):
        provider = DataProvider(cache_manager, mock_api_fetcher)
        versions = provider.get_versions()
        assert versions == ["140", "139"]
        mock_api_fetcher.fetch.assert_called_once()

    def test_get_versions_api_fail_uses_fallback(self, cache_manager: CacheManager, mock_api_fetcher):
        mock_api_fetcher.fetch.side_effect = APIFetchError("API down")
        provider = DataProvider(cache_manager, mock_api_fetcher)
        versions = provider.get_versions()
        assert versions == FALLBACK_VERSIONS

    def test_get_versions_cache_read_error_falls_back_to_api(self, cache_manager: CacheManager, mock_api_fetcher):
        cache_manager.load = MagicMock(side_effect=CacheError("Read failed"))
        provider = DataProvider(cache_manager, mock_api_fetcher)
        versions = provider.get_versions()
        assert versions == ["140", "139"]
        mock_api_fetcher.fetch.assert_called_once()

    def test_get_versions_api_works_but_cache_save_fails(self, cache_manager: CacheManager, mock_api_fetcher):
        cache_manager.save = MagicMock(side_effect=CacheError("Write failed"))
        provider = DataProvider(cache_manager, mock_api_fetcher)
        versions = provider.get_versions()
        assert versions == ["140", "139"]  # Should still return API data
        mock_api_fetcher.fetch.assert_called_once()
        cache_manager.save.assert_called_once()


# --- UADataBuilder Tests ---
class TestUADataBuilder:
    """Tests for data transformation logic."""

    def test_build_agents_success(self):
        agents = UADataBuilder.build_agents(["139"])
        assert len(agents) > 0
        assert "Chrome/139" in agents[0][3]
        assert agents[0][0] in ("mac", "win")

    def test_build_agents_empty_raises_error(self):
        with pytest.raises(DataValidationError):
            UADataBuilder.build_agents([])

    def test_build_sec_ua_map_success(self):
        sec_map = UADataBuilder.build_sec_ua_map(["139"])
        assert "139" in sec_map
        assert 'v="139"' in sec_map["139"]

    def test_build_sec_ua_map_empty_raises_error(self):
        with pytest.raises(DataValidationError):
            UADataBuilder.build_sec_ua_map([])


# --- DataManager Tests ---
class TestDataManager:
    """Tests for high-level data management."""

    def test_initialization_does_not_load_data(self, temp_cache_path: Path, mock_api_fetcher):
        """Should NOT load data during initialization."""
        dm = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        mock_api_fetcher.fetch.assert_not_called()
        assert not dm._is_loaded

    def test_lazy_loading_on_first_access(self, temp_cache_path: Path, mock_api_fetcher):
        """Should load data on the first call to a getter."""
        dm = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        agents = dm.get_agents()
        mock_api_fetcher.fetch.assert_called_once()
        assert len(agents) > 0
        assert dm._is_loaded

    def test_force_update_refreshes_data(self, temp_cache_path: Path, mock_api_fetcher):
        """Should refresh data when force_update is called."""
        dm = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        dm.get_agents()  # First call, loads data
        dm.force_update()  # Second call, re-loads data
        assert mock_api_fetcher.fetch.call_count == 2
