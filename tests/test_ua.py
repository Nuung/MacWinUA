"""
Tests for the simplified MacWinUA library.
"""

import pytest

from macwinua import ChromeUA, get_chrome_headers, ua


def test_chrome_ua_properties():
    """Test the basic properties of ChromeUA."""
    # Test chrome property returns a string
    assert isinstance(ua.chrome, str)
    assert "Chrome" in ua.chrome

    # Test mac property returns a macOS UA
    assert isinstance(ua.mac, str)
    assert "Macintosh" in ua.mac

    # Test windows property returns a Windows UA
    assert isinstance(ua.windows, str)
    assert "Windows" in ua.windows

    # Test latest property
    assert isinstance(ua.latest, str)
    assert "Chrome" in ua.latest

    # Test random property (alias for chrome)
    assert isinstance(ua.random, str)
    assert "Chrome" in ua.random


def test_get_headers():
    """Test the get_headers method."""
    headers = ua.get_headers()
    assert "User-Agent" in headers
    assert "sec-ch-ua" in headers
    assert "sec-ch-ua-platform" in headers
    assert "sec-ch-ua-mobile" in headers


def test_platform_filtering():
    """Test filtering by platform."""
    mac_headers = ua.get_headers(platform="mac")
    assert "macOS" in mac_headers["sec-ch-ua-platform"]

    win_headers = ua.get_headers(platform="win")
    assert "Windows" in win_headers["sec-ch-ua-platform"]


def test_version_filtering():
    """Test filtering by Chrome version."""
    v137_headers = ua.get_headers(chrome_version="137")
    assert "137" in v137_headers["sec-ch-ua"]

    v136_headers = ua.get_headers(chrome_version="136")
    assert "136" in v136_headers["sec-ch-ua"]


def test_platform_version_filtering():
    """Test filtering by both platform and version."""
    headers = ua.get_headers(platform="mac", chrome_version="137")
    assert "macOS" in headers["sec-ch-ua-platform"]
    assert "137" in headers["sec-ch-ua"]


def test_invalid_platform():
    """Test that invalid platform raises ValueError."""
    with pytest.raises(ValueError):
        ua.get_headers(platform="linux")


def test_invalid_version():
    """Test that invalid Chrome version raises ValueError."""
    with pytest.raises(ValueError):
        ua.get_headers(chrome_version="999")


def test_compatibility_function():
    """Test that the compatibility function works."""
    headers = get_chrome_headers(platform="win")
    assert "Windows" in headers["sec-ch-ua-platform"]


def test_memoization():
    """Test that memoization works."""
    # Get a result
    result1 = ua.get_headers(platform="mac", chrome_version="136")

    # Get the same result again - should be cached
    result2 = ua.get_headers(platform="mac", chrome_version="136")

    # They should be identical since random.choice would be memoized
    assert result1 == result2

    # Create a completely new instance with a modified set of agents
    custom_agents = [
        # Create a unique agent that only this instance will have
        ("mac", "Mac OS X Custom", "136", "Mozilla/5.0 (Macintosh; Custom Mac) Test/136")
    ]

    new_ua = ChromeUA()
    new_ua.update(agents=custom_agents)

    # Now the result must be different since we're using different data
    result3 = new_ua.get_headers(platform="mac", chrome_version="136")
    assert result1 != result3, "New instance with custom agents should produce different results"
