"""
Selenium Strategy Module Unit Tests
测试Selenium浏览器自动化策略
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.web.selenium.strategy import SeleniumStrategy


class TestSeleniumStrategy:
    """测试Selenium策略"""

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_strategy_initialization(self, mock_config, mock_factory):
        """测试策略初始化"""
        strategy = SeleniumStrategy(
            headless=True,
            download_dir="/tmp/downloads",
            config={"timeout": 30}
        )

        assert strategy.headless == True
        assert strategy.download_dir == "/tmp/downloads"
        assert strategy.driver is None

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_create_driver(self, mock_config, mock_factory):
        """测试创建driver"""
        mock_driver = Mock()
        mock_factory_instance = Mock()
        mock_factory_instance.create_driver.return_value = mock_driver
        mock_factory.return_value = mock_factory_instance

        strategy = SeleniumStrategy()
        driver = strategy.create_driver()

        assert driver == mock_driver
        assert strategy.driver == mock_driver

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_initialize(self, mock_config, mock_factory):
        """测试初始化浏览器"""
        mock_driver = Mock()
        mock_factory_instance = Mock()
        mock_factory_instance.create_driver.return_value = mock_driver
        mock_factory.return_value = mock_factory_instance

        strategy = SeleniumStrategy()
        result = strategy.initialize()

        assert result == True
        assert strategy.driver == mock_driver

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_get_driver(self, mock_config, mock_factory):
        """测试获取driver"""
        mock_driver = Mock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        driver = strategy.get_driver()
        assert driver == mock_driver

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_navigate(self, mock_config, mock_factory):
        """测试导航"""
        mock_driver = Mock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.navigate("http://example.com")

        assert result == True
        mock_driver.get.assert_called_once_with("http://example.com")

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_navigate_to_page(self, mock_config, mock_factory):
        """测试导航到页面"""
        mock_driver = Mock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.navigate_to_page("http://example.com")

        assert result == True
        mock_driver.get.assert_called_once_with("http://example.com")

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_find_elements(self, mock_config, mock_factory):
        """测试查找元素"""
        mock_elements = [Mock(), Mock()]
        mock_driver = Mock()
        mock_driver.find_elements.return_value = mock_elements
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        elements = strategy.find_elements("div.test")

        assert len(elements) == 2
        mock_driver.find_elements.assert_called_once()

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_find_element(self, mock_config, mock_factory):
        """测试查询单个元素"""
        mock_element = Mock()
        mock_driver = Mock()
        mock_driver.find_elements.return_value = [mock_element]
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        element = strategy.find_element("div.test")

        assert element == mock_element

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_click(self, mock_config, mock_factory):
        """测试点击元素"""
        mock_element = Mock()
        strategy = SeleniumStrategy()

        result = strategy.click(mock_element)

        assert result == True
        mock_element.click.assert_called_once()

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_get_text(self, mock_config, mock_factory):
        """测试获取元素文本"""
        mock_element = Mock()
        mock_element.text = "Test Text"
        strategy = SeleniumStrategy()

        text = strategy.get_text(mock_element)

        assert text == "Test Text"

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_get_attribute(self, mock_config, mock_factory):
        """测试获取元素属性"""
        mock_element = Mock()
        mock_element.get_attribute.return_value = "test-value"
        strategy = SeleniumStrategy()

        attr = strategy.get_attribute(mock_element, "data-test")

        assert attr == "test-value"

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_execute_script(self, mock_config, mock_factory):
        """测试执行脚本"""
        mock_driver = Mock()
        mock_driver.execute_script.return_value = "result"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.execute_script("return document.title")

        assert result == "result"
        mock_driver.execute_script.assert_called_once()

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_get_page_source(self, mock_config, mock_factory):
        """测试获取页面源代码"""
        mock_driver = Mock()
        mock_driver.page_source = "<html></html>"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        source = strategy.get_page_source()

        assert source == "<html></html>"

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_get_current_url(self, mock_config, mock_factory):
        """测试获取当前URL"""
        mock_driver = Mock()
        mock_driver.current_url = "http://example.com"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        url = strategy.get_current_url()

        assert url == "http://example.com"

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_get_page_title(self, mock_config, mock_factory):
        """测试获取页面标题"""
        mock_driver = Mock()
        mock_driver.title = "Test Page"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        title = strategy.get_page_title()

        assert title == "Test Page"

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.safe_cleanup')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_close(self, mock_config, mock_factory, mock_cleanup):
        """测试关闭浏览器"""
        mock_driver = Mock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        strategy.close()

        assert strategy.driver is None

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_is_healthy(self, mock_config, mock_factory):
        """测试健康检查"""
        mock_driver = Mock()
        mock_driver.current_url = "http://example.com"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        is_healthy = strategy.is_healthy()

        assert is_healthy == True

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_take_screenshot(self, mock_config, mock_factory):
        """测试截图"""
        mock_driver = Mock()
        mock_driver.get_screenshot_as_png.return_value = b"fake_png_data"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        screenshot = strategy.take_screenshot()

        assert screenshot == b"fake_png_data"

    @patch('src.web.selenium.strategy.ChromeDriverFactory')
    @patch('src.web.selenium.strategy.ConfigManager')
    def test_cleanup(self, mock_config, mock_factory):
        """测试清理资源"""
        mock_driver = Mock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        strategy.cleanup()

        # Should call close
        assert strategy.driver is None
