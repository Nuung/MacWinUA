"""
Tests for the enhanced MacWinUA library.
"""

import threading
import time

import pytest

from macwinua import ChromeUA, get_chrome_headers, ua
from macwinua.ua import DEFAULT_CHROME_VERSION, DEFAULT_HEADERS, memoize


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

    # Check that default headers are included
    for key in DEFAULT_HEADERS:
        assert key in headers


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


def test_os_version_filtering():
    """Test filtering by OS version."""
    # Test with macOS version
    mac_os_headers = ua.get_headers(os_version="Mac OS X 14_0")
    assert "Macintosh; Intel Mac OS X 14_0" in mac_os_headers["User-Agent"]

    # Test with Windows version
    win_os_headers = ua.get_headers(os_version="Windows NT 10.0; Win64; x64")
    assert "Windows NT 10.0; Win64; x64" in win_os_headers["User-Agent"]


def test_platform_version_filtering():
    """Test filtering by both platform and version."""
    headers = ua.get_headers(platform="mac", chrome_version="137")
    assert "macOS" in headers["sec-ch-ua-platform"]
    assert "137" in headers["sec-ch-ua"]


def test_multiple_filtering():
    """Test filtering by platform, Chrome version, and OS version together."""
    headers = ua.get_headers(platform="mac", chrome_version="137", os_version="Mac OS X 14_0")
    assert "macOS" in headers["sec-ch-ua-platform"]
    assert "137" in headers["sec-ch-ua"]
    assert "Macintosh; Intel Mac OS X 14_0" in headers["User-Agent"]


def test_extra_headers():
    """Test adding extra headers to the response."""
    # Define custom headers
    custom_headers = {
        "X-Custom-Header": "CustomValue",
        "Authorization": "Bearer token123",
    }

    # Get headers with custom additions
    headers = ua.get_headers(extra_headers=custom_headers)

    # Check that both default and custom headers are present
    assert "User-Agent" in headers
    assert "sec-ch-ua" in headers
    assert "X-Custom-Header" in headers
    assert headers["X-Custom-Header"] == "CustomValue"
    assert headers["Authorization"] == "Bearer token123"

    # Test overriding default headers
    override_headers = {
        "sec-ch-ua-mobile": "?1",  # Override the default "?0"
    }

    headers = ua.get_headers(extra_headers=override_headers)
    assert headers["sec-ch-ua-mobile"] == "?1"


def test_invalid_platform():
    """Test that invalid platform raises ValueError."""
    with pytest.raises(ValueError):
        ua.get_headers(platform="linux")


def test_invalid_version():
    """Test that invalid Chrome version raises ValueError."""
    with pytest.raises(ValueError):
        ua.get_headers(chrome_version="999")


def test_invalid_os_version():
    """Test that invalid OS version returns no results."""
    with pytest.raises(ValueError, match="No matching user-agent found for OS version 'Invalid OS'"):
        ua.get_headers(os_version="Invalid OS")


def test_compatibility_function():
    """Test that the compatibility function works."""
    headers = get_chrome_headers(platform="win")
    assert "Windows" in headers["sec-ch-ua-platform"]

    # Test with new parameters
    headers = get_chrome_headers(platform="mac", os_version="Mac OS X 14_0", extra_headers={"X-Test": "Value"})
    assert "macOS" in headers["sec-ch-ua-platform"]
    assert "Mac OS X 14_0" in headers["User-Agent"]
    assert headers["X-Test"] == "Value"


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
        (
            "mac",
            "Mac OS X Custom",
            "136",
            "Mozilla/5.0 (Macintosh; Custom Mac) Test/136",
        )
    ]

    new_ua = ChromeUA()
    new_ua.update(
        agents=custom_agents,
        sec_ua={
            "136": '"Test Chrome";v="136"',
            DEFAULT_CHROME_VERSION: '"Default Chrome";v="135"',
        },
    )

    # Now the result must be different since we're using different data
    result3 = new_ua.get_headers(platform="mac", chrome_version="136")
    assert result1 != result3, "New instance with custom agents should produce different results"


