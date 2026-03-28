"""
Selenium Strategy Module Tests
Tests for Selenium browser automation strategy
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.constants import BrowserConfig, TimeoutConfig
from src.web.browser_strategy import BrowserAutomationStrategy
from src.web.selenium.strategy import SeleniumStrategy


class TestSeleniumStrategy:
    """SeleniumStrategy class tests"""

    def test_init_default(self):
        """Test initialization with default values"""
        strategy = SeleniumStrategy()
        assert strategy.headless is True
        assert strategy.download_dir is None
        assert strategy.config == {}
        assert strategy.driver is None
        assert strategy.download_count == 0
        assert strategy.window_size == BrowserConfig.DEFAULT_WINDOW_SIZE

    def test_init_with_params(self):
        """Test initialization with custom parameters"""
        config = {
            "window_size": "1280,720",
            "timeout": 60,
            "implicit_wait": 5,
            "max_downloads_per_session": 10,
        }
        strategy = SeleniumStrategy(
            headless=False,
            download_dir="/tmp/downloads",
            config=config
        )
        assert strategy.headless is False
        assert strategy.download_dir == "/tmp/downloads"
        assert strategy.config == config
        assert strategy.window_size == "1280,720"
        assert strategy.page_load_timeout == 60
        assert strategy.implicit_wait == 5

    def test_driver_factory_initialized(self):
        """Test that driver factory is initialized"""
        strategy = SeleniumStrategy()
        assert strategy._driver_factory is not None
        assert strategy._download_manager is None

    def test_initialize_success(self):
        """Test successful initialization"""
        mock_driver = MagicMock()
        strategy = SeleniumStrategy()

        with patch.object(strategy._driver_factory, "create_driver", return_value=mock_driver):
            result = strategy.initialize()

            assert result is True
            assert strategy.driver is mock_driver

    def test_initialize_failure(self):
        """Test initialization failure handling"""
        strategy = SeleniumStrategy()

        with patch.object(strategy._driver_factory, "create_driver", side_effect=Exception("Init failed")):
            result = strategy.initialize()
            assert result is False
            assert strategy.driver is None

    def test_get_driver_none(self):
        """Test get_driver when driver is None"""
        strategy = SeleniumStrategy()
        assert strategy.get_driver() is None

    def test_get_driver_returns_driver(self):
        """Test get_driver returns driver instance"""
        mock_driver = MagicMock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        assert strategy.get_driver() is mock_driver

    def test_navigate_no_driver(self):
        """Test navigate when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.navigate("https://example.com")
        assert result is False

    def test_navigate_success(self):
        """Test successful navigation"""
        mock_driver = MagicMock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.navigate("https://example.com")
        assert result is True
        mock_driver.get.assert_called_once_with("https://example.com")

    def test_navigate_failure(self):
        """Test navigation failure handling"""
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("Navigation failed")
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.navigate("https://example.com")
        assert result is False

    def test_navigate_to_page_compatibility(self):
        """Test navigate_to_page for compatibility"""
        mock_driver = MagicMock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.navigate_to_page("https://example.com")
        assert result is True
        mock_driver.get.assert_called_once_with("https://example.com")

    def test_find_elements_no_driver(self):
        """Test find_elements when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.find_elements("#test")
        assert result == []

    def test_find_elements_css(self):
        """Test find elements with CSS selector"""
        mock_driver = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]
        mock_driver.find_elements.return_value = mock_elements

        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.find_elements(".test-class", by="css")
        assert result == mock_elements

    def test_find_elements_xpath(self):
        """Test find elements with XPath"""
        mock_driver = MagicMock()
        mock_elements = [MagicMock()]
        mock_driver.find_elements.return_value = mock_elements

        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.find_elements("//div[@class='test']", by="xpath")
        assert result == mock_elements

    def test_find_element_returns_first(self):
        """Test find_element returns first element"""
        mock_elements = [MagicMock(), MagicMock()]
        with patch.object(SeleniumStrategy, "find_elements", return_value=mock_elements):
            strategy = SeleniumStrategy()
            result = strategy.find_element("#test")
            assert result is mock_elements[0]

    def test_find_element_returns_none(self):
        """Test find_element returns None when no elements"""
        with patch.object(SeleniumStrategy, "find_elements", return_value=[]):
            strategy = SeleniumStrategy()
            result = strategy.find_element("#test")
            assert result is None

    def test_click_success(self):
        """Test successful element click"""
        mock_element = MagicMock()
        strategy = SeleniumStrategy()
        result = strategy.click(mock_element)
        assert result is True
        mock_element.click.assert_called_once()

    def test_click_none_element(self):
        """Test click with None element"""
        strategy = SeleniumStrategy()
        result = strategy.click(None)
        assert result is False

    def test_click_failure(self):
        """Test click failure handling"""
        mock_element = MagicMock()
        mock_element.click.side_effect = Exception("Click failed")
        strategy = SeleniumStrategy()
        result = strategy.click(mock_element)
        assert result is False

    def test_get_text_success(self):
        """Test getting element text"""
        mock_element = MagicMock()
        mock_element.text = "Test Text"
        strategy = SeleniumStrategy()
        result = strategy.get_text(mock_element)
        assert result == "Test Text"

    def test_get_text_none_element(self):
        """Test get_text with None element"""
        strategy = SeleniumStrategy()
        result = strategy.get_text(None)
        assert result == ""

    def test_get_attribute_success(self):
        """Test getting element attribute"""
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "attribute-value"
        strategy = SeleniumStrategy()
        result = strategy.get_attribute(mock_element, "href")
        assert result == "attribute-value"

    def test_get_attribute_none_element(self):
        """Test get_attribute with None element"""
        strategy = SeleniumStrategy()
        result = strategy.get_attribute(None, "href")
        assert result is None

    def test_execute_script_no_driver(self):
        """Test execute_script when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.execute_script("return true")
        assert result is None

    def test_execute_script_success(self):
        """Test successful script execution"""
        mock_driver = MagicMock()
        mock_driver.execute_script.return_value = 42
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.execute_script("return 2 * 21")
        assert result == 42

    def test_wait_for_element_no_driver(self):
        """Test wait_for_element when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.wait_for_element("#test")
        assert result is False

    def test_wait_for_element_visible(self):
        """Test waiting for visible element"""
        mock_driver = MagicMock()
        mock_wait = MagicMock()
        mock_wait.until.return_value = True

        with patch("src.web.selenium.strategy.WebDriverWait", return_value=mock_wait):
            strategy = SeleniumStrategy()
            strategy.driver = mock_driver

            result = strategy.wait_for_element("#test", condition="visible")
            assert result is True

    def test_wait_for_element_presence(self):
        """Test waiting for element presence"""
        mock_driver = MagicMock()
        mock_wait = MagicMock()
        mock_wait.until.return_value = True

        with patch("src.web.selenium.strategy.WebDriverWait", return_value=mock_wait):
            strategy = SeleniumStrategy()
            strategy.driver = mock_driver

            result = strategy.wait_for_element("#test", condition="presence")
            assert result is True

    def test_get_page_source_no_driver(self):
        """Test get_page_source when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.get_page_source()
        assert result == ""

    def test_get_page_source_success(self):
        """Test successful get_page_source"""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>Test</body></html>"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.get_page_source()
        assert result == "<html><body>Test</body></html>"

    def test_get_current_url_no_driver(self):
        """Test get_current_url when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.get_current_url()
        assert result == ""

    def test_get_current_url_success(self):
        """Test successful get_current_url"""
        mock_driver = MagicMock()
        mock_driver.current_url = "https://example.com/page"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.get_current_url()
        assert result == "https://example.com/page"

    def test_get_page_title_no_driver(self):
        """Test get_page_title when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.get_page_title()
        assert result == ""

    def test_get_page_title_success(self):
        """Test successful get_page_title"""
        mock_driver = MagicMock()
        mock_driver.title = "Test Page"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.get_page_title()
        assert result == "Test Page"

    def test_is_healthy_no_driver(self):
        """Test is_healthy when no driver"""
        strategy = SeleniumStrategy()
        assert strategy.is_healthy() is False

    def test_is_healthy_success(self):
        """Test is_healthy when driver is working"""
        mock_driver = MagicMock()
        mock_driver.current_url = "https://example.com"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        assert strategy.is_healthy() is True

    def test_is_healthy_exception(self):
        """Test is_healthy when driver raises exception"""
        mock_driver = MagicMock()
        # Mock current_url as a property that raises exception
        from unittest.mock import PropertyMock
        type(mock_driver).current_url = PropertyMock(side_effect=Exception("Driver error"))
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        assert strategy.is_healthy() is False

    def test_take_screenshot_no_driver(self):
        """Test take_screenshot when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.take_screenshot()
        assert result is None

    def test_take_screenshot_success(self):
        """Test successful screenshot"""
        mock_driver = MagicMock()
        mock_driver.get_screenshot_as_png.return_value = b"fake_png_data"
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        result = strategy.take_screenshot()
        assert result == b"fake_png_data"

    def test_take_screenshot_with_save_path(self):
        """Test screenshot with save path"""
        mock_driver = MagicMock()
        mock_driver.get_screenshot_as_png.return_value = b"fake_png_data"

        with patch("builtins.open", create=True) as mock_open:
            strategy = SeleniumStrategy()
            strategy.driver = mock_driver

            result = strategy.take_screenshot("/tmp/screenshot.png")
            assert result == b"fake_png_data"

    def test_cleanup(self):
        """Test cleanup method"""
        mock_driver = MagicMock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        strategy.cleanup()
        assert strategy.driver is None

    def test_close(self):
        """Test close method"""
        mock_driver = MagicMock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver
        strategy._download_manager = MagicMock()

        with patch("src.web.selenium.strategy.safe_cleanup"):
            strategy.close()
            assert strategy.driver is None
            assert strategy._download_manager is None

    def test_download_file_no_manager(self):
        """Test download_file when manager not initialized"""
        strategy = SeleniumStrategy()
        result = strategy.download_file("https://example.com/file.pdf", "/tmp/file.pdf")
        assert result is False

    def test_download_file_success(self):
        """Test successful file download"""
        mock_manager = MagicMock()
        mock_manager.download_file.return_value = True
        mock_manager.download_count = 5
        strategy = SeleniumStrategy()
        strategy._download_manager = mock_manager

        result = strategy.download_file("https://example.com/file.pdf", "/tmp/file.pdf")
        assert result is True
        assert strategy.download_count == 5

    def test_go_to_page_no_driver(self):
        """Test go_to_page when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.go_to_page(5)
        assert result is False

    def test_go_to_page_success(self):
        """Test successful page navigation"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        with patch.object(strategy, "find_element", return_value=mock_element), \
             patch("time.sleep"):
            result = strategy.go_to_page(5)
            assert result is True

    def test_go_to_next_page_no_driver(self):
        """Test go_to_next_page when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.go_to_next_page()
        assert result is False

    def test_go_to_next_page_success(self):
        """Test successful next page navigation"""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        strategy = SeleniumStrategy()
        strategy.driver = mock_driver

        with patch.object(strategy, "find_element", return_value=mock_element), \
             patch.object(strategy, "click", return_value=True), \
             patch("time.sleep"):
            result = strategy.go_to_next_page()
            assert result is True

    def test_has_next_page_no_driver(self):
        """Test has_next_page when no driver"""
        strategy = SeleniumStrategy()
        result = strategy.has_next_page()
        assert result is False

    def test_has_next_page_disabled_button(self):
        """Test has_next_page when disabled button exists"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        with patch.object(strategy, "find_element", return_value=MagicMock()):
            result = strategy.has_next_page()
            # Disabled button found means no next page
            assert result is False

    def test_has_next_page_no_disabled_button(self):
        """Test has_next_page when no disabled button"""
        strategy = SeleniumStrategy()
        strategy.driver = MagicMock()

        with patch.object(strategy, "find_element", return_value=None):
            result = strategy.has_next_page()
            assert result is True

    def test_restart_success(self):
        """Test successful restart"""
        mock_driver = MagicMock()
        strategy = SeleniumStrategy()

        with patch.object(strategy, "close"), \
             patch.object(strategy, "create_driver", return_value=mock_driver):
            result = strategy.restart()
            assert result is True

    def test_restart_failure_after_all_attempts(self):
        """Test restart failure after all attempts"""
        strategy = SeleniumStrategy()

        with patch.object(strategy, "close"), \
             patch.object(strategy, "create_driver", side_effect=Exception("Create failed")), \
             patch("time.sleep"):
            result = strategy.restart()
            assert result is False

    def test_is_subclass_of_browser_automation_strategy(self):
        """Test SeleniumStrategy is subclass of BrowserAutomationStrategy"""
        assert issubclass(SeleniumStrategy, BrowserAutomationStrategy)

    def test_has_all_abstract_methods(self):
        """Test SeleniumStrategy implements all abstract methods"""
        from src.web.browser_strategy import BrowserAutomationStrategy

        abstract_methods = BrowserAutomationStrategy.__abstractmethods__
        for method in abstract_methods:
            assert hasattr(SeleniumStrategy, method)
