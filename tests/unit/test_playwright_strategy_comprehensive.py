#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Playwright策略全面测试
测试PlaywrightStrategy的所有公共方法和核心私有方法
"""

import pytest
import tempfile
import os
import time
import random
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, List, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.playwright_strategy import PlaywrightStrategy, is_test_environment
from src.web.browser_strategy import BrowserAutomationStrategy
from src.core.exceptions import (
    WebDriverInitError, WebDriverTimeoutError, WebDriverCrashError,
    ErrorCode, ErrorSeverity, RecoveryStrategy
)
from src.core.config import ConfigManager


class TestPlaywrightStrategyComprehensive:
    """PlaywrightStrategy全面功能测试"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, 'downloads')
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
        assert strategy.context is None
        assert strategy.download_count == 0
        assert isinstance(strategy, BrowserAutomationStrategy)

    def test_initialization_with_parameters(self):
        """测试带参数初始化"""
        config = {
            'window_size': {'width': 1280, 'height': 720},
            'timeout': 60000,
            'max_downloads_per_session': 5,
            'user_agents': ['Test-Agent/1.0']
        }

        strategy = PlaywrightStrategy(
            headless=False,
            download_dir=self.download_dir,
            config=config
        )

        assert strategy.headless is False
        assert strategy.download_dir == self.download_dir
        assert strategy.config == config
        assert strategy.window_size == {'width': 1280, 'height': 720}
        assert strategy.timeout == 60000
        assert strategy.max_downloads_per_session == 5
        assert strategy._user_agents == ['Test-Agent/1.0']

    def test_initialization_with_config_manager(self):
        """测试配置管理器加载"""
        # 创建临时配置文件
        config_file = os.path.join(self.temp_dir, 'test_config.json')
        test_config = {
            "browser": {
                "window_size": {"width": 1366, "height": 768},
                "timeout": 45000
            }
        }
        import json
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)

        # ConfigManager会从文件中加载配置
        config_manager = ConfigManager(config_file)
        config = config_manager.config

        strategy = PlaywrightStrategy(config=config)
        # 注意：PlaywrightStrategy从config参数中获取配置，不是直接从ConfigManager
        # 此测试主要验证config参数传递

    # ==================== 浏览器创建测试 ====================

    @patch('src.web.playwright_strategy.sync_playwright')
    def test_create_driver_success(self, mock_sync_playwright):
        """测试成功创建浏览器驱动"""
        # 设置mock
        mock_playwright_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright_instance = MagicMock()
        mock_sync_playwright_instance.start.return_value = mock_playwright_instance
        mock_sync_playwright.return_value = mock_sync_playwright_instance

        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        strategy = PlaywrightStrategy(headless=True)

        # 执行创建
        result = strategy.create_driver()

        # 验证
        assert result == mock_browser
        assert strategy.browser == mock_browser
        assert strategy.context == mock_context
        assert strategy.page == mock_page

        # 验证调用
        mock_sync_playwright_instance.start.assert_called_once()
        mock_playwright_instance.chromium.launch.assert_called_once()
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_page.goto.assert_called_once_with('about:blank', wait_until='domcontentloaded')

    @patch('src.web.playwright_strategy.sync_playwright')
    def test_create_driver_import_error(self, mock_sync_playwright):
        """测试导入Playwright失败"""
        mock_sync_playwright.side_effect = ImportError("Playwright not installed")

        strategy = PlaywrightStrategy()

        # 应该抛出WebDriverInitError
        with pytest.raises(WebDriverInitError) as exc_info:
            strategy.create_driver()

        assert "Playwright未安装" in str(exc_info.value)
        assert exc_info.value.error_code == ErrorCode.WEBDRIVER_INIT_ERROR

    @patch('src.web.playwright_strategy.sync_playwright')
    def test_create_driver_timeout_error(self, mock_sync_playwright):
        """测试创建浏览器超时"""
        mock_sync_playwright_instance = MagicMock()
        mock_sync_playwright.return_value = mock_sync_playwright_instance

        # 模拟超时错误
        mock_playwright_instance = MagicMock()
        mock_sync_playwright_instance.start.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.side_effect = Exception("timeout: browser launch timeout")

        strategy = PlaywrightStrategy()

        # 应该抛出WebDriverTimeoutError（create_driver内部将timeout异常转换为WebDriverTimeoutError）
        with pytest.raises(WebDriverTimeoutError) as exc_info:
            strategy.create_driver()

        assert "timeout" in str(exc_info.value).lower()
        assert exc_info.value.error_code == ErrorCode.WEBDRIVER_TIMEOUT_ERROR

    @patch('src.web.playwright_strategy.sync_playwright')
    def test_create_driver_close_existing(self, mock_sync_playwright):
        """测试创建前关闭现有浏览器"""
        # 设置mock
        mock_playwright_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright_instance = MagicMock()
        mock_sync_playwright_instance.start.return_value = mock_playwright_instance
        mock_sync_playwright.return_value = mock_sync_playwright_instance

        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        strategy = PlaywrightStrategy()
        strategy.browser = MagicMock()
        strategy.context = MagicMock()
        strategy.page = MagicMock()

        # 验证close会被调用
        with patch.object(strategy, 'close') as mock_close:
            strategy.create_driver()
            mock_close.assert_called_once()

    # ==================== 页面操作测试 ====================

    def test_navigate_success(self):
        """测试成功导航"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()

        result = strategy.navigate("https://example.com")

        assert result is True
        strategy.page.goto.assert_called_once_with("https://example.com", wait_until='domcontentloaded', timeout=180000)

    def test_navigate_no_page(self):
        """测试无页面时导航失败"""
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

    def test_find_elements_css(self):
        """测试CSS选择器查找元素"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]
        strategy.page.query_selector_all.return_value = mock_elements

        elements = strategy.find_elements(".test-class", "css")

        assert elements == mock_elements
        strategy.page.query_selector_all.assert_called_once_with(".test-class")

    def test_find_elements_xpath(self):
        """测试XPath选择器查找元素"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]
        strategy.page.query_selector_all.return_value = mock_elements

        elements = strategy.find_elements("//div[@class='test']", "xpath")

        assert elements == mock_elements
        strategy.page.query_selector_all.assert_called_once_with("xpath=//div[@class='test']")

    def test_find_elements_no_page(self):
        """测试无页面时查找元素"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        elements = strategy.find_elements(".test")
        assert elements == []

    def test_find_element_success(self):
        """测试查找单个元素成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        mock_element = MagicMock()
        strategy.page.query_selector.return_value = mock_element

        element = strategy.find_element(".test")

        assert element == mock_element
        strategy.page.query_selector.assert_called_once_with(".test")

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

    def test_click_element_exception(self):
        """测试点击元素异常"""
        strategy = PlaywrightStrategy()
        mock_element = MagicMock()
        mock_element.click.side_effect = Exception("Click failed")

        result = strategy.click(mock_element)
        assert result is False

    def test_get_text_success(self):
        """测试获取元素文本成功"""
        strategy = PlaywrightStrategy()
        mock_element = MagicMock()
        mock_element.evaluate.return_value = "Sample Text"

        text = strategy.get_text(mock_element)
        assert text == "Sample Text"
        mock_element.evaluate.assert_called_once_with('element => element.textContent?.trim() || ""')

    def test_get_text_no_element(self):
        """测试获取空元素文本"""
        strategy = PlaywrightStrategy()
        text = strategy.get_text(None)
        assert text == ""

    def test_get_attribute_success(self):
        """测试获取元素属性成功"""
        strategy = PlaywrightStrategy()
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "https://example.com"

        href = strategy.get_attribute(mock_element, "href")
        assert href == "https://example.com"
        mock_element.get_attribute.assert_called_once_with("href")

    def test_get_attribute_no_element(self):
        """测试获取空元素属性"""
        strategy = PlaywrightStrategy()
        result = strategy.get_attribute(None, "href")
        assert result is None

    # ==================== JavaScript执行测试 ====================

    def test_execute_script_success(self):
        """测试执行JavaScript脚本成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.evaluate.return_value = "result"

        result = strategy.execute_script("return document.title;")
        assert result == "result"
        strategy.page.evaluate.assert_called_once_with("return document.title;")

    def test_execute_script_no_page(self):
        """测试无页面时执行脚本"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.execute_script("return document.title;")
        assert result is None

    # ==================== 等待元素测试 ====================

    def test_wait_for_element_visible(self):
        """测试等待元素可见"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()

        result = strategy.wait_for_element(".test", timeout=5, condition="visible")
        assert result is True
        strategy.page.wait_for_selector.assert_called_once_with(".test", state='visible', timeout=5000)

    def test_wait_for_element_hidden(self):
        """测试等待元素隐藏"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()

        result = strategy.wait_for_element(".test", timeout=3, condition="hidden")
        assert result is True
        strategy.page.wait_for_selector.assert_called_once_with(".test", state='hidden', timeout=3000)

    def test_wait_for_element_default(self):
        """测试等待元素默认条件"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()

        result = strategy.wait_for_element(".test", timeout=10)
        assert result is True
        strategy.page.wait_for_selector.assert_called_once_with(".test", state='visible', timeout=10000)

    def test_wait_for_element_no_page(self):
        """测试无页面时等待元素"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.wait_for_element(".test")
        assert result is False

    def test_wait_for_element_timeout(self):
        """测试等待元素超时"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.wait_for_selector.side_effect = Exception("Timeout")

        result = strategy.wait_for_element(".test")
        assert result is False

    # ==================== 页面信息获取测试 ====================

    def test_get_page_source_success(self):
        """测试获取页面源代码成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.content.return_value = "<html>...</html>"

        source = strategy.get_page_source()
        assert source == "<html>...</html>"
        strategy.page.content.assert_called_once()

    def test_get_page_source_no_page(self):
        """测试无页面时获取源代码"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        source = strategy.get_page_source()
        assert source == ""

    def test_get_current_url_success(self):
        """测试获取当前URL成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.url = "https://example.com"

        url = strategy.get_current_url()
        assert url == "https://example.com"

    def test_get_current_url_no_page(self):
        """测试无页面时获取URL"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        url = strategy.get_current_url()
        assert url == ""

    def test_get_page_title_success(self):
        """测试获取页面标题成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.title.return_value = "Example Page"

        title = strategy.get_page_title()
        assert title == "Example Page"
        strategy.page.title.assert_called_once()

    def test_get_page_title_no_page(self):
        """测试无页面时获取标题"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        title = strategy.get_page_title()
        assert title == ""

    # ==================== 浏览器管理测试 ====================

    def test_close_with_all_resources(self):
        """测试关闭所有浏览器资源"""
        strategy = PlaywrightStrategy()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_playwright = MagicMock()

        strategy.browser = mock_browser
        strategy.context = mock_context
        strategy.page = mock_page
        strategy.playwright = mock_playwright
        strategy.user_data_dir = None

        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            strategy.close()

        # 验证资源被关闭 (使用存储的mock引用)
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

        # 验证资源被置为None
        assert strategy.browser is None
        assert strategy.context is None
        assert strategy.page is None
        assert strategy.download_count == 0

    def test_close_partial_resources(self):
        """测试关闭部分资源"""
        strategy = PlaywrightStrategy()
        mock_browser = MagicMock()
        strategy.browser = mock_browser
        strategy.context = None
        strategy.page = None
        strategy.playwright = None
        strategy.user_data_dir = None

        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            strategy.close()

        # 只有browser应该被关闭 (使用存储的mock引用)
        mock_browser.close.assert_called_once()
        assert strategy.browser is None

    def test_close_exception_handling(self):
        """测试关闭时异常处理"""
        strategy = PlaywrightStrategy()
        strategy.browser = MagicMock()
        strategy.browser.close.side_effect = Exception("Close error")
        strategy.context = MagicMock()
        strategy.context.close.side_effect = Exception("Context close error")
        strategy.page = None
        strategy.playwright = None
        strategy.user_data_dir = None

        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            # 应该不会抛出异常
            strategy.close()

        # 资源应该被置为None
        assert strategy.browser is None
        assert strategy.context is None

    def test_is_healthy_with_page(self):
        """测试有页面时健康检查"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.url = "https://example.com"

        result = strategy.is_healthy()
        assert result is True

    def test_is_healthy_no_page(self):
        """测试无页面时健康检查"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.is_healthy()
        assert result is False

    def test_is_healthy_page_exception(self):
        """测试页面异常时健康检查"""
        from unittest.mock import PropertyMock

        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        # 使用PropertyMock来正确模拟属性异常
        type(strategy.page).url = PropertyMock(side_effect=Exception("Page crashed"))

        result = strategy.is_healthy()
        # 根据实现，异常会被捕获并返回False
        assert result is False

    @patch('src.web.playwright_strategy.sync_playwright')
    def test_restart_success(self, mock_sync_playwright):
        """测试重启成功"""
        # 设置mock
        mock_playwright_instance = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright_instance = MagicMock()
        mock_sync_playwright_instance.start.return_value = mock_playwright_instance
        mock_sync_playwright.return_value = mock_sync_playwright_instance

        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        strategy = PlaywrightStrategy()

        # 验证close会被调用
        with patch.object(strategy, 'close') as mock_close:
            result = strategy.restart()
            assert result is True
            mock_close.assert_called_once()
            # create_driver会被调用，因为我们在mock中
            # 实际测试中，由于mock了sync_playwright，create_driver会成功

    @patch('src.web.playwright_strategy.sync_playwright')
    def test_restart_failure(self, mock_sync_playwright):
        """测试重启失败"""
        mock_sync_playwright.side_effect = ImportError("Playwright not installed")

        strategy = PlaywrightStrategy()

        # 重启应该重试但最终失败
        result = strategy.restart()
        assert result is False

    # ==================== 截图测试 ====================

    def test_take_screenshot_success(self):
        """测试截取屏幕截图成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        screenshot_data = b"screenshot bytes"
        strategy.page.screenshot.return_value = screenshot_data

        result = strategy.take_screenshot()
        assert result == screenshot_data
        strategy.page.screenshot.assert_called_once()

    def test_take_screenshot_with_save_path(self):
        """测试截取截图并保存"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        screenshot_data = b"screenshot bytes"
        strategy.page.screenshot.return_value = screenshot_data

        save_path = os.path.join(self.temp_dir, "screenshot.png")

        # Mock open函数
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = strategy.take_screenshot(save_path=save_path)

            assert result == screenshot_data
            strategy.page.screenshot.assert_called_once()
            mock_open.assert_called_once_with(save_path, 'wb')
            mock_file.write.assert_called_once_with(screenshot_data)

    def test_take_screenshot_no_page(self):
        """测试无页面时截取截图"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.take_screenshot()
        assert result is None

    # ==================== 下载功能测试 ====================

    def test_download_file_success(self):
        """测试下载文件成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        mock_download = MagicMock()

        # Mock导航
        with patch.object(strategy, 'navigate', return_value=True):
            # Mock查找元素
            mock_button = MagicMock()
            with patch.object(strategy, 'find_element', return_value=mock_button):
                # Mock点击
                with patch.object(strategy, 'click', return_value=True):
                    # Mock等待下载事件
                    strategy.page.expect_download.return_value.__enter__.return_value.value = mock_download

                    save_path = os.path.join(self.download_dir, "test.pdf")
                    result = strategy.download_file("https://example.com/file.pdf", save_path)

                    assert result is True
                    mock_download.save_as.assert_called_once_with(save_path)

    def test_download_file_no_page(self):
        """测试无页面时下载文件"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.download_file("https://example.com/file.pdf", "/tmp/test.pdf")
        assert result is False

    def test_download_file_navigate_failure(self):
        """测试导航失败时下载"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()

        with patch.object(strategy, 'navigate', return_value=False):
            result = strategy.download_file("https://example.com/file.pdf", "/tmp/test.pdf")
            assert result is False

    def test_download_file_find_element_failure(self):
        """测试找不到下载按钮时下载"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()

        with patch.object(strategy, 'navigate', return_value=True):
            with patch.object(strategy, 'find_element', return_value=None):
                result = strategy.download_file("https://example.com/file.pdf", "/tmp/test.pdf")
                assert result is False

    # ==================== 翻页功能测试 ====================

    def test_go_to_next_page_success(self):
        """测试跳转到下一页成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        mock_button = MagicMock()
        mock_button.is_enabled.return_value = True

        strategy.page.query_selector.side_effect = [None, mock_button, None, None]

        result = strategy.go_to_next_page()
        assert result is True
        mock_button.click.assert_called_once()
        strategy.page.wait_for_load_state.assert_called_once_with('domcontentloaded', timeout=10000)

    def test_go_to_next_page_no_page(self):
        """测试无页面时跳转下一页"""
        strategy = PlaywrightStrategy()
        strategy.page = None

        result = strategy.go_to_next_page()
        assert result is False

    def test_go_to_next_page_no_button(self):
        """测试找不到下一页按钮"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.query_selector.return_value = None

        result = strategy.go_to_next_page()
        assert result is False

    def test_go_to_page_success(self):
        """测试跳转到指定页码成功"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        mock_input = MagicMock()
        mock_button = MagicMock()
        mock_input.is_enabled.return_value = True
        mock_button.is_enabled.return_value = True

        strategy.page.query_selector.side_effect = [mock_input, mock_button]

        result = strategy.go_to_page(3)
        assert result is True
        mock_input.fill.assert_called_once_with("")
        mock_input.type.assert_called_once_with("3")
        mock_button.click.assert_called_once()

    def test_has_next_page_true(self):
        """测试有下一页"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        mock_button = MagicMock()
        mock_button.is_enabled.return_value = True

        strategy.page.query_selector.return_value = mock_button

        result = strategy.has_next_page()
        assert result is True

    def test_has_next_page_false(self):
        """测试没有下一页"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()
        strategy.page.query_selector.return_value = None

        result = strategy.has_next_page()
        assert result is False

    # ==================== 私有方法测试 ====================

    def test_build_launch_options(self):
        """测试构建启动选项"""
        strategy = PlaywrightStrategy(
            headless=False,
            config={
                'window_size': {'width': 1280, 'height': 720},
                'user_agents': ['Test-Agent/1.0']
            }
        )

        options = strategy._build_launch_options()

        assert options['headless'] is False
        assert '--window-size=1280,720' in options['args']
        assert any('--user-agent=Test-Agent/1.0' in arg for arg in options['args'])
        assert '--no-sandbox' in options['args']

    def test_build_context_options_with_download_dir(self):
        """测试构建带下载目录的上下文选项"""
        strategy = PlaywrightStrategy(download_dir=self.download_dir)

        options = strategy._build_context_options()

        assert options['viewport'] == {'width': 1920, 'height': 1080}
        assert options['accept_downloads'] is True
        assert 'user_agent' in options

    def test_build_context_options_no_download_dir(self):
        """测试无下载目录的上下文选项"""
        strategy = PlaywrightStrategy(download_dir=None)

        options = strategy._build_context_options()

        assert 'accept_downloads' not in options

    # ==================== 环境检测测试 ====================

    def test_is_test_environment(self):
        """测试环境检测函数"""
        # 保存原始环境
        original_argv = sys.argv
        original_env = os.environ.copy()

        try:
            # 测试正常环境
            sys.argv = ['normal_script.py']
            os.environ.pop('TEST_ENV', None)
            os.environ.pop('PYTEST_CURRENT_TEST', None)
            assert is_test_environment() is False

            # 测试TEST_ENV环境变量
            os.environ['TEST_ENV'] = 'true'
            assert is_test_environment() is True

            # 清理
            os.environ.pop('TEST_ENV', None)

            # 测试包含test的脚本名
            sys.argv = ['test_script.py']
            assert is_test_environment() is True

            # 测试包含pytest的脚本名
            sys.argv = ['pytest_runner.py']
            assert is_test_environment() is True

            # 测试PYTEST_CURRENT_TEST环境变量
            sys.argv = ['normal_script.py']
            os.environ['PYTEST_CURRENT_TEST'] = 'test_function'
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
        assert strategy.go_to_page(1) is False
        assert strategy.has_next_page() is False

    # ==================== 集成测试 ====================

    @patch('src.web.playwright_strategy.sync_playwright')
    @patch('tempfile.mkdtemp')
    def test_full_workflow(self, mock_mkdtemp, mock_sync_playwright):
        """测试完整工作流程"""
        # 设置mock
        mock_playwright_instance = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright_instance = MagicMock()
        mock_sync_playwright_instance.start.return_value = mock_playwright_instance
        mock_sync_playwright.return_value = mock_sync_playwright_instance

        # Mock persistent context (since download_dir is provided)
        mock_playwright_instance.chromium.launch_persistent_context.return_value = mock_context
        mock_context.pages = [mock_page]
        mock_mkdtemp.return_value = "/tmp/playwright_user_test"

        # 创建策略
        strategy = PlaywrightStrategy(headless=True, download_dir=self.download_dir)

        # 1. 创建driver (使用持久化上下文)
        browser_or_context = strategy.create_driver()
        assert browser_or_context == mock_context
        assert strategy.is_healthy() is True

        # 2. 导航
        result = strategy.navigate("https://example.com")
        assert result is True
        mock_page.goto.assert_called_with("https://example.com", wait_until='domcontentloaded', timeout=180000)

        # 3. 查找元素
        mock_elements = [MagicMock(), MagicMock()]
        mock_page.query_selector_all.return_value = mock_elements
        elements = strategy.find_elements(".test")
        assert elements == mock_elements

        # 4. 获取页面信息
        mock_page.url = "https://example.com"
        assert strategy.get_current_url() == "https://example.com"

        # 5. 关闭
        with patch('time.sleep'):
            strategy.close()
        assert strategy.browser is None
        assert strategy.page is None
        assert strategy.is_healthy() is False

    # ==================== 性能测试 ====================

    def test_performance_initialization(self):
        """测试初始化性能"""
        import time
        start_time = time.time()
        strategy = PlaywrightStrategy()
        end_time = time.time()

        initialization_time = end_time - start_time
        # 初始化应该在合理时间内完成
        assert initialization_time < 2.0, f"初始化时间过长: {initialization_time:.2f}秒"

    def test_performance_method_calls(self):
        """测试方法调用性能"""
        strategy = PlaywrightStrategy()
        strategy.page = MagicMock()

        import time
        iterations = 100

        # 测试简单方法调用性能
        start_time = time.time()
        for _ in range(iterations):
            strategy.get_current_url()
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        # 平均调用时间应该很小
        assert avg_time < 0.001, f"方法调用性能差: {avg_time*1000:.2f}毫秒/次"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])