"""
Integration tests for the MacWinUA library.
Verifies the interaction between caching, API fetching, and header generation.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from macwinua.core import DataManager
from macwinua.ua import HeaderGenerator


@pytest.fixture
def temp_cache_path(tmp_path: Path) -> Path:
    """Provides a temporary cache file path for integration tests."""
    return tmp_path / ".macwinua" / "test_cache.json"


@pytest.fixture
def mock_api_fetcher() -> MagicMock:
    """Provides a mock version fetcher that simulates API calls."""
    fetcher = MagicMock()
    fetcher.fetch.return_value = ["140", "139", "138"]
    return fetcher


class TestIntegration:
    """
    Tests the full workflow of the library, including caching and data fetching.
    """

    def test_full_lifecycle_api_to_cache(self, temp_cache_path, mock_api_fetcher):
        """
        Tests the full lifecycle:
        1. First initialization triggers an API call (mocked).
        2. Data is saved to the cache file.
        3. Second initialization reads from the now-valid cache, avoiding an API call.
        """
        # 1. First run: Cache is empty, should call API
        dm1 = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        hg1 = HeaderGenerator(data_manager=dm1)

        headers1 = hg1.get_headers(chrome_version="140")
        assert "Chrome/140" in headers1["User-Agent"]

        mock_api_fetcher.fetch.assert_called_once()
        assert temp_cache_path.exists()
        with temp_cache_path.open("r") as f:
            cache_data = json.load(f)
            assert cache_data["versions"] == ["140", "139", "138"]

        # 2. Second run: Cache is valid, should NOT call API
        mock_api_fetcher.fetch.reset_mock()

        dm2 = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        hg2 = HeaderGenerator(data_manager=dm2)

        headers2 = hg2.get_headers(chrome_version="139")
        assert "Chrome/139" in headers2["User-Agent"]

        mock_api_fetcher.fetch.assert_not_called()

    def test_force_update_bypasses_cache(self, temp_cache_path, mock_api_fetcher):
        """
        Tests that force_update() correctly bypasses a valid cache and calls the API.
        """
        cache_content = {"versions": ["130"], "timestamp": time.time()}
        temp_cache_path.parent.mkdir(exist_ok=True)
        with temp_cache_path.open("w") as f:
            json.dump(cache_content, f)

        dm = DataManager(cache_path=temp_cache_path, version_fetcher=mock_api_fetcher)
        hg = HeaderGenerator(data_manager=dm)

        # Force an update
        hg.force_update()

        # The new versions from the API should now be available
        headers = hg.get_headers(chrome_version="140")
        assert "Chrome/140" in headers["User-Agent"]

        mock_api_fetcher.fetch.assert_called_once()
