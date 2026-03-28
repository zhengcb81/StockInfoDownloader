"""
Playwright Async Strategy Module Unit Tests
"""

import asyncio

import pytest
from unittest.mock import patch
import nest_asyncio

from src.web.playwright_async_strategy import PlaywrightAsyncStrategy

# Allow nested event loops for pytest-asyncio compatibility
nest_asyncio.apply()


class TestPlaywrightAsyncStrategy:
    """Test Playwright async strategy"""

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_strategy_initialization(self, mock_config):
        """Test strategy initialization"""
        strategy = PlaywrightAsyncStrategy(
            headless=True,
            download_dir="/tmp/downloads",
            config={"timeout": 30}
        )

        assert strategy.headless is True
        assert strategy.download_dir == "/tmp/downloads"
        assert strategy.browser is None
        assert strategy.page is None

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_get_driver_no_page(self, mock_config):
        """Test get driver with no page"""
        strategy = PlaywrightAsyncStrategy()

        driver = strategy.get_driver()

        assert driver is None

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_build_launch_options(self, mock_config):
        """Test build launch options"""
        strategy = PlaywrightAsyncStrategy(headless=True)

        options = strategy._build_launch_options()

        assert isinstance(options, dict)
        assert "headless" in options
        assert "args" in options

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_build_context_options(self, mock_config):
        """Test build context options"""
        strategy = PlaywrightAsyncStrategy(download_dir="/tmp/downloads")

        options = strategy._build_context_options()

        assert isinstance(options, dict)
        assert "viewport" in options

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_navigate_no_page(self, mock_config):
        """Test navigate with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(strategy.navigate("http://example.com"))
            assert result is False
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_find_elements_no_page(self, mock_config):
        """Test find elements with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            elements = loop.run_until_complete(strategy.find_elements("div.test"))
            assert elements == []
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_click_no_element(self, mock_config):
        """Test click with no element"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(strategy.click(None))
            assert result is False
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_get_text_no_element(self, mock_config):
        """Test get text with no element"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            text = loop.run_until_complete(strategy.get_text(None))
            assert text == ""
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_get_attribute_no_element(self, mock_config):
        """Test get attribute with no element"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            attr = loop.run_until_complete(strategy.get_attribute(None, "data-test"))
            assert attr is None
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_execute_script_no_page(self, mock_config):
        """Test execute script with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(strategy.execute_script("return document.title"))
            assert result is None
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_wait_for_element_no_page(self, mock_config):
        """Test wait for element with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(strategy.wait_for_element("div.test"))
            assert result is False
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_get_page_source_no_page(self, mock_config):
        """Test get page source with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            source = loop.run_until_complete(strategy.get_page_source())
            assert source == ""
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_get_current_url_no_page(self, mock_config):
        """Test get current URL with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            url = loop.run_until_complete(strategy.get_current_url())
            assert url == ""
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_get_page_title_no_page(self, mock_config):
        """Test get page title with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            title = loop.run_until_complete(strategy.get_page_title())
            assert title == ""
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_close_no_browser(self, mock_config):
        """Test close with no browser"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(strategy.close())
            assert strategy.browser is None
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_is_healthy_no_page(self, mock_config):
        """Test is healthy with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            is_healthy = loop.run_until_complete(strategy.is_healthy())
            assert is_healthy is False
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_take_screenshot_no_page(self, mock_config):
        """Test take screenshot with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            screenshot = loop.run_until_complete(strategy.take_screenshot())
            assert screenshot is None
        finally:
            loop.close()

    @patch('src.web.playwright_async_strategy.ConfigManager')
    def test_download_file_no_page(self, mock_config):
        """Test download file with no page"""
        strategy = PlaywrightAsyncStrategy()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                strategy.download_file("http://example.com/file.pdf", "/tmp/file.pdf")
            )
            assert result is False
        finally:
            loop.close()
