"""
浏览器策略管理器
提供统一的浏览器策略选择和管理功能
"""

from enum import Enum
from typing import Optional, Union

from ..core.config import ConfigManager
from ..core.exceptions import BrowserStrategyError, ErrorCode, ErrorSeverity
from ..core.logger import get_logger
from .browser_strategy import BrowserAutomationStrategy
from .playwright_strategy import PlaywrightStrategy
from .selenium_strategy import SeleniumStrategy

logger = get_logger(__name__)


class BrowserType(Enum):
    """浏览器类型枚举"""

    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"


class BrowserStrategyManager:
    """浏览器策略管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化浏览器策略管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_manager = ConfigManager(config_file)
        self._current_strategy: Optional[BrowserAutomationStrategy] = None
        self._current_type: Optional[BrowserType] = None

        # 从配置获取默认浏览器类型
        self.default_browser_type = self.config_manager.get(
            "browser.strategy", "playwright"  # 默认使用Playwright
        ).lower()

        # 验证浏览器类型
        if self.default_browser_type not in [t.value for t in BrowserType]:
            logger.warning(
                f"未知的浏览器类型: {self.default_browser_type}, 使用默认的playwright"
            )
            self.default_browser_type = "playwright"

    def get_strategy(
        self, browser_type: Optional[Union[str, BrowserType]] = None, **kwargs
    ) -> BrowserAutomationStrategy:
        """
        获取浏览器策略实例

        Args:
            browser_type: 浏览器类型
            **kwargs: 策略初始化参数

        Returns:
            BrowserAutomationStrategy: 浏览器策略实例
        """
        if browser_type is None:
            browser_type = self.default_browser_type

        if isinstance(browser_type, str):
            browser_type = BrowserType(browser_type.lower())

        # 如果已经有相同类型的策略，直接返回
        if self._current_strategy is not None and self._current_type == browser_type:
            return self._current_strategy

        # 关闭旧策略
        if self._current_strategy is not None:
            try:
                self._current_strategy.close()
            except Exception as e:
                logger.warning(f"关闭旧浏览器策略失败: {e}")

        # 创建新策略
        try:
            if browser_type == BrowserType.PLAYWRIGHT:
                self._current_strategy = PlaywrightStrategy(**kwargs)
                self._current_type = BrowserType.PLAYWRIGHT
                logger.info("使用Playwright浏览器策略")

            elif browser_type == BrowserType.SELENIUM:
                self._current_strategy = SeleniumStrategy(**kwargs)
                self._current_type = BrowserType.SELENIUM
                logger.info("使用Selenium浏览器策略")

            else:
                raise BrowserStrategyError(
                    f"不支持的浏览器类型: {browser_type}",
                    error_code=ErrorCode.BROWSER_STRATEGY_ERROR,
                    severity=ErrorSeverity.ERROR,
                )

            return self._current_strategy

        except ImportError as e:
            logger.error(f"导入浏览器策略失败: {e}")
            # 如果Playwright不可用，降级到Selenium
            if browser_type == BrowserType.PLAYWRIGHT:
                logger.info("Playwright不可用，降级到Selenium策略")
                return self.get_strategy(BrowserType.SELENIUM, **kwargs)
            else:
                raise BrowserStrategyError(
                    f"无法初始化浏览器策略: {e}",
                    error_code=ErrorCode.BROWSER_STRATEGY_ERROR,
                    severity=ErrorSeverity.CRITICAL,
                )

    def get_current_strategy(self) -> Optional[BrowserAutomationStrategy]:
        """获取当前浏览器策略"""
        return self._current_strategy

    def get_current_type(self) -> Optional[BrowserType]:
        """获取当前浏览器类型"""
        return self._current_type

    def switch_strategy(
        self, browser_type: Union[str, BrowserType], **kwargs
    ) -> BrowserAutomationStrategy:
        """
        切换浏览器策略

        Args:
            browser_type: 新的浏览器类型
            **kwargs: 策略初始化参数

        Returns:
            BrowserAutomationStrategy: 新的浏览器策略实例
        """
        logger.info(f"切换浏览器策略: {self._current_type} -> {browser_type}")
        return self.get_strategy(browser_type, **kwargs)

    def close(self):
        """关闭当前浏览器策略"""
        if self._current_strategy is not None:
            try:
                self._current_strategy.close()
                logger.info("浏览器策略已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器策略失败: {e}")
            finally:
                self._current_strategy = None
                self._current_type = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
