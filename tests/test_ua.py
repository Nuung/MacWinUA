"""
Tests for HeaderGenerator and user-facing API of MacWinUA.
Tests header generation, property access, and public functions.
"""

from unittest.mock import MagicMock

import pytest

from macwinua.ua import HeaderGenerator
from macwinua.core import DataManager
from macwinua.exceptions import UAError


# --- Fixtures ---
@pytest.fixture
def mock_data_manager():
    """Provides a mocked DataManager with test data."""
    mock_manager = MagicMock(spec=DataManager)
    mock_agents = [
        ("mac", "OSX", "139", "Mozilla/5.0 (Macintosh...) Chrome/139..."),
        ("win", "NT10", "139", "Mozilla/5.0 (Windows...) Chrome/139..."),
        ("mac", "OSX", "138", "Mozilla/5.0 (Macintosh...) Chrome/138..."),
    ]
    mock_sec_ua_map = {
        "139": '"Google Chrome";v="139"',
        "138": '"Google Chrome";v="138"',
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

    def test_chrome_property(self, header_generator):
        ua_string = header_generator.chrome
        assert "Chrome/" in ua_string

    def test_mac_property(self, header_generator):
        ua_string = header_generator.mac
        assert "Macintosh" in ua_string

    def test_windows_property(self, header_generator):
        ua_string = header_generator.windows
        assert "Windows" in ua_string

    def test_latest_property(self, header_generator):
        ua_string = header_generator.latest
        assert "Chrome/139" in ua_string

    def test_get_headers_basic(self, header_generator):
        headers = header_generator.get_headers()
        assert "User-Agent" in headers
        assert "sec-ch-ua" in headers
        assert "sec-ch-ua-platform" in headers

    def test_get_headers_platform_mac(self, header_generator):
        headers = header_generator.get_headers(platform="mac")
        assert "Macintosh" in headers["User-Agent"]
        assert headers["sec-ch-ua-platform"] == '"macOS"'

    def test_get_headers_chrome_version(self, header_generator):
        headers = header_generator.get_headers(chrome_version="138")
        assert "Chrome/138" in headers["User-Agent"]

    def test_get_headers_extra_headers(self, header_generator):
        extra = {"X-Custom": "Test"}
        headers = header_generator.get_headers(extra_headers=extra)
        assert headers["X-Custom"] == "Test"

    def test_get_headers_invalid_platform_raises_error(self, header_generator):
        with pytest.raises(UAError, match="Platform must be 'mac' or 'win'"):
            header_generator.get_headers(platform="linux")

    def test_get_headers_invalid_chrome_version_raises_error(self, header_generator):
        with pytest.raises(UAError, match="Chrome version must be one of"):
            header_generator.get_headers(chrome_version="999")

    def test_force_update_calls_data_manager(self, header_generator, mock_data_manager):
        header_generator.force_update()
        mock_data_manager.force_update.assert_called_once()

    # --- Edge Case Tests for Empty Data ---

    def test_chrome_property_raises_error_on_no_agents(self, header_generator, mock_data_manager):
        """Test that the chrome property raises UAError if no agents are available."""
        mock_data_manager.get_agents.return_value = []
        with pytest.raises(UAError, match="No user agents available"):
            _ = header_generator.chrome

    def test_mac_property_raises_error_on_no_matching_agents(self, header_generator, mock_data_manager):
        """Test that the mac property raises UAError if no matching agents are found."""
        # Simulate only Windows agents being available
        mock_data_manager.get_agents.return_value = [("win", "NT10", "139", "...")]
        with pytest.raises(UAError, match="No matching user-agent found"):
            _ = header_generator.mac

    def test_get_headers_raises_error_on_no_matching_agents(self, header_generator, mock_data_manager):
        """Test get_headers raises UAError if no agents match the criteria."""
        # Simulate data only for version "138"
        mock_data_manager.get_agents.return_value = [("mac", "OSX", "138", "...")]
        with pytest.raises(UAError, match="No matching user-agent found"):
            header_generator.get_headers(chrome_version="139")
