"""
Tests for the MacWinUA package's public API (__init__.py).
Ensures that convenience instances and functions are correctly exposed and operational.
"""

from unittest.mock import patch

from macwinua import HeaderGenerator, ua, get_chrome_headers, force_update
from macwinua import __version__ as lib_version


def test_ua_instance_is_header_generator():
    """Verify that the `ua` instance is of the correct type."""
    assert isinstance(ua, HeaderGenerator)


@patch("macwinua.ua.HeaderGenerator.get_headers")
def test_get_chrome_headers_convenience_function(mock_get_headers):
    """Test that the `get_chrome_headers` function calls the method on the `ua` instance."""
    get_chrome_headers(platform="mac")
    mock_get_headers.assert_called_once_with(platform="mac")


@patch("macwinua.ua.HeaderGenerator.force_update")
def test_force_update_convenience_function(mock_force_update):
    """Test that the `force_update` function calls the method on the `ua` instance."""
    force_update()
    mock_force_update.assert_called_once()


def test_version_is_a_string():
    """Verify that the __version__ is defined and is a string."""
    assert isinstance(lib_version, str)
    assert len(lib_version.split(".")) == 3