def test_update_method():
    """Test the update method of ChromeUA."""
    # Create a new instance
    custom_ua = ChromeUA()

    # Create custom agents and sec_ua values
    custom_agents = [("mac", "Mac OS X Test", "100", "Mozilla/5.0 (Test OS) Chrome/100.0.0.0")]
    custom_sec_ua = {
        "100": '"Test Chrome";v="100", "Test";v="100"',
        DEFAULT_CHROME_VERSION: f'"Google Chrome";v="{DEFAULT_CHROME_VERSION}", "Chromium";v="{DEFAULT_CHROME_VERSION}", "Not.A/Brand";v="99"',  # noqa: E501
    }

    # Update the instance
    custom_ua.update(agents=custom_agents, sec_ua=custom_sec_ua)

    # Test that the update was applied
    assert custom_ua.chrome == "Mozilla/5.0 (Test OS) Chrome/100.0.0.0"

    # Test for cross-consistency validation - should succeed
    assert custom_ua.get_headers()["User-Agent"] == "Mozilla/5.0 (Test OS) Chrome/100.0.0.0"

    # Test with invalid platform value in agents
    invalid_agents = [("invalid", "Test OS", "100", "Mozilla/5.0 (Invalid) Chrome/100.0.0.0")]
    with pytest.raises(ValueError, match="Platform at index 0 must be 'mac' or 'win'"):
        custom_ua.update(agents=invalid_agents)

    # Original values should be preserved after failed update
    assert custom_ua.chrome == "Mozilla/5.0 (Test OS) Chrome/100.0.0.0"


def test_cross_consistency_validation():
    """Test the validation of consistency between agents and sec_ua."""
    test_ua = ChromeUA()

    # Create agents with version that doesn't exist in sec_ua
    agents = [("mac", "Mac OS X", "999", "Mozilla/5.0 (Mac) Chrome/999.0.0.0")]

    sec_ua = {
        # Missing entry for version "999"
        DEFAULT_CHROME_VERSION: f'"Google Chrome";v="{DEFAULT_CHROME_VERSION}"'
    }

    # Update should fail due to missing sec_ua entry
    with pytest.raises(ValueError, match="sec_ua is missing entries for Chrome versions"):
        test_ua.update(agents=agents, sec_ua=sec_ua)

    # Now add the missing entry and try again
    sec_ua["999"] = '"Chrome";v="999"'
    test_ua.update(agents=agents, sec_ua=sec_ua)

    # Should succeed now
    assert test_ua.chrome == "Mozilla/5.0 (Mac) Chrome/999.0.0.0"


def test_update_clear_cache():
    """Test that update clears the memoization cache."""
    # Create a new instance
    test_ua = ChromeUA()

    # Get a result that will be cached
    result1 = test_ua.get_headers(platform="mac", chrome_version="136")

    # Create custom agents
    custom_agents = [
        (
            "mac",
            "Mac OS X Test",
            "136",
            "Mozilla/5.0 (Macintosh; Test) Chrome/136.0.0.0",
        )
    ]

    custom_sec_ua = {
        "136": '"Test Chrome";v="136"',
        DEFAULT_CHROME_VERSION: f'"Google Chrome";v="{DEFAULT_CHROME_VERSION}"',
    }

    # Update the instance, which should clear cache
    test_ua.update(agents=custom_agents, sec_ua=custom_sec_ua)

    # Get the result again - should use the new data, not cached value
    result2 = test_ua.get_headers(platform="mac", chrome_version="136")

    # Results should be different after cache clear
    assert result1 != result2
    assert "Test" in result2["User-Agent"]


def test_no_matching_user_agent():
    """Test ValueError when no matching user-agent is found."""
    # Create a new instance
    test_ua = ChromeUA()

    # Update with empty agents list
    test_ua.update(agents=[], sec_ua={DEFAULT_CHROME_VERSION: "test"})

    # Should raise ValueError with empty agent list
    with pytest.raises(ValueError, match="No matching user-agent found."):
        test_ua.get_headers()


