"""
Tests for the user-facing HeaderGenerator class and public functions of MacWinUA.
This suite ensures the public API is stable, predictable, and handles all
user inputs correctly. It uses a mocked DataProvider to completely isolate the
header generation logic from data acquisition (caching, API calls).
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from macwinua import force_update, get_chrome_headers, ua
from macwinua.exceptions import UAError
from macwinua.ua import HeaderGenerator


# --- Fixtures for Mocking and Isolation ---


@pytest.fixture
def mock_data() -> dict:
    """Provides a standard, predictable set of mock data for testing."""
    return {
        "agents": [
            ("mac", "Mac OS X 10_15_7", "139", "UA-MAC-139-A"),
            ("mac", "Mac OS X 14_0", "139", "UA-MAC-139-B"),
            ("win", "Windows NT 10.0", "139", "UA-WIN-139"),
            ("mac", "Mac OS X 10_15_7", "138", "UA-MAC-138"),
        ],
        "sec_ua": {
            "139": "SEC-UA-139",
            "138": "SEC-UA-138",
        },
    }


@pytest.fixture
def header_generator(mock_data: dict) -> HeaderGenerator:
    """
    Provides a HeaderGenerator instance isolated with mock data.
    This fixture ensures that tests are fast, predictable, and do not
    perform any I/O operations.
    """
    mock_provider = MagicMock()
    mock_provider.get_data.return_value = mock_data
    return HeaderGenerator(data_provider=mock_provider)


# --- Test Cases for HeaderGenerator ---


class TestHeaderGenerator:
    """Tests the functionality of the HeaderGenerator class."""

    def test_properties(self, header_generator: HeaderGenerator):
        """Should return correct UA strings for each property."""
        assert header_generator.chrome in [a[3] for a in header_generator._agents]
        assert header_generator.mac.startswith("UA-MAC-")
        assert header_generator.windows == "UA-WIN-139"
        assert header_generator.latest.startswith("UA-MAC-139") or header_generator.latest == "UA-WIN-139"
        assert header_generator.random is not None

    def test_get_headers_basic(self, header_generator: HeaderGenerator):
        """Should generate a complete set of valid headers."""
        headers = header_generator.get_headers()
        assert "User-Agent" in headers
        assert "sec-ch-ua" in headers
        assert "sec-ch-ua-platform" in headers
        assert "Accept-Language" in headers

    def test_get_headers_platform_filter(self, header_generator: HeaderGenerator):
        """Should correctly filter headers by platform."""
        mac_headers = header_generator.get_headers(platform="mac")
        assert mac_headers["sec-ch-ua-platform"] == '"macOS"'
        assert mac_headers["User-Agent"].startswith("UA-MAC-")

        win_headers = header_generator.get_headers(platform="win")
        assert win_headers["sec-ch-ua-platform"] == '"Windows"'
        assert win_headers["User-Agent"] == "UA-WIN-139"

    def test_get_headers_version_filter(self, header_generator: HeaderGenerator):
        """Should correctly filter headers by Chrome version."""
        headers = header_generator.get_headers(chrome_version="138")
        assert headers["User-Agent"] == "UA-MAC-138"
        assert headers["sec-ch-ua"] == "SEC-UA-138"

    def test_get_headers_combined_filters(self, header_generator: HeaderGenerator):
        """Should correctly filter headers with multiple criteria."""
        headers = header_generator.get_headers(platform="win", chrome_version="139")
        assert headers["User-Agent"] == "UA-WIN-139"

    def test_get_headers_no_match_raises_error(self, header_generator: HeaderGenerator):
        """Should raise UAError when no agent matches the specified criteria."""
        with pytest.raises(UAError, match="No matching user-agent found"):
            header_generator.get_headers(platform="win", chrome_version="138")

    def test_get_headers_invalid_platform_raises_error(self, header_generator: HeaderGenerator):
        """Should raise UAError for an invalid platform string."""
        with pytest.raises(UAError, match="Platform must be 'mac' or 'win'"):
            header_generator.get_headers(platform="linux")

    def test_get_headers_invalid_version_raises_error(self, header_generator: HeaderGenerator):
        """Should raise UAError for a non-existent Chrome version."""
        with pytest.raises(UAError, match="Chrome version must be one of: 139, 138"):
            header_generator.get_headers(chrome_version="99")

    def test_initialization_with_empty_data_raises_error(self):
        """Should raise UAError if initialized with an empty or partial data set."""
        empty_provider = MagicMock(get_data=MagicMock(return_value={}))
        with pytest.raises(UAError, match="Cannot initialize HeaderGenerator"):
            HeaderGenerator(data_provider=empty_provider)

        partial_provider = MagicMock(get_data=MagicMock(return_value={"agents": []}))
        with pytest.raises(UAError, match="Cannot initialize HeaderGenerator"):
            HeaderGenerator(data_provider=partial_provider)


# --- Test Cases for Public Functions and Singleton ---


@patch("macwinua.ua._data_provider_singleton")
def test_force_update_reloads_singleton_data(mock_provider: MagicMock):
    """
    Should call the provider's force_refresh and then reload data
    in the global `ua` instance, ensuring it gets the new data.
    """
    # Arrange: Define the new data that force_refresh will "fetch".
    new_data = {
        "agents": [("win", "OS", "999", "UA-NEW-999")],
        "sec_ua": {"999": "SEC-UA-999"},
    }
    # When force_refresh is called, it returns the new data.
    mock_provider.force_refresh.return_value = new_data
    # When ua._reload_data calls get_data, it should also get the new data.
    mock_provider.get_data.return_value = new_data

    # Act
    force_update()

    # Assert
    mock_provider.force_refresh.assert_called_once()
    assert ua.latest == "UA-NEW-999"  # Verify the singleton's data was reloaded.


@patch("macwinua.ua.ua.get_headers")
def test_get_chrome_headers_convenience_function(mock_get_headers: MagicMock):
    """
    Should call the get_headers method on the singleton `ua` instance
    with the correct arguments.
    """
    # Arrange
    expected_headers = {"User-Agent": "test"}
    mock_get_headers.return_value = expected_headers
    headers = get_chrome_headers(platform="mac", chrome_version="139")
    mock_get_headers.assert_called_once_with(platform="mac", chrome_version="139")
    assert headers == expected_headers


def test_thread_safety_of_singleton(mock_data):
    """
    Ensures that multiple threads can access the singleton `ua` instance
    properties and methods without race conditions or errors.
    """
    # CRITICAL FIX: Patch the provider and then explicitly reload the data
    # into the *existing* ua singleton instance to ensure it uses the mock data.
    with patch("macwinua.ua._data_provider_singleton") as mock_provider:
        mock_provider.get_data.return_value = mock_data

        # Manually reload the data into the already-imported `ua` instance
        ua._reload_data()

        errors = []

        def worker():
            try:
                for _ in range(20):
                    # Access properties and methods of the reloaded ua instance
                    _ = ua.chrome
                    _ = ua.mac
                    _ = ua.latest
                    _ = ua.get_headers(platform="mac")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety test failed with errors: {errors}"
