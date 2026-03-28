"""
Browser Strategy Module Tests
Tests for browser strategy abstract base class and factory
"""

from unittest.mock import MagicMock, patch

import pytest

from src.web.browser_strategy import (
    BrowserAutomationStrategy,
    BrowserStrategy,
    BrowserStrategyFactory,
)


class TestBrowserAutomationStrategy:
    """BrowserAutomationStrategy abstract class tests"""

    def test_cannot_instantiate_abc(self):
        """Test that abstract base class cannot be instantiated"""
        with pytest.raises(TypeError):
            BrowserAutomationStrategy()

    def test_has_abstract_methods(self):
        """Test that all abstract methods are defined"""
        abstract_methods = BrowserAutomationStrategy.__abstractmethods__
        expected_methods = {
            "__init__",
            "create_driver",
            "get_driver",
            "navigate",
            "find_elements",
            "find_element",
            "click",
            "get_text",
            "get_attribute",
            "execute_script",
            "wait_for_element",
            "get_page_source",
            "get_current_url",
            "cleanup",
            "is_healthy",
            "restart",
            "take_screenshot",
            "download_file",
            "go_to_next_page",
            "go_to_page",
            "has_next_page",
            "get_current_page_info",
            "initialize",
        }
        assert abstract_methods == expected_methods

    def test_backwards_compatible_alias(self):
        """Test that BrowserStrategy is an alias"""
        assert BrowserStrategy is BrowserAutomationStrategy


class TestBrowserStrategyFactory:
    """BrowserStrategyFactory class tests"""

    def test_create_selenium_strategy(self):
        """Test creating selenium strategy"""
        with patch("src.web.selenium_strategy.SeleniumStrategy") as mock_selenium:
            mock_instance = MagicMock()
            mock_selenium.return_value = mock_instance

            strategy = BrowserStrategyFactory.create_strategy("selenium", headless=True)

            mock_selenium.assert_called_once_with(headless=True)
            assert strategy is mock_instance

    def test_create_playwright_strategy(self):
        """Test creating playwright strategy"""
        with patch("src.web.playwright_strategy.PlaywrightStrategy") as mock_playwright:
            mock_instance = MagicMock()
            mock_playwright.return_value = mock_instance

            strategy = BrowserStrategyFactory.create_strategy("playwright", headless=False)

            mock_playwright.assert_called_once_with(headless=False)
            assert strategy is mock_instance

    def test_create_strategy_case_insensitive(self):
        """Test that strategy type is case insensitive"""
        with patch("src.web.playwright_strategy.PlaywrightStrategy") as mock_playwright:
            mock_instance = MagicMock()
            mock_playwright.return_value = mock_instance

            # Test various case combinations
            for strategy_type in ["PLAYWRIGHT", "Playwright", "pLaYwRiGhT"]:
                mock_playwright.reset_mock()
                strategy = BrowserStrategyFactory.create_strategy(strategy_type)
                mock_playwright.assert_called_once()
                assert strategy is mock_instance

    def test_create_strategy_invalid_type(self):
        """Test creating strategy with invalid type"""
        with pytest.raises(ValueError, match="不支持的浏览器策略类型"):
            BrowserStrategyFactory.create_strategy("invalid_strategy")

    def test_create_strategy_passes_kwargs(self):
        """Test that kwargs are passed through"""
        with patch("src.web.selenium_strategy.SeleniumStrategy") as mock_selenium:
            mock_instance = MagicMock()
            mock_selenium.return_value = mock_instance

            kwargs = {
                "headless": True,
                "download_dir": "/tmp/downloads",
                "timeout": 30,
            }
            strategy = BrowserStrategyFactory.create_strategy("selenium", **kwargs)

            mock_selenium.assert_called_once_with(**kwargs)
            assert strategy is mock_instance
