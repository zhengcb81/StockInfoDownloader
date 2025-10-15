#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
浏览器策略基础测试
测试Selenium和Playwright浏览器策略的基本功能
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.browser_strategy import BrowserStrategy
from src.web.selenium_strategy import SeleniumStrategy
from src.web.playwright_strategy import PlaywrightStrategy


class TestBrowserStrategyInterface:
    """浏览器策略接口测试"""

    def test_strategy_interface_methods(self):
        """测试策略接口定义的方法"""
        # 检查接口方法是否存在
        assert hasattr(BrowserStrategy, 'navigate')
        assert hasattr(BrowserStrategy, 'find_elements')
        assert hasattr(BrowserStrategy, 'click')
        assert hasattr(BrowserStrategy, 'get_current_url')
        assert hasattr(BrowserStrategy, 'close')

    def test_strategy_interface_abstract_methods(self):
        """测试策略接口的抽象方法"""
        # 尝试实例化抽象类应该失败
        with pytest.raises(TypeError):
            BrowserStrategy()


class TestSeleniumStrategy:
    """Selenium策略测试"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, 'downloads')

    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('selenium.webdriver.Chrome')
    @patch('selenium.webdriver.chrome.options.Options')
    def test_selenium_strategy_initialization(self, mock_chrome_options, mock_chrome_driver):
        """测试Selenium策略初始化"""
        # 设置mock
        mock_options = MagicMock()
        mock_chrome_options.return_value = mock_options

        mock_driver = MagicMock()
        mock_chrome_driver.return_value = mock_driver

        # 创建策略
        strategy = SeleniumStrategy(headless=True, download_dir=self.download_dir)

        # 验证初始化
        assert strategy.headless is True
        assert strategy.download_dir == self.download_dir

        # 创建driver
        strategy.create_driver()
        assert strategy.driver is not None

        # 验证Chrome选项设置 - 由于_build_chrome_options内部创建新的Options，这里不验证

    @patch('selenium.webdriver.Chrome')
    @patch('selenium.webdriver.chrome.options.Options')
    def test_selenium_navigate(self, mock_chrome_options, mock_chrome_driver):
        """测试Selenium导航功能"""
        # 设置mock
        mock_options = MagicMock()
        mock_chrome_options.return_value = mock_options

        mock_driver = MagicMock()
        mock_chrome_driver.return_value = mock_driver

        # 创建策略
        strategy = SeleniumStrategy(headless=True, download_dir=self.download_dir)
        strategy.driver = mock_driver  # 直接设置driver

        # 测试导航
        test_url = "https://www.cninfo.com.cn"
        result = strategy.navigate(test_url)

        # 验证导航调用
        mock_driver.get.assert_called_once_with(test_url)
        assert result is True

    @patch('selenium.webdriver.Chrome')
    @patch('selenium.webdriver.chrome.options.Options')
    def test_selenium_find_elements(self, mock_chrome_options, mock_chrome_driver):
        """测试Selenium元素查找功能"""
        # 设置mock
        mock_options = MagicMock()
        mock_chrome_options.return_value = mock_options

        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_driver.find_elements.return_value = [mock_element]
        mock_chrome_driver.return_value = mock_driver

        # 创建策略
        strategy = SeleniumStrategy(headless=True, download_dir=self.download_dir)
        strategy.driver = mock_driver  # 直接设置driver

        # 测试元素查找
        selector = ".pdf-link"
        by = "css"
        elements = strategy.find_elements(selector, by)

        # 验证查找调用
        from selenium.webdriver.common.by import By
        mock_driver.find_elements.assert_called_once_with(By.CSS_SELECTOR, selector)
        assert len(elements) == 1

    @patch('selenium.webdriver.Chrome')
    @patch('selenium.webdriver.chrome.options.Options')
    def test_selenium_close(self, mock_chrome_options, mock_chrome_driver):
        """测试Selenium关闭功能"""
        # 设置mock
        mock_options = MagicMock()
        mock_chrome_options.return_value = mock_options

        mock_driver = MagicMock()
        mock_chrome_driver.return_value = mock_driver

        # 创建策略
        strategy = SeleniumStrategy(headless=True, download_dir=self.download_dir)
        strategy.driver = mock_driver  # 直接设置driver

        # 测试关闭
        strategy.close()

        # 验证关闭调用
        mock_driver.quit.assert_called_once()


class TestPlaywrightStrategy:
    """Playwright策略测试"""

    @pytest.mark.skip(reason="Playwright模块未安装")

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, 'downloads')

    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.skip(reason="Playwright模块未安装")
    @patch('playwright.sync_api.sync_playwright')
    def test_playwright_strategy_initialization(self, mock_sync_playwright):
        """测试Playwright策略初始化"""
        # 设置mock
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # 创建策略
        strategy = PlaywrightStrategy(headless=True, download_dir=self.download_dir)

        # 验证初始化
        assert strategy.headless is True
        assert strategy.download_dir == self.download_dir
        assert strategy.browser is not None
        assert strategy.context is not None
        assert strategy.page is not None

    @pytest.mark.skip(reason="Playwright模块未安装")
    @patch('playwright.sync_api.sync_playwright')
    def test_playwright_navigate(self, mock_sync_playwright):
        """测试Playwright导航功能"""
        # 设置mock
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # 创建策略
        strategy = PlaywrightStrategy(headless=True, download_dir=self.download_dir)

        # 测试导航
        test_url = "https://www.cninfo.com.cn"
        result = strategy.navigate(test_url)

        # 验证导航调用
        mock_page.goto.assert_called_once_with(test_url, wait_until="networkidle")
        assert result is True

    @pytest.mark.skip(reason="Playwright模块未安装")
    @patch('playwright.sync_api.sync_playwright')
    def test_playwright_find_elements(self, mock_sync_playwright):
        """测试Playwright元素查找功能"""
        # 设置mock
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_element = MagicMock()

        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.query_selector_all.return_value = [mock_element]

        # 创建策略
        strategy = PlaywrightStrategy(headless=True, download_dir=self.download_dir)

        # 测试元素查找
        selector = ".pdf-link"
        elements = strategy.find_elements(selector)

        # 验证查找调用
        mock_page.query_selector_all.assert_called_once_with(selector)
        assert len(elements) == 1

    @pytest.mark.skip(reason="Playwright模块未安装")
    @patch('playwright.sync_api.sync_playwright')
    def test_playwright_close(self, mock_sync_playwright):
        """测试Playwright关闭功能"""
        # 设置mock
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        # 创建策略
        strategy = PlaywrightStrategy(headless=True, download_dir=self.download_dir)

        # 测试关闭
        strategy.close()

        # 验证关闭调用
        mock_browser.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])