#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""浏览器工具函数测试"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.constants import BrowserConfig, TimeoutConfig
from src.utils.browser_utils import (
    get_common_chrome_args,
    get_default_user_agents,
    is_test_environment,
    validate_and_normalize_timeout,
)


class TestBrowserUtils:
    """浏览器工具函数测试"""

    def test_is_test_environment(self):
        """测试环境检测"""
        # 保存原始环境
        original_argv = sys.argv
        original_env = os.environ.copy()

        try:
            # 测试TEST_ENV环境变量
            os.environ["TEST_ENV"] = "true"
            assert is_test_environment() is True

            # 清理
            del os.environ["TEST_ENV"]

            # 测试包含pytest的脚本名
            sys.argv = ["pytest", "test.py"]
            assert is_test_environment() is True

            # 测试正常环境
            sys.argv = ["normal_script.py"]
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            assert is_test_environment() is False

        finally:
            # 恢复原始环境
            sys.argv = original_argv
            os.environ.clear()
            os.environ.update(original_env)

    def test_get_default_user_agents(self):
        """测试获取默认用户代理"""
        agents = get_default_user_agents()
        assert isinstance(agents, list)
        assert len(agents) >= 2
        assert all("Mozilla" in agent for agent in agents)
        assert all("Chrome" in agent for agent in agents)

    def test_validate_and_normalize_timeout_seconds(self):
        """测试timeout验证 - 秒转毫秒"""
        assert validate_and_normalize_timeout(30) == 30000
        assert validate_and_normalize_timeout(1) == 1000
        assert validate_and_normalize_timeout(180) == 180000

    def test_validate_and_normalize_timeout_milliseconds(self):
        """测试timeout验证 - 毫秒保持不变"""
        assert validate_and_normalize_timeout(30000) == 30000
        assert validate_and_normalize_timeout(1000) == 1000
        assert validate_and_normalize_timeout(180000) == 180000

    def test_validate_and_normalize_timeout_boundary(self):
        """测试timeout边界值"""
        # 1000是边界值，应该保持不变
        assert validate_and_normalize_timeout(1000) == 1000

    def test_validate_and_normalize_timeout_invalid(self):
        """测试timeout无效值"""
        with pytest.raises(ValueError):
            validate_and_normalize_timeout(0)

        with pytest.raises(ValueError):
            validate_and_normalize_timeout(-1)

    def test_get_common_chrome_args(self):
        """测试获取Chrome启动参数"""
        args = get_common_chrome_args()
        assert isinstance(args, list)
        assert "--no-sandbox" in args
        assert "--disable-dev-shm-usage" in args
        assert "--disable-gpu" in args
        assert "--disable-blink-features=AutomationControlled" in args
        assert len(args) > 10

    def test_get_common_chrome_args_no_duplicates(self):
        """测试Chrome参数无重复"""
        args = get_common_chrome_args()
        assert len(args) == len(set(args))


class TestConstants:
    """常量配置测试"""

    def test_timeout_config(self):
        """测试超时配置"""
        assert TimeoutConfig.PAGE_LOAD == 30
        assert TimeoutConfig.DOWNLOAD == 300
        assert TimeoutConfig.ELEMENT_WAIT == 10
        assert TimeoutConfig.NAVIGATION == 10
        assert TimeoutConfig.BUTTON_CLICK == 5

    def test_browser_config(self):
        """测试浏览器配置"""
        assert BrowserConfig.DEFAULT_WINDOW_SIZE == "1920,1080"
        assert BrowserConfig.DEFAULT_WINDOW_SIZE_DICT == {"width": 1920, "height": 1080}
        assert BrowserConfig.MAX_DOWNLOADS_PER_SESSION == 10
        assert BrowserConfig.IMPLICIT_WAIT == 3

    def test_file_size_threshold(self):
        """测试文件大小阈值"""
        from src.core.constants import FileSizeThreshold

        assert FileSizeThreshold.MIN_VALID_PDF == 10 * 1024
        assert FileSizeThreshold.DOWNLOAD_CHECK_INTERVAL == 0.5

    def test_retry_config(self):
        """测试重试配置"""
        from src.core.constants import RetryConfig

        assert RetryConfig.MAX_RETRIES == 3
        assert RetryConfig.BASE_DELAY == 1.0
        assert RetryConfig.BACKOFF_FACTOR == 2.0

    def test_selector_config(self):
        """测试选择器配置"""
        from src.core.constants import SelectorConfig

        assert SelectorConfig.DOWNLOAD_BUTTON == "//button[contains(., '公告下载')]"
        assert len(SelectorConfig.NEXT_PAGE_SELECTORS) > 0
        assert len(SelectorConfig.DOWNLOAD_BUTTON_ALTERNATIVES) > 0
        assert isinstance(SelectorConfig.NEXT_PAGE_SELECTORS, list)
        assert isinstance(SelectorConfig.DOWNLOAD_BUTTON_ALTERNATIVES, list)

    def test_user_agents_constant(self):
        """测试用户代理常量"""
        from src.core.constants import USER_AGENTS

        assert isinstance(USER_AGENTS, list)
        assert len(USER_AGENTS) >= 5
        assert all("Mozilla" in agent for agent in USER_AGENTS)

    def test_chrome_launch_args_constant(self):
        """测试Chrome启动参数常量"""
        from src.core.constants import CHROME_LAUNCH_ARGS

        assert isinstance(CHROME_LAUNCH_ARGS, list)
        assert "--no-sandbox" in CHROME_LAUNCH_ARGS
        assert len(CHROME_LAUNCH_ARGS) > 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
