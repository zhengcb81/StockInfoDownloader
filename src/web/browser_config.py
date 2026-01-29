"""
浏览器配置管理模块
统一管理所有浏览器相关配置参数
"""

from typing import Any, Dict, List, Optional

from ..core.config import ConfigManager
from ..core.config_constants import ConfigConstants


class BrowserConfig:
    """浏览器配置管理类"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化浏览器配置

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()

    def get_browser_config(self) -> Dict[str, Any]:
        """
        获取完整的浏览器配置

        Returns:
            Dict[str, Any]: 浏览器配置字典
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
        获取是否使用无头模式

        Returns:
            bool: 是否使用无头模式
        """
        return self.config_manager.get("headless", True)

    def get_window_size(self) -> str:
        """
        获取窗口大小

        Returns:
            str: 窗口大小字符串，如 "1920,1080"
        """
        return self.config_manager.get("browser.window_size", "1920,1080")

    def get_page_load_strategy(self) -> str:
        """
        获取页面加载策略

        Returns:
            str: 页面加载策略
        """
        return self.config_manager.get("page_load_strategy", "eager")

    def get_user_agents(self) -> List[str]:
        """
        获取用户代理列表

        Returns:
            List[str]: 用户代理字符串列表
        """
        return self.config_manager.get(
            "browser.user_agents", ConfigConstants.USER_AGENTS
        )

    def get_browser_strategy(self) -> str:
        """
        获取浏览器策略

        Returns:
            str: 浏览器策略类型
        """
        return self.config_manager.get("browser.strategy", "playwright")

    def get_all_timeouts(self) -> Dict[str, int]:
        """
        获取所有超时设置

        Returns:
            Dict[str, int]: 超时设置字典
        """
        return {
            "page_load": self.get_timeout("page_load"),
            "element_wait": self.get_timeout("element_wait"),
            "download": self.get_timeout("download"),
            "script": self.get_timeout("script"),
        }

    def get_timeout(self, timeout_type: str) -> int:
        """
        获取指定类型的超时时间

        Args:
            timeout_type: 超时类型

        Returns:
            int: 超时时间（秒）
        """
        return self.config_manager.get(
            f"timeout.{timeout_type}", ConfigConstants.get_timeout(timeout_type)
        )

    def get_test_browser_config(self) -> Dict[str, Any]:
        """
        获取测试环境的浏览器配置

        Returns:
            Dict[str, Any]: 测试浏览器配置
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
        获取Selenium特定的选项配置

        Returns:
            Dict[str, Any]: Selenium选项配置
        """
        return {
            "headless": self.is_headless(),
            "window_size": self.get_window_size(),
            "page_load_strategy": self.get_page_load_strategy(),
            "user_agent": self.get_random_user_agent(),
        }

    def get_playwright_options(self) -> Dict[str, Any]:
        """
        获取Playwright特定的选项配置

        Returns:
            Dict[str, Any]: Playwright选项配置
        """
        return {
            "headless": self.is_headless(),
            "viewport": self._parse_window_size(),
            "user_agent": self.get_random_user_agent(),
        }

    def get_random_user_agent(self) -> str:
        """
        获取随机用户代理

        Returns:
            str: 随机用户代理字符串
        """
        import random

        user_agents = self.get_user_agents()
        return random.choice(user_agents)

    def _parse_window_size(self) -> Dict[str, int]:
        """
        解析窗口大小字符串

        Returns:
            Dict[str, int]: 视口尺寸
        """
        try:
            window_size = self.get_window_size()
            width, height = map(int, window_size.split(","))
            return {"width": width, "height": height}
        except (ValueError, AttributeError):
            return {"width": 1920, "height": 1080}

    def update_config(self, **kwargs) -> None:
        """
        更新浏览器配置

        Args:
            **kwargs: 配置键值对
        """
        for key, value in kwargs.items():
            if "." in key:
                # 支持嵌套配置，如 'browser.window_size'
                self.config_manager.set(key, value)
            else:
                # 顶级配置
                self.config_manager.set(key, value)

    def validate_config(self) -> List[str]:
        """
        验证浏览器配置的有效性

        Returns:
            List[str]: 错误消息列表，如果为空则配置有效
        """
        errors = []

        # 验证超时设置
        for timeout_type in ["page_load", "element_wait", "download", "script"]:
            timeout = self.get_timeout(timeout_type)
            if timeout <= 0:
                errors.append(f"Invalid timeout for {timeout_type}: {timeout}")

        # 验证窗口大小
        try:
            self._parse_window_size()
        except Exception:
            errors.append("Invalid window size format")

        # 验证用户代理
        if not self.get_user_agents():
            errors.append("No user agents configured")

        # 验证浏览器策略
        strategy = self.get_browser_strategy()
        if strategy not in ["selenium", "playwright"]:
            errors.append(f"Invalid browser strategy: {strategy}")

        return errors
