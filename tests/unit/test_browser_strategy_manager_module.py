"""
Browser Strategy Manager Module Tests
Tests for browser strategy manager functionality
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import BrowserStrategyError
from src.web.browser_strategy import BrowserAutomationStrategy
from src.web.browser_strategy_manager import (
    BrowserStrategyManager,
    BrowserType,
)


class TestBrowserType:
    """BrowserType enum tests"""

    def test_browser_type_values(self):
        """Test browser type enum values"""
        assert BrowserType.SELENIUM.value == "selenium"
        assert BrowserType.PLAYWRIGHT.value == "playwright"


class TestBrowserStrategyManager:
    """BrowserStrategyManager class tests"""

    def test_init_default(self):
        """Test initialization with default config"""
        manager = BrowserStrategyManager()
        assert manager.config_manager is not None
        assert manager._current_strategy is None
        assert manager._current_type is None
        assert manager.default_browser_type in ["selenium", "playwright"]

    def test_init_with_config_file(self):
        """Test initialization with config file"""
        with patch("src.web.browser_strategy_manager.ConfigManager") as mock_cm:
            manager = BrowserStrategyManager(config_file="test_config.json")
            mock_cm.assert_called_once_with("test_config.json")

    def test_init_with_invalid_browser_type(self):
        """Test initialization with invalid browser type falls back to playwright"""
        with patch("src.web.browser_strategy_manager.ConfigManager") as mock_cm:
            mock_config = MagicMock()
            mock_config.get.return_value = "invalid_type"
            mock_cm.return_value = mock_config

            manager = BrowserStrategyManager()
            assert manager.default_browser_type == "playwright"

    def test_get_current_strategy_none(self):
        """Test get_current_strategy when none exists"""
        manager = BrowserStrategyManager()
        assert manager.get_current_strategy() is None

    def test_get_current_type_none(self):
        """Test get_current_type when none exists"""
        manager = BrowserStrategyManager()
        assert manager.get_current_type() is None

    def test_get_strategy_with_playwright(self):
        """Test getting Playwright strategy"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            strategy = manager.get_strategy(BrowserType.PLAYWRIGHT)

            assert strategy is mock_instance
            assert manager._current_strategy is mock_instance
            assert manager._current_type == BrowserType.PLAYWRIGHT

    def test_get_strategy_with_selenium(self):
        """Test getting Selenium strategy"""
        with patch("src.web.browser_strategy_manager.SeleniumStrategy") as mock_sel:
            mock_instance = MagicMock()
            mock_sel.return_value = mock_instance

            manager = BrowserStrategyManager()
            strategy = manager.get_strategy(BrowserType.SELENIUM)

            assert strategy is mock_instance
            assert manager._current_strategy is mock_instance
            assert manager._current_type == BrowserType.SELENIUM

    def test_get_strategy_string_type(self):
        """Test getting strategy with string type"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            strategy = manager.get_strategy("playwright")

            assert strategy is mock_instance

    def test_get_strategy_string_case_insensitive(self):
        """Test that string type is case insensitive"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            strategy = manager.get_strategy("PLAYWRIGHT")

            assert strategy is mock_instance

    def test_get_strategy_same_type_returns_cached(self):
        """Test that requesting same type returns cached strategy"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            strategy1 = manager.get_strategy(BrowserType.PLAYWRIGHT)
            strategy2 = manager.get_strategy(BrowserType.PLAYWRIGHT)

            assert strategy1 is strategy2
            # Only called once due to caching
            mock_pw.assert_called_once()

    def test_get_strategy_closes_old_strategy(self):
        """Test that getting new strategy closes old one"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw, \
             patch("src.web.browser_strategy_manager.SeleniumStrategy") as mock_sel:
            mock_pw_instance = MagicMock()
            mock_pw.return_value = mock_pw_instance
            mock_sel_instance = MagicMock()
            mock_sel.return_value = mock_sel_instance

            manager = BrowserStrategyManager()
            strategy1 = manager.get_strategy(BrowserType.PLAYWRIGHT)
            strategy2 = manager.get_strategy(BrowserType.SELENIUM)

            mock_pw_instance.close.assert_called_once()
            assert strategy2 is mock_sel_instance

    def test_get_strategy_passes_kwargs(self):
        """Test that kwargs are passed to strategy constructor"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            kwargs = {"headless": True, "download_dir": "/tmp"}
            manager.get_strategy(BrowserType.PLAYWRIGHT, **kwargs)

            mock_pw.assert_called_once_with(**kwargs)

    def test_get_strategy_invalid_type(self):
        """Test getting strategy with invalid type"""
        # Create a mock BrowserType that's not SELENIUM or PLAYWRIGHT
        invalid_type = MagicMock()
        invalid_type.__str__ = lambda self: "invalid"

        manager = BrowserStrategyManager()

        with pytest.raises(BrowserStrategyError):
            manager.get_strategy(invalid_type)

    def test_get_strategy_uses_default_when_none(self):
        """Test that None uses default browser type"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            # None should use the default type
            strategy = manager.get_strategy(None)

            assert strategy is mock_instance

    def test_switch_strategy(self):
        """Test switching strategy"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw, \
             patch("src.web.browser_strategy_manager.SeleniumStrategy") as mock_sel:
            mock_pw_instance = MagicMock()
            mock_pw.return_value = mock_pw_instance
            mock_sel_instance = MagicMock()
            mock_sel.return_value = mock_sel_instance

            manager = BrowserStrategyManager()
            manager.get_strategy(BrowserType.PLAYWRIGHT)

            new_strategy = manager.switch_strategy(BrowserType.SELENIUM)

            assert new_strategy is mock_sel_instance
            mock_pw_instance.close.assert_called_once()

    def test_close(self):
        """Test closing manager"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            manager.get_strategy(BrowserType.PLAYWRIGHT)
            manager.close()

            mock_instance.close.assert_called_once()
            assert manager._current_strategy is None
            assert manager._current_type is None

    def test_close_with_exception(self):
        """Test close handles exceptions gracefully"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_instance.close.side_effect = Exception("Close error")
            mock_pw.return_value = mock_instance

            manager = BrowserStrategyManager()
            manager.get_strategy(BrowserType.PLAYWRIGHT)
            # Should not raise exception
            manager.close()

            assert manager._current_strategy is None
            assert manager._current_type is None

    def test_context_manager(self):
        """Test using manager as context manager"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            with BrowserStrategyManager() as manager:
                manager.get_strategy(BrowserType.PLAYWRIGHT)

            mock_instance.close.assert_called_once()

    def test_context_manager_with_exception(self):
        """Test context manager cleans up even with exception"""
        with patch("src.web.browser_strategy_manager.PlaywrightStrategy") as mock_pw:
            mock_instance = MagicMock()
            mock_pw.return_value = mock_instance

            try:
                with BrowserStrategyManager() as manager:
                    manager.get_strategy(BrowserType.PLAYWRIGHT)
                    raise ValueError("Test exception")
            except ValueError:
                pass

            mock_instance.close.assert_called_once()
