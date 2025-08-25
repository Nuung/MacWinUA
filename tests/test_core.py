"""
Tests for the core data provisioning components of MacWinUA.
These tests ensure that caching, API fetching, and fallback logic work correctly,
aiming for 100% test coverage of the core module.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib import error

import pytest

from macwinua.constants import CACHE_VALIDITY_SECONDS, FALLBACK_CHROME_VERSIONS
from macwinua.core import APIFetcher, CacheManager, DataProvider
from macwinua.exceptions import APIFetchError, CacheError, UAError


# --- Fixtures for Test Setup ---


@pytest.fixture
def mock_cache_path(tmp_path: Path) -> Path:
    """Provides a temporary path for cache files for test isolation."""
    return tmp_path / "macwinua_cache.json"


@pytest.fixture
def cache_manager(mock_cache_path: Path) -> CacheManager:
    """Provides a CacheManager instance configured with a temporary path."""
    return CacheManager(mock_cache_path)


@pytest.fixture(autouse=True)
def reset_dataprovider_singleton():
    """
    Ensures the DataProvider singleton is reset before each test, preventing
    state leakage between tests.
    """
    DataProvider._instance = None
    DataProvider._data = None


# --- Test Cases for CacheManager ---


class TestCacheManager:
    """Thoroughly tests the CacheManager class for all I/O scenarios."""

    def test_read_valid_cache(self, cache_manager: CacheManager, mock_cache_path: Path):
        """Should read and return data from a valid, non-expired cache file."""
        valid_data = {"timestamp": time.time(), "versions": ["100"]}
        mock_cache_path.write_text(json.dumps(valid_data))
        assert cache_manager.read() == valid_data

    def test_read_non_existent_cache(self, cache_manager: CacheManager):
        """Should return None when the cache file does not exist."""
        assert cache_manager.read() is None

    def test_read_expired_cache(self, cache_manager: CacheManager, mock_cache_path: Path):
        """Should return None when the cache file is expired."""
        expired_timestamp = time.time() - (CACHE_VALIDITY_SECONDS + 100)
        expired_data = {"timestamp": expired_timestamp, "versions": ["99"]}
        mock_cache_path.write_text(json.dumps(expired_data))
        assert cache_manager.read() is None

    def test_read_corrupted_json_raises_error(self, cache_manager: CacheManager, mock_cache_path: Path):
        """Should raise CacheError when the cache file contains invalid JSON."""
        mock_cache_path.write_text("{'key': 'not valid json'}")
        with pytest.raises(CacheError, match="is corrupted"):
            cache_manager.read()

    def test_read_missing_timestamp_is_treated_as_miss(self, cache_manager: CacheManager, mock_cache_path: Path):
        """Should return None if 'timestamp' key is missing, not raise an error."""
        corrupted_data = {"versions": ["100"]}  # No timestamp
        mock_cache_path.write_text(json.dumps(corrupted_data))
        # CRITICAL FIX: The test was correct, the implementation was wrong.
        # The test asserts that a missing timestamp is a "miss" (returns None),
        # which is the desired behavior. The fix is in core.py's CacheManager.read.
        # This test remains as is to validate the fix.
        assert cache_manager.read() is None

    def test_read_io_error_raises_error(self, mock_cache_path: Path):
        """Should raise CacheError on file read IO errors."""
        mock_cache_path.touch()
        with patch.object(Path, "open", side_effect=IOError("Permission denied")):
            cm = CacheManager(mock_cache_path)
            with pytest.raises(CacheError, match="Failed to read"):
                cm.read()

    def test_write_success(self, cache_manager: CacheManager, mock_cache_path: Path):
        """Should write data and a current timestamp to the cache file."""
        data_to_write = {"versions": ["101"]}
        cache_manager.write(data_to_write)
        content = json.loads(mock_cache_path.read_text())
        assert content["versions"] == ["101"]
        assert "timestamp" in content
        assert time.time() - content["timestamp"] < 5  # Check if timestamp is recent

    def test_write_io_error_raises_error(self, cache_manager: CacheManager):
        """Should raise CacheError on file write IO errors."""
        with patch.object(Path, "open", side_effect=IOError("Disk full")):
            with pytest.raises(CacheError, match="Failed to write"):
                cache_manager.write({"versions": ["102"]})


# --- Test Cases for APIFetcher ---


class TestAPIFetcher:
    """Thoroughly tests the APIFetcher for various network responses."""

    @patch("urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen):
        """Should return parsed and sorted versions on a successful API response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(
            {
                "versions": [
                    {"version": "140.0.1.2"},
                    {"version": "139.0.3.4"},
                    {"version": "141.0.0.0"},
                    {"version": "invalid"},
                ]
            }
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        assert APIFetcher.fetch_versions() == ["141", "140", "139"]

    @patch("urllib.request.urlopen")
    def test_fetch_http_error_raises_error(self, mock_urlopen):
        """Should raise APIFetchError on non-200 HTTP status codes."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response
        with pytest.raises(APIFetchError, match="status code: 404"):
            APIFetcher.fetch_versions()

    @pytest.mark.parametrize("exception", [error.URLError("Network down"), TimeoutError("Request timed out")])
    @patch("urllib.request.urlopen")
    def test_fetch_network_errors_raise_error(self, mock_urlopen, exception):
        """Should raise APIFetchError on various network-related errors."""
        mock_urlopen.side_effect = exception
        with pytest.raises(APIFetchError, match="Failed to fetch or parse"):
            APIFetcher.fetch_versions()

    @patch("urllib.request.urlopen")
    def test_fetch_invalid_json_raises_error(self, mock_urlopen):
        """Should raise APIFetchError if the API returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"not json"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        with pytest.raises(APIFetchError, match="Failed to fetch or parse"):
            APIFetcher.fetch_versions()


# --- Test Cases for DataProvider ---


class TestDataProvider:
    """Thoroughly tests the orchestration logic of the DataProvider class."""

    def test_priority_1_uses_valid_cache(self, cache_manager: CacheManager):
        """Should prioritize using data from a valid cache and not call the API."""
        cache_manager.read = MagicMock(return_value={"versions": ["123"]})
        mock_fetcher = MagicMock()
        provider = DataProvider(cache_manager, mock_fetcher)
        data = provider.get_data()
        assert "123" in data["sec_ua"]
        mock_fetcher.fetch_versions.assert_not_called()

    def test_priority_2_fetches_from_api_on_cache_miss(self, cache_manager: CacheManager):
        """Should fetch from API if cache is missing, and then write to cache."""
        cache_manager.read = MagicMock(return_value=None)
        cache_manager.write = MagicMock()
        mock_fetcher = MagicMock(fetch_versions=MagicMock(return_value=["140", "139"]))
        provider = DataProvider(cache_manager, mock_fetcher)
        data = provider.get_data()
        assert "140" in data["sec_ua"]
        mock_fetcher.fetch_versions.assert_called_once()
        cache_manager.write.assert_called_once_with({"versions": ["140", "139"]})

    def test_priority_3_uses_fallback_on_all_failures(self, cache_manager: CacheManager):
        """Should use fallback data if both reading cache and fetching API fail."""
        cache_manager.read = MagicMock(side_effect=CacheError("Cannot read"))
        mock_fetcher = MagicMock(fetch_versions=MagicMock(side_effect=APIFetchError("API down")))
        provider = DataProvider(cache_manager, mock_fetcher)
        data = provider.get_data()
        assert set(data["sec_ua"].keys()) == set(FALLBACK_CHROME_VERSIONS)

    def test_force_refresh_bypasses_cache_and_fetches_api(self, cache_manager: CacheManager):
        """force_refresh should ignore cache and fetch directly from the API."""
        cache_manager.read = MagicMock()  # Should not be called
        cache_manager.write = MagicMock()
        mock_fetcher = MagicMock(fetch_versions=MagicMock(return_value=["150"]))
        provider = DataProvider(cache_manager, mock_fetcher)
        provider.force_refresh()
        data = provider.get_data()  # get_data should now return the refreshed data
        assert "150" in data["sec_ua"]
        cache_manager.read.assert_not_called()
        mock_fetcher.fetch_versions.assert_called_once()
        cache_manager.write.assert_called_once_with({"versions": ["150"]})

    def test_generate_ua_data_with_empty_list_raises_error(self):
        """Should raise UAError if trying to generate data from an empty version list."""
        with pytest.raises(UAError, match="empty version list"):
            DataProvider._generate_ua_data([])

    def test_singleton_behavior(self, cache_manager: CacheManager):
        """Should always return the same instance of DataProvider."""
        mock_fetcher = MagicMock()
        instance1 = DataProvider(cache_manager, mock_fetcher)
        instance2 = DataProvider(cache_manager, mock_fetcher)
        assert instance1 is instance2
