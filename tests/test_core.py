"""
Tests for core data processing components of MacWinUA.
Tests cache management, API fetching, and data coordination.
"""

import json
import time
import threading
from unittest.mock import MagicMock, patch
from urllib.error import URLError
import pytest
from macwinua.constants import CACHE_VALIDITY_DAYS, FALLBACK_VERSIONS
from macwinua.core import (
    CacheManager,
    VersionFetcher,
    DataProvider,
    UADataBuilder,
    DataManager,
)
from macwinua.exceptions import CacheError, APIFetchError, DataValidationError


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
def version_fetcher():
    """Provides VersionFetcher instance."""
    return VersionFetcher()


@pytest.fixture
def data_provider(cache_manager, version_fetcher):
    """Provides DataProvider instance."""
    return DataProvider(cache_manager, version_fetcher)


@pytest.fixture(autouse=True)
def reset_data_manager_singleton():
    """Reset DataManager singleton before each test."""
    DataManager._instance = None
    DataManager._initialized = False


# --- CacheManager Tests ---
class TestCacheManager:
    """Tests for cache management functionality."""

    def test_is_valid_nonexistent_file(self, cache_manager):
        """Should return False for non-existent cache file."""
        assert not cache_manager.is_valid()

    def test_is_valid_fresh_cache(self, cache_manager, temp_cache_path):
        """Should return True for fresh cache."""
        cache_data = {"versions": ["139", "138"], "timestamp": time.time()}
        temp_cache_path.write_text(json.dumps(cache_data))
        assert cache_manager.is_valid()

    def test_is_valid_expired_cache(self, cache_manager, temp_cache_path):
        """Should return False for expired cache."""
        old_timestamp = time.time() - (CACHE_VALIDITY_DAYS + 1) * 24 * 60 * 60
        cache_data = {"versions": ["139", "138"], "timestamp": old_timestamp}
        temp_cache_path.write_text(json.dumps(cache_data))
        assert not cache_manager.is_valid()

    def test_is_valid_corrupted_file(self, cache_manager, temp_cache_path):
        """Should return False for corrupted JSON file."""
        temp_cache_path.write_text("invalid json")
        assert not cache_manager.is_valid()

    def test_is_valid_missing_timestamp(self, cache_manager, temp_cache_path):
        """Should return False for cache missing timestamp."""
        cache_data = {"versions": ["139"]}  # No timestamp
        temp_cache_path.write_text(json.dumps(cache_data))
        assert not cache_manager.is_valid()

    def test_load_valid_cache(self, cache_manager, temp_cache_path):
        """Should load versions from valid cache."""
        versions = ["139", "138", "137"]
        cache_data = {"versions": versions, "timestamp": time.time()}
        temp_cache_path.write_text(json.dumps(cache_data))
        loaded_versions = cache_manager.load()
        assert loaded_versions == versions

    def test_load_invalid_cache_returns_none(self, cache_manager):
        """Should return None for invalid cache."""
        assert cache_manager.load() is None

    def test_load_empty_versions_returns_none(self, cache_manager, temp_cache_path):
        """Should return None for cache with empty versions."""
        cache_data = {"versions": [], "timestamp": time.time()}
        temp_cache_path.write_text(json.dumps(cache_data))
        assert cache_manager.load() is None

    @patch("pathlib.Path.open")
    @patch.object(CacheManager, "is_valid", return_value=True)
    def test_load_io_error_raises_cache_error(self, mock_is_valid, mock_path_open, cache_manager, temp_cache_path):
        """
        Tests that CacheError is raised when an I/O error occurs in the load() method.
        is_valid() is mocked to return True to simplify the test.
        """
        mock_path_open.side_effect = IOError("Read error")
        with pytest.raises(CacheError, match="Failed to load cache"):
            cache_manager.load()

        mock_is_valid.assert_called_once()
        mock_path_open.assert_called_once()

    def test_save_success(self, cache_manager, temp_cache_path):
        """Should save versions with timestamp."""
        versions = ["139", "138"]
        cache_manager.save(versions)
        # Verify file was created
        assert temp_cache_path.exists()
        # Verify content
        with temp_cache_path.open("r") as f:
            data = json.load(f)
        assert data["versions"] == versions
        assert "timestamp" in data
        assert isinstance(data["timestamp"], float)

    def test_save_empty_versions_raises_error(self, cache_manager):
        """Should raise DataValidationError for empty versions."""
        with pytest.raises(DataValidationError, match="Cannot save empty versions"):
            cache_manager.save([])

    @patch("pathlib.Path.open")
    def test_save_io_error_raises_cache_error(self, mock_open_method, cache_manager):
        """Should raise CacheError on I/O error."""
        mock_open_method.side_effect = IOError("Write error")
        with pytest.raises(CacheError, match="Failed to save cache"):
            cache_manager.save(["139"])

    @patch("pathlib.Path.open")
    def test_save_permission_error_raises_cache_error(self, mock_open_method, cache_manager):
        """Should raise CacheError on permission error."""
        mock_open_method.side_effect = PermissionError("Permission denied")
        with pytest.raises(CacheError, match="Failed to save cache"):
            cache_manager.save(["139"])

    def test_save_creates_parent_directory(self, tmp_path):
        """Should create parent directory if it doesn't exist."""
        nested_path = tmp_path / "nested" / "dir" / "cache.json"
        cache_manager = CacheManager(nested_path)
        cache_manager.save(["139"])
        assert nested_path.exists()


