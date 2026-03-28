"""
Selenium Driver Factory Module Unit Tests
测试Selenium WebDriver工厂功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.web.selenium.driver_factory import ChromeDriverFactory


class TestChromeDriverFactory:
    """测试Chrome WebDriver工厂"""

    def test_factory_initialization(self):
        """测试工厂初始化"""
        factory = ChromeDriverFactory(
            headless=True,
            download_dir="/tmp/downloads",
            config={"window_size": "1920,1080"}
        )

        assert factory.headless == True
        assert factory.download_dir == "/tmp/downloads"
        assert factory.window_size == "1920,1080"

    def test_factory_default_config(self):
        """测试工厂默认配置"""
        factory = ChromeDriverFactory()

        assert factory.headless == True
        assert factory.download_dir is None

    @patch('src.web.selenium.driver_factory.webdriver.Chrome')
    @patch('src.web.selenium.driver_factory.is_test_environment')
    def test_create_driver(self, mock_is_test, mock_chrome):
        """测试创建driver"""
        mock_is_test.return_value = True
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        factory = ChromeDriverFactory()
        driver = factory.create_driver()

        assert driver is not None
        mock_chrome.assert_called()

    def test_build_chrome_options(self):
        """测试构建Chrome选项"""
        factory = ChromeDriverFactory(headless=True)

        options = factory._build_chrome_options()

        assert options is not None
        # 验证一些基本参数被设置
        assert hasattr(options, 'arguments')

    def test_build_chrome_options_with_download_dir(self, tmp_path):
        """测试带下载目录的Chrome选项"""
        factory = ChromeDriverFactory(download_dir=str(tmp_path))

        options = factory._build_chrome_options()

        assert options is not None

    @patch('src.web.selenium.driver_factory.is_test_environment')
    @patch('src.web.selenium.driver_factory.subprocess.run')
    def test_cleanup_chrome_processes_in_test(self, mock_subprocess, mock_is_test):
        """测试在测试环境中清理Chrome进程"""
        mock_is_test.return_value = True
        factory = ChromeDriverFactory()

        factory._cleanup_chrome_processes()

        # 测试环境不应该执行清理
        mock_subprocess.assert_not_called()

    @patch('src.web.selenium.driver_factory.is_test_environment')
    @patch('src.web.selenium.driver_factory.platform.system')
    @patch('src.web.selenium.driver_factory.subprocess.run')
    def test_cleanup_windows(self, mock_subprocess, mock_platform, mock_is_test):
        """测试Windows系统清理"""
        mock_is_test.return_value = False
        mock_platform.return_value = "Windows"
        factory = ChromeDriverFactory()

        factory._cleanup_chrome_processes()

        mock_subprocess.assert_called_once()

    @patch('src.web.selenium.driver_factory.is_test_environment')
    @patch('src.web.selenium.driver_factory.platform.system')
    @patch('src.web.selenium.driver_factory.subprocess.run')
    def test_cleanup_linux(self, mock_subprocess, mock_platform, mock_is_test):
        """测试Linux系统清理"""
        mock_is_test.return_value = False
        mock_platform.return_value = "Linux"
        factory = ChromeDriverFactory()

        factory._cleanup_chrome_processes()

        mock_subprocess.assert_called_once()
