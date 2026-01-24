#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Selenium策略全面测试
测试SeleniumStrategy的所有公共方法和核心私有方法
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

from src.web.selenium_strategy import SeleniumStrategy, is_test_environment
from src.web.browser_strategy import BrowserAutomationStrategy
from src.core.exceptions import (
    WebDriverInitError, WebDriverTimeoutError, WebDriverCrashError,
    ErrorCode, ErrorSeverity, RecoveryStrategy
)
from src.core.config import ConfigManager


class TestSeleniumStrategyComprehensive:
    """SeleniumStrategy全面功能测试"""

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
        strategy = SeleniumStrategy()

        assert strategy.headless is True
        assert strategy.download_dir is None
        assert strategy.config == {}
        assert strategy.driver is None
        assert strategy.download_count == 0
        assert isinstance(strategy, BrowserAutomationStrategy)

    def test_initialization_with_parameters(self):
        """测试带参数初始化"""
        config = {
            'window_size': '1280,720',
            'page_load_timeout': 30000,
            'max_downloads_per_session': 5,
            'user_agents': ['Test-Agent/1.0']
        }

        strategy = SeleniumStrategy(
            headless=False,
            download_dir=self.download_dir,
            config=config
        )

        assert strategy.headless is False
        assert strategy.download_dir == self.download_dir
        assert strategy.config == config
        assert strategy.window_size == '1280,720'
        assert strategy.page_load_timeout == 30000
        assert strategy.max_downloads_per_session == 5
        assert strategy._user_agents == ['Test-Agent/1.0']

    def test_initialization_with_config_manager(self):
        """测试配置管理器加载"""
        # 创建临时配置文件
        config_file = os.path.join(self.temp_dir, 'test_config.json')
        test_config = {
            "browser": {
                "window_size": "1366,768",
                "timeout": 15000
            }
        }
        import json
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)

        # ConfigManager会从文件中加载配置
        config_manager = ConfigManager(config_file)
        config = config_manager.config

        strategy = SeleniumStrategy(config=config)
        # 注意：SeleniumStrategy从config参数中获取配置，不是直接从ConfigManager
        # 此测试主要验证config参数传递

    # ==================== 浏览器创建测试 ====================

    @patch('src.web.selenium_strategy.webdriver.Chrome')
    def test_create_driver_success(self, mock_chrome):
        """测试成功创建浏览器驱动"""
        # 设置mock
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        strategy = SeleniumStrategy(headless=True)

        # 执行创建
        result = strategy.create_driver()

        # 验证
        assert result == mock_driver
        assert strategy.driver == mock_driver

        # 验证调用
        mock_chrome.assert_called_once()
        # 默认配置：timeout=30 (TimeoutConfig.PAGE_LOAD), implicit_wait=3
        mock_driver.set_page_load_timeout.assert_called_once_with(30)
        mock_driver.implicitly_wait.assert_called_once_with(3)
        mock_driver.get.assert_called_once_with("about:blank")

    @patch('src.web.selenium_strategy.webdriver.Chrome')
    def test_create_driver_close_existing(self, mock_chrome):
        """测试创建前关闭现有浏览器"""
        # 设置mock
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        # 验证close会被调用
        with patch.object(strategy, 'close') as mock_close:
            strategy.create_driver()
            mock_close.assert_called_once()

    @patch('src.web.selenium_strategy.webdriver.Chrome')
    def test_create_driver_chrome_creation_failure(self, mock_chrome):
        """测试ChromeDriver创建失败"""
        # 模拟首次创建失败，第二次成功
        mock_driver = MagicMock()
        mock_chrome.side_effect = [Exception("Chrome error"), mock_driver]

        strategy = SeleniumStrategy()

        # 创建应该成功（有重试机制）
        result = strategy.create_driver()

        assert result == mock_driver
        assert mock_chrome.call_count == 2

    # ==================== 页面操作测试 ====================

    def test_navigate_success(self):
        """测试成功导航"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        result = strategy.navigate("https://example.com")

        assert result is True
        strategy.driver.get.assert_called_once_with("https://example.com")

    def test_navigate_no_driver(self):
        """测试无driver时导航失败"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        result = strategy.navigate("https://example.com")
        assert result is False

    def test_navigate_exception(self):
        """测试导航时发生异常"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        strategy.driver.get.side_effect = Exception("Navigation failed")

        result = strategy.navigate("https://example.com")
        assert result is False

    # ==================== 元素查找测试 ====================

    def test_find_elements_css(self):
        """测试CSS选择器查找元素"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]
        strategy.driver.find_elements.return_value = mock_elements

        elements = strategy.find_elements(".test-class", "css")

        assert elements == mock_elements
        strategy.driver.find_elements.assert_called_once()

    def test_find_elements_xpath(self):
        """测试XPath选择器查找元素"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]
        strategy.driver.find_elements.return_value = mock_elements

        elements = strategy.find_elements("//div[@class='test']", "xpath")

        assert elements == mock_elements
        strategy.driver.find_elements.assert_called_once()

    def test_find_elements_no_driver(self):
        """测试无driver时查找元素"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        elements = strategy.find_elements(".test")
        assert elements == []

    def test_find_element_success(self):
        """测试查找单个元素成功"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        mock_element = MagicMock()
        strategy.driver.find_elements.return_value = [mock_element]

        element = strategy.find_element(".test")

        assert element == mock_element
        strategy.driver.find_elements.assert_called_once()

    def test_find_element_not_found(self):
        """测试查找单个元素未找到"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        strategy.driver.find_elements.return_value = []

        element = strategy.find_element(".nonexistent")
        assert element is None

    # ==================== 元素操作测试 ====================

    def test_click_element_success(self):
        """测试点击元素成功"""
        strategy = SeleniumStrategy()
        mock_element = MagicMock()

        result = strategy.click(mock_element)
        assert result is True
        mock_element.click.assert_called_once()

    def test_click_element_none(self):
        """测试点击空元素"""
        strategy = SeleniumStrategy()
        result = strategy.click(None)
        assert result is False

    def test_click_element_exception(self):
        """测试点击元素异常"""
        strategy = SeleniumStrategy()
        mock_element = MagicMock()
        mock_element.click.side_effect = Exception("Click failed")

        result = strategy.click(mock_element)
        assert result is False

    def test_get_text_success(self):
        """测试获取元素文本成功"""
        strategy = SeleniumStrategy()
        mock_element = MagicMock()
        mock_element.text = "Sample Text"

        text = strategy.get_text(mock_element)
        assert text == "Sample Text"

    def test_get_text_no_element(self):
        """测试获取空元素文本"""
        strategy = SeleniumStrategy()
        text = strategy.get_text(None)
        assert text == ""

    def test_get_attribute_success(self):
        """测试获取元素属性成功"""
        strategy = SeleniumStrategy()
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "https://example.com"

        href = strategy.get_attribute(mock_element, "href")
        assert href == "https://example.com"
        mock_element.get_attribute.assert_called_once_with("href")

    def test_get_attribute_no_element(self):
        """测试获取空元素属性"""
        strategy = SeleniumStrategy()
        result = strategy.get_attribute(None, "href")
        assert result is None

    # ==================== JavaScript执行测试 ====================

    def test_execute_script_success(self):
        """测试执行JavaScript脚本成功"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        strategy.driver.execute_script.return_value = "result"

        result = strategy.execute_script("return document.title;")
        assert result == "result"
        strategy.driver.execute_script.assert_called_once_with("return document.title;")

    def test_execute_script_no_driver(self):
        """测试无driver时执行脚本"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        result = strategy.execute_script("return document.title;")
        assert result is None

    # ==================== 等待元素测试 ====================

    @patch('src.web.selenium_strategy.WebDriverWait')
    @patch('selenium.webdriver.common.by')
    @patch('selenium.webdriver.support.expected_conditions')
    def test_wait_for_element_visible(self, mock_ec, mock_by, mock_webdriver_wait):
        """测试等待元素可见"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        # 模拟By模块
        mock_by.CSS_SELECTOR = 'css selector'
        mock_by.XPATH = 'xpath'

        # 模拟EC模块
        mock_ec.visibility_of_element_located = MagicMock(return_value=MagicMock())

        mock_wait = MagicMock()
        # 模拟wait.until成功（不引发异常）
        mock_wait.until = MagicMock(return_value=MagicMock())
        mock_webdriver_wait.return_value = mock_wait

        result = strategy.wait_for_element(".test", timeout=5, condition="visible")
        print(f"Result: {result}")
        print(f"wait.until called: {mock_wait.until.called}")
        print(f"wait.until call count: {mock_wait.until.call_count}")
        assert result is True
        mock_webdriver_wait.assert_called_once_with(strategy.driver, 5)
        # 验证wait.until被调用（具体条件在内部，我们只关心被调用）
        mock_wait.until.assert_called_once()

    @patch('src.web.selenium_strategy.WebDriverWait')
    def test_wait_for_element_no_driver(self, mock_webdriver_wait):
        """测试无driver时等待元素"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        result = strategy.wait_for_element(".test")
        assert result is False
        mock_webdriver_wait.assert_not_called()

    # ==================== 页面信息获取测试 ====================

    def test_get_page_source_success(self):
        """测试获取页面源代码成功"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        strategy.driver.page_source = "<html>...</html>"

        source = strategy.get_page_source()
        assert source == "<html>...</html>"

    def test_get_page_source_no_driver(self):
        """测试无driver时获取源代码"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        source = strategy.get_page_source()
        assert source == ""

    def test_get_current_url_success(self):
        """测试获取当前URL成功"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        strategy.driver.current_url = "https://example.com"

        url = strategy.get_current_url()
        assert url == "https://example.com"

    def test_get_current_url_no_driver(self):
        """测试无driver时获取URL"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        url = strategy.get_current_url()
        assert url == ""

    def test_get_page_title_success(self):
        """测试获取页面标题成功"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        strategy.driver.title = "Example Page"

        title = strategy.get_page_title()
        assert title == "Example Page"

    def test_get_page_title_no_driver(self):
        """测试无driver时获取标题"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        title = strategy.get_page_title()
        assert title == ""

    # ==================== 浏览器管理测试 ====================

    def test_close_with_driver(self):
        """测试关闭浏览器"""
        strategy = SeleniumStrategy()
        mock_driver = MagicMock()
        strategy.driver = mock_driver

        strategy.close()

        # 验证driver被关闭（使用保存的引用）
        mock_driver.quit.assert_called_once()
        assert strategy.driver is None
        assert strategy.download_count == 0

    def test_close_no_driver(self):
        """测试关闭无driver的浏览器"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        # 不应该抛出异常
        strategy.close()
        assert strategy.driver is None

    def test_is_healthy_with_driver(self):
        """测试有driver时健康检查"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        strategy.driver.current_url = "https://example.com"

        result = strategy.is_healthy()
        assert result is True

    def test_is_healthy_no_driver(self):
        """测试无driver时健康检查"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        result = strategy.is_healthy()
        assert result is False

    def test_is_healthy_driver_exception(self):
        """测试driver异常时健康检查"""
        from unittest.mock import PropertyMock

        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        # 使用PropertyMock模拟current_url属性抛出异常
        type(strategy.driver).current_url = PropertyMock(side_effect=Exception("Driver crashed"))

        result = strategy.is_healthy()
        # 根据实现，异常会被捕获并返回False
        assert result is False

    @patch('src.web.selenium_strategy.webdriver.Chrome')
    def test_restart_success(self, mock_chrome):
        """测试重启成功"""
        # 设置mock
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        strategy = SeleniumStrategy()

        # 验证close会被调用
        with patch.object(strategy, 'close') as mock_close:
            result = strategy.restart()
            assert result is True
            mock_close.assert_called_once()
            # create_driver会被调用，因为我们在mock中
            # 实际测试中，由于mock了webdriver.Chrome，create_driver会成功

    @patch('src.web.selenium_strategy.webdriver.Chrome')
    def test_restart_failure(self, mock_chrome):
        """测试重启失败"""
        mock_chrome.side_effect = Exception("WebDriver creation failed")

        strategy = SeleniumStrategy()

        # 重启应该重试但最终失败
        result = strategy.restart()
        assert result is False

    # ==================== 截图测试 ====================

    def test_take_screenshot_success(self):
        """测试截取屏幕截图成功"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        screenshot_data = b"screenshot bytes"
        strategy.driver.get_screenshot_as_png.return_value = screenshot_data

        result = strategy.take_screenshot()
        assert result == screenshot_data
        strategy.driver.get_screenshot_as_png.assert_called_once()

    def test_take_screenshot_with_save_path(self):
        """测试截取截图并保存"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()
        screenshot_data = b"screenshot bytes"
        strategy.driver.get_screenshot_as_png.return_value = screenshot_data

        save_path = os.path.join(self.temp_dir, "screenshot.png")

        # Mock open函数
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = strategy.take_screenshot(save_path=save_path)

            assert result == screenshot_data
            strategy.driver.get_screenshot_as_png.assert_called_once()
            mock_open.assert_called_once_with(save_path, 'wb')
            mock_file.write.assert_called_once_with(screenshot_data)

    def test_take_screenshot_no_driver(self):
        """测试无driver时截取截图"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        result = strategy.take_screenshot()
        assert result is None

    # ==================== 下载功能测试 ====================

    def test_download_file_success(self):
        """测试下载文件成功"""
        strategy = SeleniumStrategy(download_dir=self.download_dir)
        strategy.driver = MagicMock()

        # Mock导航
        with patch.object(strategy, 'navigate', return_value=True):
            # Mock查找元素
            mock_button = MagicMock()
            with patch.object(strategy, 'find_element', return_value=mock_button):
                # Mock点击
                with patch.object(strategy, 'click', return_value=True):
                    # 设置文件检查逻辑
                    with patch('os.path.exists') as mock_exists, \
                         patch('shutil.move') as mock_move:
                        mock_exists.return_value = True

                        save_path = os.path.join(self.download_dir, "test.pdf")
                        result = strategy.download_file("https://example.com/file.pdf", save_path)

                        # 在mock环境中无法实际完成下载，但应该执行到相关逻辑
                        strategy.navigate.assert_called_once_with("https://example.com/file.pdf")
                        strategy.find_element.assert_called_once()
                        strategy.click.assert_called_once()

    def test_download_file_no_driver(self):
        """测试无driver时下载文件"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        result = strategy.download_file("https://example.com/file.pdf", "/tmp/test.pdf")
        assert result is False

    def test_download_file_navigate_failure(self):
        """测试导航失败时下载"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        with patch.object(strategy, 'navigate', return_value=False):
            result = strategy.download_file("https://example.com/file.pdf", "/tmp/test.pdf")
            assert result is False

    # ==================== 翻页功能测试 ====================

    def test_go_to_next_page_success(self):
        """测试跳转到下一页成功"""
        from selenium.webdriver.common.by import By

        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        mock_button = MagicMock()
        mock_button.is_enabled.return_value = True
        mock_button.is_displayed.return_value = True
        mock_button.click = MagicMock()

        # 直接模拟driver.find_element方法
        strategy.driver.find_element = MagicMock(return_value=mock_button)

        # 模拟execute_script和WebDriverWait
        strategy.driver.execute_script = MagicMock()

        # 模拟time.sleep
        with patch('time.sleep'):
            # 模拟WebDriverWait和EC
            with patch('src.web.selenium_strategy.WebDriverWait') as mock_wait_class, \
                 patch('selenium.webdriver.support.expected_conditions') as mock_ec:

                mock_wait = MagicMock()
                mock_wait_class.return_value = mock_wait
                mock_wait.until = MagicMock(return_value=True)

                # 模拟EC.staleness_of返回一个返回True的函数
                mock_staleness = MagicMock(return_value=True)
                mock_ec.staleness_of = MagicMock(return_value=mock_staleness)

                result = strategy.go_to_next_page()

                # 验证find_element被调用
                print(f"find_element called: {strategy.driver.find_element.called}")
                print(f"find_element call count: {strategy.driver.find_element.call_count}")
                if strategy.driver.find_element.called:
                    print(f"find_element call args: {strategy.driver.find_element.call_args}")

                assert strategy.driver.find_element.called
                # 验证返回True
                assert result is True

    def test_go_to_next_page_no_driver(self):
        """测试无driver时跳转下一页"""
        strategy = SeleniumStrategy()
        strategy.driver = None

        result = strategy.go_to_next_page()
        assert result is False

    def test_go_to_next_page_no_button(self):
        """测试找不到下一页按钮"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        with patch.object(strategy.driver, 'find_element') as mock_find_element:
            mock_find_element.side_effect = Exception("No such element")

            result = strategy.go_to_next_page()
            assert result is False

    def test_has_next_page_true(self):
        """测试有下一页"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        with patch.object(strategy.driver, 'find_element') as mock_find_element:
            mock_button = MagicMock()
            mock_button.is_enabled.return_value = True
            mock_button.is_displayed.return_value = True
            mock_find_element.return_value = mock_button

            result = strategy.has_next_page()
            assert result is True

    def test_has_next_page_false(self):
        """测试没有下一页"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        with patch.object(strategy.driver, 'find_element') as mock_find_element:
            mock_find_element.side_effect = Exception("No such element")

            result = strategy.has_next_page()
            assert result is False

    # ==================== 私有方法测试 ====================

    @patch('src.web.selenium_strategy.Options')
    def test_build_chrome_options(self, mock_options):
        """测试构建Chrome选项"""
        mock_chrome_options = MagicMock()
        mock_options.return_value = mock_chrome_options

        strategy = SeleniumStrategy(
            headless=False,
            download_dir=self.download_dir,
            config={
                'window_size': '1280,720',
                'user_agents': ['Test-Agent/1.0']
            }
        )

        options = strategy._build_chrome_options()

        assert options == mock_chrome_options
        # 验证Chrome选项配置
        mock_chrome_options.add_argument.assert_any_call('--window-size=1280,720')
        mock_chrome_options.add_argument.assert_any_call('--no-sandbox')
        mock_chrome_options.add_argument.assert_any_call(f'--user-agent=Test-Agent/1.0')
        mock_chrome_options.add_experimental_option.assert_any_call("excludeSwitches", ["enable-automation"])

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
        strategy = SeleniumStrategy()

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

    # ==================== 集成测试 ====================

    @patch('src.web.selenium_strategy.webdriver.Chrome')
    def test_full_workflow(self, mock_chrome):
        """测试完整工作流程"""
        # 设置mock
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        # 创建策略
        strategy = SeleniumStrategy(headless=True, download_dir=self.download_dir)

        # 1. 创建driver
        driver = strategy.create_driver()
        assert driver == mock_driver
        assert strategy.is_healthy() is True

        # 2. 导航
        result = strategy.navigate("https://example.com")
        assert result is True
        mock_driver.get.assert_called_with("https://example.com")

        # 3. 查找元素
        mock_elements = [MagicMock(), MagicMock()]
        mock_driver.find_elements.return_value = mock_elements
        elements = strategy.find_elements(".test")
        assert elements == mock_elements

        # 4. 获取页面信息
        mock_driver.current_url = "https://example.com"
        assert strategy.get_current_url() == "https://example.com"

        # 5. 关闭
        strategy.close()
        assert strategy.driver is None
        assert strategy.is_healthy() is False

    # ==================== 性能测试 ====================

    def test_performance_initialization(self):
        """测试初始化性能"""
        import time
        start_time = time.time()
        strategy = SeleniumStrategy()
        end_time = time.time()

        initialization_time = end_time - start_time
        # 初始化应该在合理时间内完成
        assert initialization_time < 2.0, f"初始化时间过长: {initialization_time:.2f}秒"

    def test_performance_method_calls(self):
        """测试方法调用性能"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

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