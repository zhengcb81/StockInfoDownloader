#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BrowserService增强测试模块
测试src.services.browser_service.BrowserService类的全面功能
使用依赖注入和mock技术提高测试隔离性
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.core.config import ConfigManager
from src.services.browser_service import BrowserService

from .dependency_injection import DependencyInjectionTestBase
from .test_utils import EnvironmentManager


class TestBrowserServiceEnhanced(DependencyInjectionTestBase):
    """BrowserService增强测试类"""

    def setup_method(self):
        """测试初始化"""
        super().setup_method()
        self.test_env = EnvironmentManager()
        self.temp_dir = self.test_env.create_temp_dir()

        # 创建mock配置管理器
        self.mock_config_manager = Mock(spec=ConfigManager)
        self._setup_mock_config()

        # 创建BrowserService实例
        self.service = BrowserService(config_manager=self.mock_config_manager)

    def teardown_method(self):
        """测试清理"""
        super().teardown_method()
        self.test_env.cleanup()

    def _setup_mock_config(self):
        """设置mock配置"""
        # 基础配置
        self.mock_config_manager.get.side_effect = lambda key, default=None: {
            "save_dir": self.temp_dir,
            "anti_crawler.min_delay": 2.0,
            "anti_crawler.max_delay": 8.0,
            "anti_crawler.max_downloads": 5,
            "anti_crawler.scroll_range": [200, 600],
            "anti_crawler.behavior_delay": [0.5, 1.5],
            "anti_crawler": {
                "min_delay": 2.0,
                "max_delay": 8.0,
                "max_downloads": 5,
                "scroll_range": [200, 600],
                "behavior_delay": [0.5, 1.5],
            },
        }.get(key, default)

    def test_init(self):
        """测试初始化"""
        # 测试默认初始化
        default_service = BrowserService()
        assert default_service.config_manager is not None
        assert default_service.browser_config is not None
        assert default_service.anti_crawler is not None
        assert default_service.driver is None
        assert default_service.download_count == 0
        assert default_service.logger is not None

        # 测试自定义配置管理器
        custom_service = BrowserService(config_manager=self.mock_config_manager)
        assert custom_service.config_manager == self.mock_config_manager

    @patch("src.services.browser_service.webdriver.Chrome")
    @patch("src.services.browser_service.BrowserConfig")
    def test_setup_driver_success(self, mock_browser_config, mock_chrome):
        """测试成功设置浏览器驱动"""
        # 设置mock
        mock_config_instance = Mock()
        mock_config_instance.is_headless.return_value = False
        mock_config_instance.get_all_timeouts.return_value = {"page_load": 30}
        mock_config_instance.get_window_size.return_value = "1920,1080"
        mock_config_instance.get_random_user_agent.return_value = "test-user-agent"
        mock_config_instance.get_page_load_strategy.return_value = "normal"
        mock_browser_config.return_value = mock_config_instance

        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        # 执行测试
        result = self.service.setup_driver(headless=False)

        # 验证结果
        assert result == mock_driver
        assert self.service.driver == mock_driver
        mock_chrome.assert_called_once()

        # 验证驱动配置
        mock_driver.set_page_load_timeout.assert_called_with(30)
        mock_driver.set_window_size.assert_called_with(1920, 1080)

    @patch("src.services.browser_service.webdriver.Chrome")
    @patch("src.services.browser_service.BrowserConfig")
    def test_setup_driver_failure(self, mock_browser_config, mock_chrome):
        """测试设置浏览器驱动失败"""
        # 设置mock
        mock_config_instance = Mock()
        mock_config_instance.is_headless.return_value = False
        mock_config_instance.get_all_timeouts.return_value = {"page_load": 30}
        mock_config_instance.get_window_size.return_value = "1920,1080"
        mock_config_instance.get_random_user_agent.return_value = "test-user-agent"
        mock_config_instance.get_page_load_strategy.return_value = "normal"
        mock_browser_config.return_value = mock_config_instance

        mock_chrome.side_effect = Exception("Chrome driver failed")

        # 测试异常处理
        with pytest.raises(Exception):
            self.service.setup_driver()

    @patch("src.services.browser_service.webdriver.Chrome")
    def test_setup_driver_headless_mode(self, mock_chrome):
        """测试无头模式设置"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        # 测试无头模式
        self.service.setup_driver(headless=True)

        # 验证Chrome选项包含无头模式参数
        call_args = mock_chrome.call_args
        options = call_args[1]["options"]

        # 检查是否包含无头模式参数
        options_args = [
            arg for arg in options.arguments if arg.startswith("--headless")
        ]
        assert len(options_args) > 0

    def test_get_chrome_options(self):
        """测试获取Chrome选项"""
        # 测试无头模式
        options = self.service._get_chrome_options(headless=True)
        assert options is not None

        # 检查基础参数
        expected_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-infobars",
            "--disable-notifications",
            "--disable-popup-blocking",
        ]

        for arg in expected_args:
            assert arg in options.arguments

        # 检查无头模式参数
        assert "--headless" in options.arguments

    def test_get_download_directory(self):
        """测试获取下载目录"""
        # 测试目录创建
        download_dir = self.service._get_download_directory()

        assert download_dir is not None
        assert os.path.exists(download_dir)
        assert download_dir == os.path.abspath(self.temp_dir)

    @patch("src.services.browser_service.random")
    @patch("src.services.browser_service.time")
    def test_simulate_human_behavior_with_driver(self, mock_time, mock_random):
        """测试有驱动时模拟人类行为"""
        # 设置mock驱动
        self.service.driver = Mock()

        # 设置mock随机值
        mock_random.randint.return_value = 300
        mock_random.uniform.return_value = 1.0

        # 执行测试
        self.service.simulate_human_behavior()

        # 验证行为
        self.service.driver.execute_script.assert_called_with("window.scrollBy(0, 300)")
        mock_time.sleep.assert_called_with(1.0)

    def test_simulate_human_behavior_without_driver(self):
        """测试无驱动时模拟人类行为"""
        # 确保没有驱动
        self.service.driver = None

        # 应该不会抛出异常
        self.service.simulate_human_behavior()

    @patch("src.services.browser_service.random")
    @patch("src.services.browser_service.time")
    def test_dynamic_delay(self, mock_time, mock_random):
        """测试动态延迟"""
        # 设置mock随机值
        mock_random.uniform.return_value = 3.0

        # 初始下载计数为0
        self.service.download_count = 0

        # 执行测试
        self.service.dynamic_delay()

        # 验证延迟调用
        mock_time.sleep.assert_called_with(3.0)

        # 测试下载计数增加后的延迟因子
        self.service.download_count = 10
        self.service.dynamic_delay()

        # 验证延迟因子计算
        expected_min = 2.0 * (1 + 10 / 20)  # 1.5倍
        expected_max = 8.0 * (1 + 10 / 20)  # 1.5倍
        mock_random.uniform.assert_called_with(expected_min, expected_max)

    def test_wait_for_element_success(self):
        """测试成功等待元素"""
        # 设置mock驱动
        self.service.driver = Mock()

        # 设置mock等待
        with patch("src.services.browser_service.WebDriverWait") as mock_wait:
            mock_wait_instance = Mock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = True

            # Mock BrowserConfig
            with patch.object(
                self.service.browser_config, "get_timeout"
            ) as mock_timeout:
                mock_timeout.return_value = 10

                # 执行测试
                result = self.service.wait_for_element(("id", "test-element"))

                # 验证结果
                assert result is True

    def test_wait_for_element_timeout(self):
        """测试等待元素超时"""
        # 设置mock驱动
        self.service.driver = Mock()

        # 设置mock等待超时
        with patch("src.services.browser_service.WebDriverWait") as mock_wait:
            mock_wait_instance = Mock()
            mock_wait.return_value = mock_wait_instance

            # 模拟TimeoutException
            from selenium.common.exceptions import TimeoutException

            mock_wait_instance.until.side_effect = TimeoutException("Timeout")

            # Mock BrowserConfig
            with patch.object(
                self.service.browser_config, "get_timeout"
            ) as mock_timeout:
                mock_timeout.return_value = 10

                # 执行测试
                result = self.service.wait_for_element(("id", "test-element"))

                # 验证结果
                assert result is False

    def test_wait_for_element_without_driver(self):
        """测试无驱动时等待元素"""
        # 确保没有驱动
        self.service.driver = None

        # 由于实际代码没有检查driver是否为None，这会抛出AttributeError
        # 我们需要捕获这个异常
        with pytest.raises(AttributeError):
            self.service.wait_for_element(("id", "test-element"))

    @patch("src.services.browser_service.BrowserService.setup_driver")
    def test_restart_driver(self, mock_setup_driver):
        """测试重启驱动"""
        # 设置现有驱动
        self.service.driver = Mock()
        self.service.download_count = 5

        # 执行重启
        self.service.restart_driver()

        # 验证驱动被关闭
        self.service.driver.quit.assert_called_once()

        # 验证下载计数被重置
        assert self.service.download_count == 0

        # 验证重新设置驱动
        mock_setup_driver.assert_called_once()

    def test_restart_driver_without_existing_driver(self):
        """测试重启无现有驱动"""
        # 确保没有现有驱动
        self.service.driver = None

        with patch(
            "src.services.browser_service.BrowserService.setup_driver"
        ) as mock_setup_driver:
            # 执行重启
            self.service.restart_driver()

            # 验证重新设置驱动
            mock_setup_driver.assert_called_once()

    def test_close_with_driver(self):
        """测试关闭有驱动"""
        # 设置mock驱动
        mock_driver = Mock()
        self.service.driver = mock_driver

        # 执行关闭
        self.service.close()

        # 验证驱动被关闭
        mock_driver.quit.assert_called_once()
        assert self.service.driver is None

    def test_init_anti_crawler(self):
        """测试反爬虫策略初始化"""
        # 验证反爬虫策略已初始化
        assert self.service.anti_crawler is not None

        # 验证配置已设置
        # 检查AntiCrawlerStrategy的实际属性
        assert hasattr(self.service.anti_crawler, "min_delay")
        assert hasattr(self.service.anti_crawler, "max_delay")
        assert hasattr(self.service.anti_crawler, "max_session_downloads")
        assert hasattr(self.service.anti_crawler, "set_session_parameters")

    def test_error_handling_consistency(self):
        """测试错误处理的一致性"""
        # 测试各种边界情况下的错误处理

        # 无驱动时的各种操作
        self.service.driver = None

        # 模拟人类行为应该不会抛出异常
        self.service.simulate_human_behavior()

        # 等待元素会抛出AttributeError（因为driver为None）
        with pytest.raises(AttributeError):
            self.service.wait_for_element(("id", "test"))

        # 关闭应该不会抛出异常
        self.service.close()

    def test_close_without_driver(self):
        """测试关闭无驱动"""
        # 确保没有驱动
        self.service.driver = None

        # 应该不会抛出异常
        self.service.close()

    def test_context_manager(self):
        """测试上下文管理器"""
        # 测试进入上下文
        with patch.object(self.service, "setup_driver") as mock_setup:
            # 模拟上下文管理器使用
            with self.service as service:
                assert service == self.service

            # 验证退出上下文时调用了close
            with patch.object(self.service, "close") as mock_close:
                self.service.__exit__(None, None, None)
                mock_close.assert_called_once()

    def test_download_count_tracking(self):
        """测试下载计数跟踪"""
        # 初始下载计数
        assert self.service.download_count == 0

        # 增加下载计数
        self.service.download_count += 1
        assert self.service.download_count == 1

        # 重启后重置
        with patch("src.services.browser_service.BrowserService.setup_driver"):
            self.service.restart_driver()
            assert self.service.download_count == 0


class TestBrowserServiceEdgeCases:
    """BrowserService边界情况测试"""

    def setup_method(self):
        """测试初始化"""
        self.mock_config_manager = Mock(spec=ConfigManager)
        # 设置基础mock配置
        self.mock_config_manager.get.side_effect = lambda key, default=None: {
            "save_dir": "/tmp/test"
        }.get(key, default)

    def test_init_with_none_config(self):
        """测试使用None配置初始化"""
        service = BrowserService(config_manager=None)
        assert service.config_manager is not None

    @patch("src.services.browser_service.webdriver.Chrome")
    @patch("src.services.browser_service.BrowserConfig")
    def test_setup_driver_with_custom_timeout(self, mock_browser_config, mock_chrome):
        """测试自定义超时设置"""
        # 设置mock
        mock_config_instance = Mock()
        mock_config_instance.is_headless.return_value = True
        mock_config_instance.get_all_timeouts.return_value = {"page_load": 30}
        mock_config_instance.get_window_size.return_value = "1920,1080"
        mock_config_instance.get_random_user_agent.return_value = "test-user-agent"
        mock_config_instance.get_page_load_strategy.return_value = "normal"
        mock_browser_config.return_value = mock_config_instance

        service = BrowserService(config_manager=self.mock_config_manager)

        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        # 测试自定义超时
        service.setup_driver(headless=True)

        # 验证超时设置被调用
        mock_driver.set_page_load_timeout.assert_called_once()

    @patch("src.services.browser_service.BrowserConfig")
    def test_get_chrome_options_with_special_characters(self, mock_browser_config):
        """测试特殊字符的下载目录"""
        # 设置mock
        mock_config_instance = Mock()
        mock_config_instance.get_random_user_agent.return_value = "test-user-agent"
        mock_config_instance.get_page_load_strategy.return_value = "normal"
        mock_browser_config.return_value = mock_config_instance

        service = BrowserService(config_manager=self.mock_config_manager)

        # Mock下载目录包含特殊字符
        with patch.object(service, "_get_download_directory") as mock_dir:
            mock_dir.return_value = "/tmp/test with spaces/下载目录"

            options = service._get_chrome_options(headless=False)

            # 验证下载配置包含特殊字符路径
            prefs = options.experimental_options.get("prefs", {})
            assert "download.default_directory" in prefs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
