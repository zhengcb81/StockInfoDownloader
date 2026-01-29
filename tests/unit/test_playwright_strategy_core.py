#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Playwright策略核心功能测试
只测试核心功能，避免复杂的mock问题
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.browser_strategy import BrowserAutomationStrategy
from src.utils.browser_utils import is_test_environment
from src.web.playwright_strategy import PlaywrightStrategy


class TestPlaywrightStrategyCore:
    """Playwright策略核心功能测试"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, "downloads")
        os.makedirs(self.download_dir, exist_ok=True)

    def teardown_method(self):
        """测试清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ==================== 初始化测试 ====================

    def test_initialization_default(self):
        """测试默认初始化"""
        strategy = PlaywrightStrategy()

        assert strategy.headless is True
        assert strategy.download_dir is None
        assert strategy.config == {}
        assert strategy.browser is None
        assert strategy.page is None
        assert strategy.download_count == 0
        assert isinstance(strategy, BrowserAutomationStrategy)

    def test_initialization_with_parameters(self):
        """测试带参数初始化"""
        config = {
            "window_size": {"width": 1280, "height": 720},
            "timeout": 60,  # 60秒
            "max_downloads_per_session": 5,
            "user_agents": ["Test-Agent/1.0"],
        }

        strategy = PlaywrightStrategy(
            headless=False, download_dir=self.download_dir, config=config
        )

        assert strategy.headless is False
        assert strategy.download_dir == self.download_dir
        assert strategy.config == config
        assert strategy.window_size == {"width": 1280, "height": 720}
        assert strategy.timeout == 60000  # 60秒 = 60000毫秒
        assert strategy.max_downloads_per_session == 5
        assert strategy._user_agents == ["Test-Agent/1.0"]

    # ==================== 页面操作测试 ====================

    def test_navigate_no_page(self):
        """测试无page时导航失败"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.navigate("https://example.com")
        assert result is False

    def test_navigate_exception(self):
        """测试导航时发生异常"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.goto.side_effect = Exception("Navigation failed")

        result = strategy.navigate("https://example.com")
        assert result is False

    # ==================== 元素查找测试 ====================

    def test_find_elements_no_page(self):
        """测试无page时查找元素"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        elements = strategy.find_elements(".test")
        assert elements == []

    def test_find_element_not_found(self):
        """测试查找单个元素未找到"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.query_selector.return_value = None

        element = strategy.find_element(".nonexistent")
        assert element is None

    # ==================== 元素操作测试 ====================

    def test_click_element_success(self):
        """测试点击元素成功"""
        strategy = PlaywrightStrategy()
        mock_element = MagicMock()

        result = strategy.click(mock_element)
        assert result is True
        mock_element.click.assert_called_once()

    def test_click_element_none(self):
        """测试点击空元素"""
        strategy = PlaywrightStrategy()
        result = strategy.click(None)
        assert result is False

    def test_get_text_success(self):
        """测试获取元素文本成功"""
        strategy = PlaywrightStrategy()
        mock_element = MagicMock()
        mock_element.evaluate.return_value = "Sample Text"

        text = strategy.get_text(mock_element)
        assert text == "Sample Text"

    def test_get_text_no_element(self):
        """测试获取空元素文本"""
        strategy = PlaywrightStrategy()
        text = strategy.get_text(None)
        assert text == ""

    # ==================== 页面信息获取测试 ====================

    def test_get_page_source_no_page(self):
        """测试无page时获取源代码"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        source = strategy.get_page_source()
        assert source == ""

    def test_get_current_url_no_page(self):
        """测试无page时获取URL"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        url = strategy.get_current_url()
        assert url == ""

    def test_get_page_title_no_page(self):
        """测试无page时获取标题"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        title = strategy.get_page_title()
        assert title == ""

    # ==================== 浏览器管理测试 ====================

    def test_close_no_resources(self):
        """测试关闭无资源的浏览器"""
        strategy = PlaywrightStrategy()
        strategy.page = None
        strategy.context = None
        strategy.browser = None
        strategy.playwright = None

        # 不应该抛出异常
        strategy.close()
        assert strategy.page is None
        assert strategy.download_count == 0

    def test_is_healthy_no_page(self):
        """测试无page时健康检查"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.is_healthy()
        assert result is False

    def test_is_healthy_page_exception(self):
        """测试页面异常时健康检查"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        # 使用PropertyMock来正确模拟属性异常
        type(strategy.page).url = PropertyMock(side_effect=Exception("Page crashed"))

        result = strategy.is_healthy()
        assert result is False

    # ==================== 翻页功能测试 ====================

    def test_go_to_next_page_no_page(self):
        """测试无page时跳转下一页"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.go_to_next_page()
        assert result is False

    def test_has_next_page_no_page(self):
        """测试无page时检查下一页"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.has_next_page()
        assert result is False

    # ==================== 截图测试 ====================

    def test_take_screenshot_no_page(self):
        """测试无page时截取截图"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.take_screenshot()
        assert result is None

    # ==================== 下载功能测试 ====================

    def test_download_file_no_page(self):
        """测试无page时下载文件"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.download_file("https://example.com/file.pdf", "/tmp/test.pdf")
        assert result is False

    # ==================== 环境检测测试 ====================

    def test_is_test_environment(self):
        """测试环境检测函数"""
        # 保存原始环境
        original_argv = sys.argv
        original_env = os.environ.copy()

        try:
            # 测试正常环境
            sys.argv = ["normal_script.py"]
            os.environ.pop("TEST_ENV", None)
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            assert is_test_environment() is False

            # 测试TEST_ENV环境变量
            os.environ["TEST_ENV"] = "true"
            assert is_test_environment() is True

        finally:
            # 恢复原始环境
            sys.argv = original_argv
            os.environ.clear()
            os.environ.update(original_env)

    # ==================== 错误处理测试 ====================

    def test_methods_without_driver_return_defaults(self):
        """测试没有driver时方法返回默认值"""
        strategy = PlaywrightStrategy()

        # 所有方法应该返回安全的默认值
        assert strategy.navigate("https://example.com") is False
        assert strategy.find_elements(".test") == []
        assert strategy.find_element(".test") is None
        assert strategy.execute_script("test") is None
        assert strategy.get_page_source() == ""
        assert strategy.get_current_url() == ""
        assert strategy.get_page_title() == ""
        assert strategy.wait_for_element(".test") is False
        assert strategy.take_screenshot() is None
        assert strategy.download_file("url", "/tmp/file.pdf") is False
        assert strategy.go_to_next_page() is False
        assert strategy.has_next_page() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
