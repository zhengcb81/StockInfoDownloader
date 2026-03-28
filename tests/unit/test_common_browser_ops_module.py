"""
Common Browser Ops Module Tests
Tests for common browser operations module
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.web.common_browser_ops import (
    BROWSER_BASE_ARGS,
    CommonBrowserConfig,
    DEFAULT_USER_AGENTS,
)


class TestModuleConstants:
    """Test module-level constants"""

    def test_browser_base_args(self):
        """Test BROWSER_BASE_ARGS is defined and contains expected args"""
        assert isinstance(BROWSER_BASE_ARGS, list)
        assert len(BROWSER_BASE_ARGS) > 0
        assert "--no-sandbox" in BROWSER_BASE_ARGS
        assert "--disable-dev-shm-usage" in BROWSER_BASE_ARGS

    def test_default_user_agents(self):
        """Test DEFAULT_USER_AGENTS is defined"""
        assert isinstance(DEFAULT_USER_AGENTS, list)
        assert len(DEFAULT_USER_AGENTS) > 0
        assert all("Mozilla" in agent for agent in DEFAULT_USER_AGENTS)


class TestCommonBrowserConfig:
    """CommonBrowserConfig class tests"""

    def test_get_base_args(self):
        """Test get_base_args returns copy of base args"""
        args = CommonBrowserConfig.get_base_args()
        assert isinstance(args, list)
        assert args == BROWSER_BASE_ARGS

        # Verify it's a copy, not the same list
        assert args is not BROWSER_BASE_ARGS

    def test_get_base_args_isolation(self):
        """Test modifying returned list doesn't affect original"""
        args1 = CommonBrowserConfig.get_base_args()
        args1.append("--new-arg")

        args2 = CommonBrowserConfig.get_base_args()
        assert "--new-arg" not in args2

    def test_get_default_user_agents(self):
        """Test get_default_user_agents returns copy of user agents"""
        agents = CommonBrowserConfig.get_default_user_agents()
        assert isinstance(agents, list)
        assert agents == DEFAULT_USER_AGENTS

        # Verify it's a copy
        assert agents is not DEFAULT_USER_AGENTS

    def test_get_default_user_agents_isolation(self):
        """Test modifying returned list doesn't affect original"""
        agents1 = CommonBrowserConfig.get_default_user_agents()
        agents1.append("New Agent")

        agents2 = CommonBrowserConfig.get_default_user_agents()
        assert "New Agent" not in agents2

    def test_get_random_user_agent_default(self):
        """Test get_random_user_agent with default agents"""
        agent = CommonBrowserConfig.get_random_user_agent()
        assert isinstance(agent, str)
        assert agent in DEFAULT_USER_AGENTS

    def test_get_random_user_agent_custom(self):
        """Test get_random_user_agent with custom agents"""
        custom_agents = ["Custom/1.0", "Custom/2.0"]
        agent = CommonBrowserConfig.get_random_user_agent(custom_agents)
        assert agent in custom_agents

    def test_get_random_user_agent_empty_list(self):
        """Test get_random_user_agent with empty custom list uses default"""
        # Empty list is falsy, so it falls back to DEFAULT_USER_AGENTS
        agent = CommonBrowserConfig.get_random_user_agent([])
        assert isinstance(agent, str)
        assert agent in DEFAULT_USER_AGENTS

    def test_normalize_window_size_none(self):
        """Test normalize_window_size with None"""
        result = CommonBrowserConfig.normalize_window_size(None)
        assert result == {"width": 1920, "height": 1080}

    def test_normalize_window_size_string(self):
        """Test normalize_window_size with string"""
        result = CommonBrowserConfig.normalize_window_size("1920,1080")
        assert result == {"width": 1920, "height": 1080}

    def test_normalize_window_size_string_with_spaces(self):
        """Test normalize_window_size with string containing spaces"""
        result = CommonBrowserConfig.normalize_window_size("1280, 720")
        assert result == {"width": 1280, "height": 720}

    def test_normalize_window_size_string_invalid(self):
        """Test normalize_window_size with invalid string"""
        result = CommonBrowserConfig.normalize_window_size("invalid")
        assert result == {"width": 1920, "height": 1080}

    def test_normalize_window_size_dict(self):
        """Test normalize_window_size with dict"""
        result = CommonBrowserConfig.normalize_window_size({"width": 1280, "height": 720})
        assert result == {"width": 1280, "height": 720}

    def test_normalize_window_size_dict_partial(self):
        """Test normalize_window_size with partial dict"""
        result = CommonBrowserConfig.normalize_window_size({"width": 1280})
        assert result == {"width": 1280, "height": 1080}

    def test_normalize_window_size_list(self):
        """Test normalize_window_size with list"""
        result = CommonBrowserConfig.normalize_window_size([1280, 720])
        assert result == {"width": 1280, "height": 720}

    def test_normalize_window_size_tuple(self):
        """Test normalize_window_size with tuple"""
        result = CommonBrowserConfig.normalize_window_size((1280, 720))
        assert result == {"width": 1280, "height": 720}

    def test_normalize_window_size_list_three_elements(self):
        """Test normalize_window_size with list of 3 elements"""
        result = CommonBrowserConfig.normalize_window_size([1000, 800, 200])
        assert result == {"width": 1000, "height": 800}

    def test_normalize_window_size_invalid_type(self):
        """Test normalize_window_size with invalid type"""
        result = CommonBrowserConfig.normalize_window_size(12345)
        assert result == {"width": 1920, "height": 1080}

    def test_normalize_timeout_none(self):
        """Test normalize_timeout with None"""
        result = CommonBrowserConfig.normalize_timeout(None)
        assert result == 180

    def test_normalize_timeout_seconds(self):
        """Test normalize_timeout with seconds"""
        result = CommonBrowserConfig.normalize_timeout(30)
        assert result == 30

    def test_normalize_timeout_milliseconds(self):
        """Test normalize_timeout with milliseconds"""
        result = CommonBrowserConfig.normalize_timeout(30000)
        assert result == 30

    def test_normalize_timeout_milliseconds_boundary(self):
        """Test normalize_timeout at millisecond boundary"""
        # 1000 is not > 1000, so it's treated as seconds
        result = CommonBrowserConfig.normalize_timeout(1000)
        assert result == 1000

        # 1001 > 1000, so it's treated as milliseconds
        result = CommonBrowserConfig.normalize_timeout(1001)
        assert result == 1

    def test_normalize_timeout_string_converts_to_int(self):
        """Test normalize_timeout with string value"""
        result = CommonBrowserConfig.normalize_timeout("60")
        assert result == 60

    def test_build_selenium_preferences_no_download_dir(self):
        """Test build_selenium_preferences without download dir"""
        result = CommonBrowserConfig.build_selenium_preferences(None)
        assert result == {}

    def test_build_selenium_preferences_with_download_dir(self):
        """Test build_selenium_preferences with download dir"""
        with patch("os.makedirs"):
            result = CommonBrowserConfig.build_selenium_preferences("/tmp/downloads")
            assert "download.default_directory" in result
            assert "download.prompt_for_download" in result

    def test_build_selenium_preferences_creates_directory(self):
        """Test build_selenium_preferences creates directory"""
        with patch("os.makedirs") as mock_makedirs, \
             patch("os.path.abspath", return_value="/abs/path/downloads"):
            CommonBrowserConfig.build_selenium_preferences("downloads")
            mock_makedirs.assert_called_once_with("/abs/path/downloads", exist_ok=True)

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_build_selenium_preferences_windows_path(self):
        """Test build_selenium_preferences on Windows"""
        with patch("os.makedirs"), \
             patch("os.path.abspath", return_value="C:\\Downloads"), \
             patch("platform.system", return_value="Windows"):
            result = CommonBrowserConfig.build_selenium_preferences("downloads")
            # Windows path separators should be normalized
            assert "download.default_directory" in result