def test_empty_candidates():
    """Test when filtering produces no candidates."""
    # Create a new instance with only Windows agents
    win_only_ua = ChromeUA()
    win_only_ua.update(
        agents=[("win", "Windows NT 10.0", "137", "Mozilla/5.0 (Windows) Chrome/137.0.0.0")],
        sec_ua={
            "137": '"Chrome";v="137"',
            DEFAULT_CHROME_VERSION: f'"Chrome";v="{DEFAULT_CHROME_VERSION}"',
        },
    )

    # Try to get macOS agents - should fail
    with pytest.raises(ValueError, match="No matching user-agent found for platform 'mac'"):
        win_only_ua.get_headers(platform="mac")


def test_memoize_decorator():
    """Test the memoize decorator directly."""

    # Define a test function with the decorator
    @memoize
    def test_func(arg):
        # Return a new list each time to verify caching
        return [arg]

    # First call should create a new list
    result1 = test_func(1)

    # Second call should return the same list instance
    result2 = test_func(1)

    # Verify it's the same instance (not just equal values)
    assert result1 is result2

    # Clear cache and verify we get a new instance
    test_func.clear_cache()
    result3 = test_func(1)

    # Should be equal but not the same instance
    assert result1 == result3
    assert result1 is not result3


def test_all_available_versions():
    """Test all available Chrome versions."""
    for version in ["135", "136", "137"]:
        headers = ua.get_headers(chrome_version=version)
        assert version in headers["sec-ch-ua"]


def test_empty_properties_with_no_agents():
    """Test behavior of properties when there are no agents."""
    # Create a new instance with empty agents
    empty_ua = ChromeUA()
    empty_ua.update(agents=[], sec_ua={DEFAULT_CHROME_VERSION: "test"})

    # Testing each property when there are no agents should raise IndexError
    with pytest.raises(IndexError):
        _ = empty_ua.chrome

    with pytest.raises(IndexError):
        _ = empty_ua.mac

    with pytest.raises(IndexError):
        _ = empty_ua.windows

    with pytest.raises(IndexError):
        _ = empty_ua.latest

    with pytest.raises(IndexError):
        _ = empty_ua.random


def test_fallback_sec_ua():
    """Test fallback to default Chrome sec-ch-ua when version not found."""
    # Create a custom UA with a new version but no corresponding sec-ch-ua
    custom_ua = ChromeUA()
    custom_agents = [("win", "Windows NT 10.0", "999", "Mozilla/5.0 (Windows) Chrome/999.0.0.0")]
    custom_sec_ua = {
        "999": '"Chrome";v="999"',
        DEFAULT_CHROME_VERSION: f'"Google Chrome";v="{DEFAULT_CHROME_VERSION}", "Chromium";v="{DEFAULT_CHROME_VERSION}", "Not.A/Brand";v="99"',  # noqa: E501
    }
    custom_ua.update(agents=custom_agents, sec_ua=custom_sec_ua)

    # We should get DEFAULT_CHROME_VERSION's sec-ch-ua as a fallback
    result = custom_ua.get_headers()
    assert "999" in result["sec-ch-ua"]


def test_thread_safety():
    """Test thread safety of the ChromeUA instance."""
    # Create a shared ChromeUA instance
    shared_ua = ChromeUA()

    # Store results from different threads
    results = []
    errors = []

    def worker():
        try:
            # Get headers multiple times
            for _ in range(10):
                headers = shared_ua.get_headers()
                results.append(headers["User-Agent"])
                time.sleep(0.001)  # Small sleep to increase chance of thread switching
        except Exception as e:
            errors.append(str(e))

    # Create and start multiple threads
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that no errors occurred
    assert not errors, f"Errors occurred in threads: {errors}"

    # Check that we got results from all threads
    assert len(results) == 50, f"Expected 50 results, got {len(results)}"


