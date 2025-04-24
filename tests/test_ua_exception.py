"""
Correctly implemented exception tests for the MacWinUA library.
"""

from unittest.mock import patch

import pytest

from macwinua import ChromeUA, ua
from macwinua.ua import DEFAULT_CHROME_VERSION


def test_inconsistent_update():
    """Test that updating only agents without matching sec_ua raises error."""
    test_ua = ChromeUA()

    # Create new agents with a version not in the default sec_ua
    new_agents = [("mac", "Mac OS X", "200", "Mozilla/5.0 (Mac) Chrome/200.0.0.0")]

    # Update should fail due to cross-consistency validation
    with pytest.raises(ValueError, match="sec_ua is missing entries for Chrome versions"):
        test_ua.update(agents=new_agents)


def test_agents_not_list_type_error():
    """Test TypeError when agents is not a list."""
    test_ua = ChromeUA()
    with pytest.raises(TypeError, match="agents must be a list or None"):
        test_ua.update(agents="not a list")


def test_sec_ua_not_dict_type_error():
    """Test TypeError when sec_ua is not a dictionary."""
    test_ua = ChromeUA()
    with pytest.raises(TypeError, match="sec_ua must be a dictionary"):
        test_ua.update(sec_ua="not a dict")


def test_agent_elements_not_string_type_error():
    """Test TypeError when agent tuple elements are not strings."""
    test_ua = ChromeUA()
    with pytest.raises(TypeError, match="All elements in agent tuple at index 0 must be strings"):
        test_ua.update(agents=[("mac", 123, "137", "UA String")])


def test_invalid_platform_value_error():
    """Test ValueError with invalid platform value."""
    with pytest.raises(ValueError, match="Platform must be 'mac' or 'win'"):
        ua.get_headers(platform="linux")


def test_invalid_chrome_version_value_error():
    """Test ValueError with invalid chrome version."""
    with pytest.raises(ValueError, match="Chrome version must be one of"):
        ua.get_headers(chrome_version="999")


def test_no_matching_user_agent_value_error():
    """Test ValueError when no matching user-agent is found."""
    test_ua = ChromeUA()
    test_ua.update(agents=[], sec_ua={DEFAULT_CHROME_VERSION: "test"})
    with pytest.raises(ValueError, match="No matching user-agent found"):
        test_ua.get_headers()


def test_empty_sec_ua_value_error():
    """Test ValueError when sec_ua is empty."""
    test_ua = ChromeUA()
    with pytest.raises(ValueError, match="sec_ua dictionary cannot be empty"):
        test_ua.update(sec_ua={})


def test_sec_ua_missing_entries_value_error():
    """Test ValueError when sec_ua is missing entries for Chrome versions."""
    test_ua = ChromeUA()
    with pytest.raises(ValueError, match="sec_ua is missing entries for Chrome versions"):
        test_ua.update(agents=[("mac", "Mac OS X", "200", "Mozilla/5.0 Test")])


def test_invalid_agent_tuple_length_value_error():
    """Test ValueError when agent tuple has wrong length."""
    test_ua = ChromeUA()
    with pytest.raises(ValueError, match="Agent at index 0 must be a 4-element tuple"):
        test_ua.update(agents=[("mac", "OS X", "137")])  # Missing UA string


def test_invalid_agent_platform_value_error():
    """Test ValueError when agent has invalid platform."""
    test_ua = ChromeUA()
    with pytest.raises(ValueError, match="Platform at index 0 must be 'mac' or 'win'"):
        test_ua.update(agents=[("linux", "OS X", "137", "UA String")])


def test_missing_default_chrome_version_key_error():
    """Test KeyError when default Chrome version is missing in sec_ua."""
    test_ua = ChromeUA()
    with pytest.raises(KeyError, match=f"Default Chrome version '{DEFAULT_CHROME_VERSION}' must exist"):
        test_ua.update(sec_ua={"999": "Some value"})


def test_direct_platform_type_error():
    """Test direct platform type ValueError."""

    # Custom object with problematic string representation
    class BadObject:
        def __str__(self):
            raise AttributeError("Bad string conversion")

    with pytest.raises(ValueError):
        ua.get_headers(platform=BadObject())


def test_direct_chrome_version_type_error():
    """Test direct chrome_version type ValueError."""

    # Custom object with problematic string representation
    class BadObject:
        def __str__(self):
            raise AttributeError("Bad string conversion")

    with pytest.raises(ValueError):
        ua.get_headers(chrome_version=BadObject())


def test_direct_os_version_type_error():
    """Test direct os_version type ValueError."""

    # Custom object with problematic string representation
    class BadObject:
        def __str__(self):
            raise AttributeError("Bad string conversion")

    with pytest.raises(ValueError):
        ua.get_headers(os_version=BadObject())


def test_generate_headers_exception():
    """Test ValueError when generating headers fails."""
    # Patch random.choice to raise an exception
    with patch("random.choice", side_effect=Exception("Test error")):
        with pytest.raises(ValueError, match="Failed to generate headers"):
            ua.get_headers()


def test_extra_headers_type_error():
    """Test exception handling with string as extra_headers."""
    # This should raise a ValueError due to how dict.update handles strings
    with pytest.raises(ValueError, match="Failed to generate headers"):
        ua.get_headers(extra_headers="not-a-dict")


def test_update_revert_on_validation_failure():
    """Test that original values are preserved when validation fails during update."""
    test_ua = ChromeUA()

    # Get original agents and sec_ua
    original_agents_len = len(test_ua._agents)
    original_sec_ua_len = len(test_ua._sec_ua)

    # Try updating with invalid agents (should fail)
    with pytest.raises(TypeError):
        test_ua.update(agents=123)  # Not a list

    # Original values should be preserved
    assert len(test_ua._agents) == original_agents_len
    assert len(test_ua._sec_ua) == original_sec_ua_len

    # Now try with valid agents but invalid sec_ua
    valid_agents = [("mac", "Mac OS X", "137", "Mozilla/5.0 Valid Agent")]

    with pytest.raises(TypeError):
        test_ua.update(agents=valid_agents, sec_ua="invalid")

    # Original values should still be preserved
    assert len(test_ua._agents) == original_agents_len
    assert len(test_ua._sec_ua) == original_sec_ua_len


def test_update_partial_failure():
    """Test recovery when update succeeds for agents but fails for sec_ua."""
    test_ua = ChromeUA()

    # Store original values lengths
    original_agents_len = len(test_ua._agents)
    original_sec_ua_len = len(test_ua._sec_ua)

    # Create valid agents and invalid sec_ua
    valid_agents = [("mac", "Mac Test", "137", "Mozilla/5.0 Mac Test")]
    invalid_sec_ua = {}  # Empty dict is invalid

    # Update should fail on sec_ua validation
    with pytest.raises(ValueError):
        test_ua.update(agents=valid_agents, sec_ua=invalid_sec_ua)

    # Both original values should be preserved
    assert len(test_ua._agents) == original_agents_len
    assert len(test_ua._sec_ua) == original_sec_ua_len
