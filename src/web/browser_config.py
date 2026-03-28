"""
Browser Configuration Management Module
Unified management of all browser-related configuration parameters.
"""

from typing import Any, Dict, List, Optional, cast

from ..core.config import ConfigManager
from ..core.config_constants import ConfigConstants


class BrowserConfig:
    """Browser configuration management class"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize browser configuration.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()

    def get_browser_config(self) -> Dict[str, Any]:
        """
        Get complete browser configuration.

        Returns:
            Dict[str, Any]: Browser configuration dictionary
        """
        return {
            "headless": self.is_headless(),
            "window_size": self.get_window_size(),
            "page_load_strategy": self.get_page_load_strategy(),
            "user_agents": self.get_user_agents(),
            "strategy": self.get_browser_strategy(),
            "timeouts": self.get_all_timeouts(),
        }

    def is_headless(self) -> bool:
        """
        Get whether to use headless mode.

        Returns:
            bool: Whether to use headless mode
        """
        return cast(bool, self.config_manager.get("headless", True))

    def get_window_size(self) -> str:
        """
        Get window size.

        Returns:
            str: Window size string, e.g. "1920,1080"
        """
        return cast(str, self.config_manager.get("browser.window_size", "1920,1080"))

    def get_page_load_strategy(self) -> str:
        """
        Get page load strategy.

        Returns:
            str: Page load strategy
        """
        return cast(str, self.config_manager.get("page_load_strategy", "eager"))

    def get_user_agents(self) -> List[str]:
        """
        Get user agent list.

        Returns:
            List[str]: User agent string list
        """
        return cast(List[str], self.config_manager.get(
            "browser.user_agents", ConfigConstants.USER_AGENTS
        ))

    def get_browser_strategy(self) -> str:
        """
        Get browser strategy.

        Returns:
            str: Browser strategy type
        """
        return cast(str, self.config_manager.get("browser.strategy", "playwright"))

    def get_all_timeouts(self) -> Dict[str, int]:
        """
        Get all timeout settings.

        Returns:
            Dict[str, int]: Timeout settings dictionary
        """
        return {
            "page_load": self.get_timeout("page_load"),
            "element_wait": self.get_timeout("element_wait"),
            "download": self.get_timeout("download"),
            "script": self.get_timeout("script"),
        }

    def get_timeout(self, timeout_type: str) -> int:
        """
        Get timeout for specified type.

        Args:
            timeout_type: Timeout type

        Returns:
            int: Timeout in seconds
        """
        return cast(int, self.config_manager.get(
            f"timeout.{timeout_type}", ConfigConstants.get_timeout(timeout_type)
        ))

    def get_test_browser_config(self) -> Dict[str, Any]:
        """
        Get browser configuration for test environment.

        Returns:
            Dict[str, Any]: Test browser configuration
        """
        return {
            "headless": self.config_manager.get_test_config(
                "test_environment.headless", False
            ),
            "page_load_timeout": self.config_manager.get_test_timeout("page_load"),
            "element_wait_timeout": self.config_manager.get_test_timeout(
                "element_wait"
            ),
            "download_timeout": self.config_manager.get_test_timeout("download"),
            "window_size": self.get_window_size(),
            "user_agents": self.get_user_agents(),
            "debug_mode": self.config_manager.get_test_config(
                "test_environment.debug_mode", True
            ),
        }

    def get_selenium_options(self) -> Dict[str, Any]:
        """
        Get Selenium-specific option configuration.

        Returns:
            Dict[str, Any]: Selenium options configuration
        """
        return {
            "headless": self.is_headless(),
            "window_size": self.get_window_size(),
            "page_load_strategy": self.get_page_load_strategy(),
            "user_agent": self.get_random_user_agent(),
        }

    def get_playwright_options(self) -> Dict[str, Any]:
        """
        Get Playwright-specific option configuration.

        Returns:
            Dict[str, Any]: Playwright options configuration
        """
        return {
            "headless": self.is_headless(),
            "viewport": self._parse_window_size(),
            "user_agent": self.get_random_user_agent(),
        }

    def get_random_user_agent(self) -> str:
        """
        Get random user agent.

        Returns:
            str: Random user agent string
        """
        import random

        user_agents = self.get_user_agents()
        return random.choice(user_agents)

    def _parse_window_size(self) -> Dict[str, int]:
        """
        Parse window size string.

        Returns:
            Dict[str, int]: Viewport dimensions
        """
        try:
            window_size = self.get_window_size()
            width, height = map(int, window_size.split(","))
            return {"width": width, "height": height}
        except (ValueError, AttributeError):
            return {"width": 1920, "height": 1080}

    def update_config(self, **kwargs) -> None:
        """
        Update browser configuration.

        Args:
            **kwargs: Configuration key-value pairs
        """
        for key, value in kwargs.items():
            if "." in key:
                # Support nested config, e.g. 'browser.window_size'
                self.config_manager.set(key, value)
            else:
                # Top-level config
                self.config_manager.set(key, value)

    def validate_config(self) -> List[str]:
        """
        Validate browser configuration.

        Returns:
            List[str]: Error message list, empty if configuration is valid
        """
        errors = []

        # Validate timeout settings
        for timeout_type in ["page_load", "element_wait", "download", "script"]:
            timeout = self.get_timeout(timeout_type)
            if timeout <= 0:
                errors.append(f"Invalid timeout for {timeout_type}: {timeout}")

        # Validate window size
        try:
            self._parse_window_size()
        except Exception:
            errors.append("Invalid window size format")

        # Validate user agents
        if not self.get_user_agents():
            errors.append("No user agents configured")

        # Validate browser strategy
        strategy = self.get_browser_strategy()
        if strategy not in ["selenium", "playwright"]:
            errors.append(f"Invalid browser strategy: {strategy}")

        return errors
