"""
Tests for HeaderGenerator and user-facing API of MacWinUA.
Tests header generation, property access, and public functions.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from macwinua import ua, get_chrome_headers, force_update
from macwinua.ua import HeaderGenerator
from macwinua.core import DataManager
from macwinua.exceptions import UAError


# --- Fixtures ---


@pytest.fixture
def mock_data_manager():
    """Provides a mocked DataManager with test data."""
    mock_manager = MagicMock(spec=DataManager)

    # Mock agent data: (platform, os_version, chrome_version, ua_string)
    mock_agents = [
        (
            "mac",
            "Mac OS X 10_15_7",
            "139",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/139.0.0.0 Safari/537.36",
        ),
        (
            "mac",
            "Mac OS X 14_0",
            "139",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Chrome/139.0.0.0 Safari/537.36",
        ),
        (
            "win",
            "Windows NT 10.0; Win64; x64",
            "139",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/139.0.0.0 Safari/537.36",
        ),
        (
            "mac",
            "Mac OS X 10_15_7",
            "138",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/138.0.0.0 Safari/537.36",
        ),
        (
            "win",
            "Windows NT 10.0; Win64; x64",
            "138",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/138.0.0.0 Safari/537.36",
        ),
    ]

    # Mock sec-ch-ua mapping
    mock_sec_ua_map = {
        "139": '"Google Chrome";v="139", "Not/A)Brand";v="139", "Chromium";v="139"',
        "138": '"Google Chrome";v="138", "Not/A)Brand";v="138", "Chromium";v="138"',
    }

    mock_manager.get_agents.return_value = mock_agents
    mock_manager.get_sec_ua_map.return_value = mock_sec_ua_map

    return mock_manager


@pytest.fixture
def header_generator(mock_data_manager):
    """Provides HeaderGenerator instance with mocked data manager."""
    return HeaderGenerator(data_manager=mock_data_manager)


# --- HeaderGenerator Tests ---


class TestHeaderGenerator:
    """Tests for HeaderGenerator class."""

    def test_initialization_with_default_data_manager(self):
        """Should initialize with default DataManager when none provided."""
        # This will use the real DataManager, but we're just testing initialization
        generator = HeaderGenerator()
        assert generator._data_manager is not None

    def test_initialization_with_custom_data_manager(self, mock_data_manager):
        """Should use provided data manager."""
        generator = HeaderGenerator(data_manager=mock_data_manager)
        assert generator._data_manager is mock_data_manager

    # --- Property Tests ---

    def test_chrome_property(self, header_generator):
        """Should return a random Chrome User-Agent string."""
        ua_string = header_generator.chrome
        assert "Mozilla/5.0" in ua_string
        assert "Chrome/" in ua_string
        assert "Safari/537.36" in ua_string

    def test_mac_property(self, header_generator):
        """Should return a macOS Chrome User-Agent string."""
        ua_string = header_generator.mac
        assert "Macintosh" in ua_string
        assert "Mac OS X" in ua_string
        assert "Chrome/" in ua_string

    def test_windows_property(self, header_generator):
        """Should return a Windows Chrome User-Agent string."""
        ua_string = header_generator.windows
        assert "Windows NT" in ua_string
        assert "Chrome/" in ua_string

    def test_latest_property(self, header_generator):
        """Should return User-Agent from latest Chrome version."""
        ua_string = header_generator.latest
        assert "Chrome/139" in ua_string  # 139 is latest in mock data

    def test_latest_property_with_empty_sec_ua_map(self, mock_data_manager):
        """Should fallback to chrome property when sec-ua map is empty."""
        mock_data_manager.get_sec_ua_map.return_value = {}
        generator = HeaderGenerator(data_manager=mock_data_manager)

        # Should not raise error and return something
        ua_string = generator.latest
        assert "Chrome/" in ua_string

    def test_random_property(self, header_generator):
        """Should be alias for chrome property."""
        # We can't test exact equality due to randomness, but structure should be same
        random_ua = header_generator.random
        chrome_ua = header_generator.chrome

        # Both should be valid Chrome UAs
        assert "Mozilla/5.0" in random_ua
        assert "Chrome/" in random_ua
        assert "Mozilla/5.0" in chrome_ua
        assert "Chrome/" in chrome_ua

    # --- Header Generation Tests ---

    def test_get_headers_basic(self, header_generator):
        """Should generate complete headers dictionary."""
        headers = header_generator.get_headers()

        # Check required headers exist
        required_headers = [
            "User-Agent",
            "sec-ch-ua",
            "sec-ch-ua-platform",
            "sec-ch-ua-mobile",
            "Accept",
            "Accept-Language",
        ]

        for header in required_headers:
            assert header in headers

        # Check values are reasonable
        assert "Mozilla/5.0" in headers["User-Agent"]
        assert "Chrome/" in headers["User-Agent"]
        assert '"Google Chrome"' in headers["sec-ch-ua"]
        assert headers["sec-ch-ua-platform"] in ('"macOS"', '"Windows"')

    def test_get_headers_platform_mac(self, header_generator):
        """Should filter headers for macOS platform."""
        headers = header_generator.get_headers(platform="mac")

        assert "Macintosh" in headers["User-Agent"]
        assert headers["sec-ch-ua-platform"] == '"macOS"'

    def test_get_headers_platform_win(self, header_generator):
        """Should filter headers for Windows platform."""
        headers = header_generator.get_headers(platform="win")

        assert "Windows NT" in headers["User-Agent"]
        assert headers["sec-ch-ua-platform"] == '"Windows"'

    def test_get_headers_chrome_version(self, header_generator):
        """Should filter headers for specific Chrome version."""
        headers = header_generator.get_headers(chrome_version="138")

        assert "Chrome/138" in headers["User-Agent"]
        assert '"138"' in headers["sec-ch-ua"]

    def test_get_headers_combined_filters(self, header_generator):
        """Should handle multiple filter criteria."""
        headers = header_generator.get_headers(platform="mac", chrome_version="138")

        assert "Macintosh" in headers["User-Agent"]
        assert "Chrome/138" in headers["User-Agent"]
        assert headers["sec-ch-ua-platform"] == '"macOS"'

    def test_get_headers_extra_headers(self, header_generator):
        """Should merge extra headers into result."""
        extra = {"X-Custom-Header": "test-value", "Authorization": "Bearer token123"}

        headers = header_generator.get_headers(extra_headers=extra)

        assert headers["X-Custom-Header"] == "test-value"
        assert headers["Authorization"] == "Bearer token123"
        # Should still have default headers
        assert "User-Agent" in headers
        assert "Accept" in headers

    def test_get_headers_extra_headers_override_defaults(self, header_generator):
        """Should allow extra headers to override defaults."""
        extra = {"Accept": "application/json"}

        headers = header_generator.get_headers(extra_headers=extra)

        assert headers["Accept"] == "application/json"

    # --- Error Handling Tests ---

    def test_get_headers_invalid_platform_raises_error(self, header_generator):
        """Should raise UAError for invalid platform."""
        with pytest.raises(UAError, match="Platform must be 'mac' or 'win'"):
            header_generator.get_headers(platform="linux")

    def test_get_headers_invalid_chrome_version_raises_error(self, header_generator):
        """Should raise UAError for invalid Chrome version."""
        with pytest.raises(UAError, match="Chrome version must be one of"):
            header_generator.get_headers(chrome_version="999")

    def test_get_headers_no_matching_agents_raises_error(self, mock_data_manager):
        """Should raise UAError when no agents match criteria."""
        # Mock empty agents list
        mock_data_manager.get_agents.return_value = []
        generator = HeaderGenerator(data_manager=mock_data_manager)

        with pytest.raises(UAError, match="No matching user-agent found"):
            generator.get_headers()

    def test_get_matching_agents_platform_filter(self, header_generator):
        """Should correctly filter agents by platform."""
        mac_agents = header_generator._get_matching_agents(platform="mac")
        win_agents = header_generator._get_matching_agents(platform="win")

        # All mac agents should have 'mac' as first element
        assert all(agent[0] == "mac" for agent in mac_agents)
        # All win agents should have 'win' as first element
        assert all(agent[0] == "win" for agent in win_agents)

    def test_get_matching_agents_version_filter(self, header_generator):
        """Should correctly filter agents by Chrome version."""
        v138_agents = header_generator._get_matching_agents(chrome_version="138")
        v139_agents = header_generator._get_matching_agents(chrome_version="139")

        # All v138 agents should have '138' as third element
        assert all(agent[2] == "138" for agent in v138_agents)
        # All v139 agents should have '139' as third element
        assert all(agent[2] == "139" for agent in v139_agents)

    def test_force_update_calls_data_manager(self, header_generator, mock_data_manager):
        """Should call force_update on data manager."""
        header_generator.force_update()
        mock_data_manager.force_update.assert_called_once()


# --- Global Functions Tests ---


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    @patch("macwinua.ua.ua")
    def test_get_chrome_headers_calls_singleton(self, mock_ua):
        """Should call get_headers on singleton ua instance."""
        expected_headers = {"User-Agent": "test"}
        mock_ua.get_headers.return_value = expected_headers

        result = get_chrome_headers(platform="mac", chrome_version="139")

        mock_ua.get_headers.assert_called_once_with(platform="mac", chrome_version="139")
        assert result == expected_headers

    @patch("macwinua.ua.ua")
    def test_force_update_calls_singleton(self, mock_ua):
        """Should call force_update on singleton ua instance."""
        force_update()
        mock_ua.force_update.assert_called_once()


# --- Integration Tests ---


class TestIntegration:
    """Integration tests using the real singleton."""

    def test_singleton_ua_properties_work(self):
        """Should be able to access all properties of singleton ua."""
        # These use the real singleton, but should not fail
        assert isinstance(ua.chrome, str)
        assert isinstance(ua.mac, str)
        assert isinstance(ua.windows, str)
        assert isinstance(ua.latest, str)
        assert isinstance(ua.random, str)

        # All should contain Chrome
        assert "Chrome/" in ua.chrome
        assert "Chrome/" in ua.mac
        assert "Chrome/" in ua.windows
        assert "Chrome/" in ua.latest
        assert "Chrome/" in ua.random

    def test_singleton_ua_get_headers_works(self):
        """Should be able to generate headers with singleton ua."""
        headers = ua.get_headers()

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "sec-ch-ua" in headers
        assert "sec-ch-ua-platform" in headers

    def test_get_chrome_headers_function_works(self):
        """Should be able to use convenience function."""
        headers = get_chrome_headers(platform="mac")

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Macintosh" in headers["User-Agent"]
        assert headers["sec-ch-ua-platform"] == '"macOS"'


# --- Thread Safety Tests ---


class TestThreadSafety:
    """Tests for thread safety of HeaderGenerator."""

    def test_concurrent_header_generation(self, header_generator):
        """Should handle concurrent header generation safely."""
        errors = []

        def worker():
            try:
                for _ in range(20):
                    headers = header_generator.get_headers()
                    assert "User-Agent" in headers

                    _ = header_generator.chrome
                    _ = header_generator.mac
                    _ = header_generator.windows
                    _ = header_generator.latest
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Thread safety test failed: {errors}"

    def test_concurrent_property_access(self, header_generator):
        """Should handle concurrent property access safely."""
        results = []
        errors = []

        def worker():
            try:
                local_results = []
                for _ in range(10):
                    local_results.extend(
                        [
                            header_generator.chrome,
                            header_generator.mac,
                            header_generator.windows,
                            header_generator.latest,
                            header_generator.random,
                        ]
                    )
                results.extend(local_results)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Concurrent property access failed: {errors}"
        assert len(results) == 3 * 10 * 5  # 3 threads, 10 iterations, 5 properties
        # All results should be valid UA strings
        assert all("Chrome/" in result for result in results)


# --- Edge Cases Tests ---


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_empty_agents_list_handling(self, mock_data_manager):
        """Should handle empty agents list gracefully."""
        mock_data_manager.get_agents.return_value = []
        generator = HeaderGenerator(data_manager=mock_data_manager)

        # All methods should raise UAError
        with pytest.raises(UAError, match="No user agents available"):
            _ = generator.chrome

        with pytest.raises(UAError, match="No matching user-agent found"):
            _ = generator.mac

        with pytest.raises(UAError, match="No matching user-agent found"):
            _ = generator.windows

        with pytest.raises(UAError, match="No matching user-agent found"):
            generator.get_headers()

    def test_missing_platform_in_agents(self, mock_data_manager):
        """Should handle missing platform gracefully."""
        # Agents with only 'mac' platform
        mock_agents = [
            ("mac", "Mac OS X 10_15_7", "139", "Mozilla/5.0 (...) Chrome/139.0.0.0"),
        ]
        mock_data_manager.get_agents.return_value = mock_agents
        generator = HeaderGenerator(data_manager=mock_data_manager)

        # mac should work
        assert "Chrome/" in generator.mac

        # windows should raise error
        with pytest.raises(UAError, match="No matching user-agent found"):
            _ = generator.windows

    def test_version_filter_with_no_matches(self, mock_data_manager):
        """Should handle version filter with no matches."""
        mock_data_manager.get_sec_ua_map.return_value = {"139": "test"}
        # Agents only have version 138, but we'll ask for 139
        mock_agents = [
            ("mac", "Mac OS X 10_15_7", "138", "Mozilla/5.0 (...) Chrome/138.0.0.0"),
        ]
        mock_data_manager.get_agents.return_value = mock_agents
        generator = HeaderGenerator(data_manager=mock_data_manager)

        with pytest.raises(UAError, match="No matching user-agent found"):
            generator.get_headers(chrome_version="139")