def test_invalid_agent_structure():
    """Test validation of agent structure."""
    invalid_ua = ChromeUA()

    # Test with non-list agents
    with pytest.raises(TypeError, match="agents must be a list"):
        invalid_ua.update(agents="not a list")

    # Test with invalid tuple length
    with pytest.raises(ValueError, match="must be a 4-element tuple"):
        invalid_ua.update(agents=[("win", "Windows")])

    # Test with non-string elements
    with pytest.raises(TypeError, match="All elements in agent tuple"):
        invalid_ua.update(agents=[("win", 123, "137", "UA String")])


def test_invalid_sec_ua_structure():
    """Test validation of sec_ua structure."""
    invalid_ua = ChromeUA()

    # Test with non-dict sec_ua
    with pytest.raises(TypeError, match="sec_ua must be a dictionary"):
        invalid_ua.update(sec_ua="not a dict")

    # Test with empty dict
    with pytest.raises(ValueError, match="sec_ua dictionary cannot be empty"):
        invalid_ua.update(sec_ua={})

    # Test without default version
    with pytest.raises(KeyError, match=f"Default Chrome version '{DEFAULT_CHROME_VERSION}' must exist"):
        invalid_ua.update(sec_ua={"999": "Some value"})


def test_safe_cast_parameters():
    """Test safe casting of parameters."""
    # Test numeric platform value (should be converted to string)
    headers = ua.get_headers(platform="mac", chrome_version=137)  # Numeric version
    assert "macOS" in headers["sec-ch-ua-platform"]
    assert "137" in headers["sec-ch-ua"]


def test_available_versions():
    """Test the available_versions property."""
    test_ua = ChromeUA()

    # Get available versions
    versions = test_ua.available_versions

    # Should be a sorted list of strings
    assert isinstance(versions, list)
    assert all(isinstance(v, str) for v in versions)
    assert versions == sorted(versions)

    # Should match our expected Chrome versions
    assert "135" in versions
    assert "136" in versions
    assert "137" in versions

    # Update with custom agents and check again
    test_ua.update(
        agents=[("mac", "OS X", "100", "UA 100"), ("win", "Windows", "101", "UA 101")],
        sec_ua={"100": "v100", "101": "v101", DEFAULT_CHROME_VERSION: "default"},
    )

    versions = test_ua.available_versions
    assert versions == ["100", "101"]


def test_available_platforms():
    """Test the available_platforms property."""
    test_ua = ChromeUA()

    # Get available platforms
    platforms = test_ua.available_platforms

    # Should be a sorted list of strings
    assert isinstance(platforms, list)
    assert all(isinstance(p, str) for p in platforms)

    # Should match our expected platforms
    assert "mac" in platforms
    assert "win" in platforms
    assert len(platforms) == 2  # Should only have 'mac' and 'win'

    # Update with only mac agents and check again
    test_ua.update(
        agents=[
            ("mac", "OS X 10", "136", "UA Mac 1"),
            ("mac", "OS X 11", "137", "UA Mac 2"),
        ],
        sec_ua={"136": "v136", "137": "v137", DEFAULT_CHROME_VERSION: "default"},
    )

    platforms = test_ua.available_platforms
    assert platforms == ["mac"]
    assert "win" not in platforms


def test_available_os_versions():
    """Test the available_os_versions property."""
    test_ua = ChromeUA()

    # Get available OS versions
    os_versions = test_ua.available_os_versions

    # Should be a dictionary with platform keys
    assert isinstance(os_versions, dict)
    assert "mac" in os_versions
    assert "win" in os_versions

    # Mac OS versions
    assert "Mac OS X 13_5_2" in os_versions["mac"]
    assert "Mac OS X 14_0" in os_versions["mac"]

    # Windows OS versions
    assert "Windows NT 10.0; Win64; x64" in os_versions["win"]

    # Update with custom agents and check again
    test_ua.update(
        agents=[
            ("mac", "Custom Mac OS", "136", "UA Mac"),
            ("win", "Custom Windows", "137", "UA Win"),
        ],
        sec_ua={"136": "v136", "137": "v137", DEFAULT_CHROME_VERSION: "default"},
    )

    os_versions = test_ua.available_os_versions
    assert os_versions["mac"] == ["Custom Mac OS"]
    assert os_versions["win"] == ["Custom Windows"]