# --- VersionFetcher Tests ---
class TestVersionFetcher:
    """Tests for API version fetching."""

    @patch("urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen):
        """Should successfully fetch and parse versions."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(
            {
                "versions": [
                    {"version": "139.0.1.0"},
                    {"version": "138.0.2.0"},
                    {"version": "137.0.3.0"},
                    {"version": "136.0.4.0"},  # Should be filtered out
                ]
            }
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        versions = VersionFetcher.fetch()
        assert versions == ["139", "138", "137"]  # Latest first, only supported

    @patch("urllib.request.urlopen")
    def test_fetch_http_error(self, mock_urlopen):
        """Should raise APIFetchError for HTTP error status."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(APIFetchError, match="API returned status 404"):
            VersionFetcher.fetch()

    @patch("urllib.request.urlopen")
    def test_fetch_network_error(self, mock_urlopen):
        """Should raise APIFetchError for network errors."""
        mock_urlopen.side_effect = URLError("Network error")

        with pytest.raises(APIFetchError, match="Network error"):
            VersionFetcher.fetch()

    @patch("urllib.request.urlopen")
    def test_fetch_timeout_error(self, mock_urlopen):
        """Should raise APIFetchError for timeout."""
        mock_urlopen.side_effect = TimeoutError("Request timeout")

        with pytest.raises(APIFetchError, match="Network error"):
            VersionFetcher.fetch()

    @patch("urllib.request.urlopen")
    def test_fetch_invalid_json(self, mock_urlopen):
        """Should raise APIFetchError for invalid JSON."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"not json"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(APIFetchError, match="Invalid JSON response"):
            VersionFetcher.fetch()

    @patch("urllib.request.urlopen")
    def test_fetch_no_supported_versions(self, mock_urlopen):
        """Should raise APIFetchError when no supported versions found."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(
            {
                "versions": [
                    {"version": "136.0.1.0"},  # Not supported
                    {"version": "135.0.2.0"},  # Not supported
                ]
            }
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(APIFetchError, match="No supported versions found"):
            VersionFetcher.fetch()


# --- DataProvider Tests ---
class TestDataProvider:
    """Tests for data coordination logic."""

    def test_get_versions_from_cache_success(self, data_provider):
        """Should return cached versions when cache is valid."""
        cached_versions = ["139", "138"]
        data_provider.cache_manager.load = MagicMock(return_value=cached_versions)

        versions = data_provider.get_versions()
        assert versions == cached_versions

        # API should not be called
        data_provider.version_fetcher.fetch = MagicMock()
        data_provider.version_fetcher.fetch.assert_not_called()

    def test_get_versions_cache_miss_api_success(self, data_provider):
        """Should fetch from API when cache is invalid."""
        api_versions = ["139", "138", "137"]
        data_provider.cache_manager.load = MagicMock(return_value=None)
        data_provider.version_fetcher.fetch = MagicMock(return_value=api_versions)
        data_provider.cache_manager.save = MagicMock()

        versions = data_provider.get_versions()
        assert versions == api_versions
        data_provider.version_fetcher.fetch.assert_called_once()
        data_provider.cache_manager.save.assert_called_once_with(api_versions)

    def test_get_versions_cache_error_api_success(self, data_provider):
        """Should handle cache error gracefully and use API."""
        api_versions = ["139", "138"]
        data_provider.cache_manager.load = MagicMock(side_effect=CacheError("Cache error"))
        data_provider.version_fetcher.fetch = MagicMock(return_value=api_versions)
        data_provider.cache_manager.save = MagicMock()

        versions = data_provider.get_versions()
        assert versions == api_versions
        data_provider.version_fetcher.fetch.assert_called_once()

    def test_get_versions_api_error_uses_fallback(self, data_provider):
        """Should use fallback versions when API fails."""
        data_provider.cache_manager.load = MagicMock(return_value=None)
        data_provider.version_fetcher.fetch = MagicMock(side_effect=APIFetchError("API error"))

        versions = data_provider.get_versions()
        assert versions == FALLBACK_VERSIONS

    def test_get_versions_force_refresh_bypasses_cache(self, data_provider):
        """Should bypass cache when force_refresh is True."""
        api_versions = ["139"]
        data_provider.cache_manager.load = MagicMock()
        data_provider.version_fetcher.fetch = MagicMock(return_value=api_versions)
        data_provider.cache_manager.save = MagicMock()

        versions = data_provider.get_versions(force_refresh=True)
        assert versions == api_versions
        data_provider.cache_manager.load.assert_not_called()
        data_provider.version_fetcher.fetch.assert_called_once()

    def test_get_versions_cache_save_error_handled(self, data_provider):
        """Should handle cache save error gracefully."""
        api_versions = ["139", "138"]
        data_provider.cache_manager.load = MagicMock(return_value=None)
        data_provider.version_fetcher.fetch = MagicMock(return_value=api_versions)
        data_provider.cache_manager.save = MagicMock(side_effect=CacheError("Save error"))

        # Should still return API versions despite cache save error
        versions = data_provider.get_versions()
        assert versions == api_versions


# --- UADataBuilder Tests ---
class TestUADataBuilder:
    """Tests for User-Agent data building logic."""

    def test_build_agents_success(self):
        """Should build agent tuples correctly."""
        versions = ["139", "138"]
        agents = UADataBuilder.build_agents(versions)

        # Should have agents for both versions and all platforms
        assert len(agents) > 0

        # Check structure of first agent
        platform, os_version, version, ua_string = agents[0]
        assert platform in ("mac", "win")
        assert version in versions
        assert "Mozilla/5.0" in ua_string
        assert f"Chrome/{version}" in ua_string

    def test_build_agents_empty_versions_raises_error(self):
        """Should raise DataValidationError for empty versions."""
        with pytest.raises(DataValidationError, match="Cannot build agents from empty versions"):
            UADataBuilder.build_agents([])

    def test_build_agents_contains_all_platforms(self):
        """Should include agents for all supported platforms."""
        versions = ["139"]
        agents = UADataBuilder.build_agents(versions)
        platforms = set(agent[0] for agent in agents)
        assert "mac" in platforms
        assert "win" in platforms

    def test_build_sec_ua_map_success(self):
        """Should build sec-ch-ua mapping correctly."""
        versions = ["139", "138", "137"]
        sec_ua_map = UADataBuilder.build_sec_ua_map(versions)

        assert len(sec_ua_map) == 3
        for version in versions:
            assert version in sec_ua_map
            assert f'"Google Chrome";v="{version}"' in sec_ua_map[version]
            assert f'"Chromium";v="{version}"' in sec_ua_map[version]

    def test_build_sec_ua_map_empty_versions_raises_error(self):
        """Should raise DataValidationError for empty versions."""
        with pytest.raises(DataValidationError, match="Cannot build sec-ua map from empty versions"):
            UADataBuilder.build_sec_ua_map([])


# --- DataManager Tests ---
class TestDataManager:
    """Tests for high-level data management."""

    def test_singleton_behavior(self, temp_cache_path):
        """Should implement singleton pattern correctly."""
        manager1 = DataManager(temp_cache_path)
        manager2 = DataManager(temp_cache_path)
        assert manager1 is manager2

    def test_initialization_loads_data(self, temp_cache_path):
        """Should load data during initialization."""
        with patch.object(DataProvider, "get_versions", return_value=["139", "138"]):
            manager = DataManager(temp_cache_path)
            agents = manager.get_agents()
            sec_ua_map = manager.get_sec_ua_map()

            assert len(agents) > 0
            assert len(sec_ua_map) > 0
            assert "139" in sec_ua_map
            assert "138" in sec_ua_map

    def test_get_agents_returns_copy(self, temp_cache_path):
        """Should return copy of agents to prevent external modification."""
        with patch.object(DataProvider, "get_versions", return_value=["139"]):
            manager = DataManager(temp_cache_path)
            agents1 = manager.get_agents()
            agents2 = manager.get_agents()

            # Should be equal but not same object
            assert agents1 == agents2
            assert agents1 is not agents2

    def test_get_sec_ua_map_returns_copy(self, temp_cache_path):
        """Should return copy of sec-ua map to prevent external modification."""
        with patch.object(DataProvider, "get_versions", return_value=["139"]):
            manager = DataManager(temp_cache_path)
            map1 = manager.get_sec_ua_map()
            map2 = manager.get_sec_ua_map()

            # Should be equal but not same object
            assert map1 == map2
            assert map1 is not map2

    def test_force_update_refreshes_data(self, temp_cache_path):
        """Should refresh data when force_update is called."""
        with patch.object(DataProvider, "get_versions") as mock_get_versions:
            # First call during initialization
            mock_get_versions.return_value = ["138"]
            manager = DataManager(temp_cache_path)

            # Second call during force_update
            mock_get_versions.return_value = ["139"]
            manager.force_update()

            # Should have been called twice (init + force_update)
            assert mock_get_versions.call_count == 2
            # Check that force_refresh was used in second call
            mock_get_versions.assert_called_with(force_refresh=True)


# --- Thread Safety Tests ---
class TestThreadSafety:
    """Tests for thread safety of core components."""

    def test_cache_manager_thread_safety(self, temp_cache_path):
        """Should handle concurrent cache operations safely."""
        cache_manager = CacheManager(temp_cache_path)
        errors = []

        def worker(worker_id):
            try:
                versions = [f"13{worker_id}"]
                cache_manager.save(versions)
                loaded = cache_manager.load()
                assert loaded is not None
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # File should exist and be valid JSON
        assert temp_cache_path.exists()
        with temp_cache_path.open("r") as f:
            data = json.load(f)  # Should not raise
        assert "versions" in data
        assert "timestamp" in data

    def test_data_manager_thread_safety(self, temp_cache_path):
        """Should handle concurrent access to DataManager safely."""
        with patch.object(DataProvider, "get_versions", return_value=["139", "138"]):
            errors = []

            def worker():
                try:
                    manager = DataManager(temp_cache_path)
                    for _ in range(10):
                        agents = manager.get_agents()
                        sec_ua_map = manager.get_sec_ua_map()
                        assert len(agents) > 0
                        assert len(sec_ua_map) > 0
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker) for _ in range(3)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            assert not errors, f"Thread safety test failed: {errors}"
