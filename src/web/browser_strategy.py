"""
浏览器自动化策略模式接口
提供统一的浏览器自动化接口，支持多种框架（Selenium, Playwright）
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Any, Dict
from pathlib import Path
import logging

from ..core.logger import get_logger
from ..core.exceptions import (
    WebDriverError, WebDriverInitError, WebDriverTimeoutError, WebDriverCrashError,
    ErrorCode, ErrorSeverity, RecoveryStrategy, with_error_handling
)

logger = get_logger(__name__)


class BrowserAutomationStrategy(ABC):
    """浏览器自动化策略抽象基类"""
    
    @abstractmethod
    def __init__(self, headless: bool = True, download_dir: Optional[str] = None, 
                 config: Optional[Dict[str, Any]] = None):
        """初始化浏览器自动化策略"""
        pass
    
    @abstractmethod
    def create_driver(self) -> Any:
        """创建浏览器驱动实例"""
        pass
    
    @abstractmethod
    def get_driver(self) -> Any:
        """获取当前驱动实例"""
        pass
    
    @abstractmethod
    def navigate(self, url: str) -> bool:
        """导航到指定URL"""
        pass
    
    @abstractmethod
    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """查找元素"""
        pass
    
    @abstractmethod
    def find_element(self, selector: str, by: str = "css") -> Optional[Any]:
        """查找单个元素"""
        pass
    
    @abstractmethod
    def click(self, element: Any) -> bool:
        """点击元素"""
        pass
    
    @abstractmethod
    def get_text(self, element: Any) -> str:
        """获取元素文本"""
        pass
    
    @abstractmethod
    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """获取元素属性"""
        pass
    
    @abstractmethod
    def execute_script(self, script: str, *args) -> Any:
        """执行JavaScript脚本"""
        pass
    
    @abstractmethod
    def wait_for_element(self, selector: str, timeout: int = 10, 
                        by: str = "css", condition: str = "visible") -> bool:
        """等待元素出现"""
        pass
    
    @abstractmethod
    def get_page_source(self) -> str:
        """获取页面源代码"""
        pass
    
    @abstractmethod
    def get_current_url(self) -> str:
        """获取当前URL"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭浏览器"""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """检查浏览器是否健康"""
        pass
    
    @abstractmethod
    def restart(self) -> bool:
        """重启浏览器"""
        pass
    
    @abstractmethod
    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """截取屏幕截图"""
        pass
    
    @abstractmethod
    def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
        """
        下载文件到指定路径

        Args:
            url: 要下载的URL
            save_path: 文件保存路径
            timeout: 超时时间（秒）

        Returns:
            bool: 下载是否成功
        """
        pass

    @abstractmethod
    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        跳转到下一页

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功跳转
        """
        pass

    @abstractmethod
    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """
        跳转到指定页码

        Args:
            page_number: 目标页码
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功跳转
        """
        pass

    @abstractmethod
    def has_next_page(self, timeout: int = 5) -> bool:
        """
        检查是否有下一页

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否有下一页
        """
        pass


class BrowserStrategyFactory:
    """浏览器策略工厂"""
    
    @staticmethod
    def create_strategy(strategy_type: str = "selenium", **kwargs) -> BrowserAutomationStrategy:
        """
        创建浏览器自动化策略实例
        
        Args:
            strategy_type: 策略类型，支持 "selenium" 或 "playwright"
            **kwargs: 传递给策略构造函数的参数
            
        Returns:
            BrowserAutomationStrategy: 浏览器自动化策略实例
        """
        if strategy_type.lower() == "selenium":
            from .selenium_strategy import SeleniumStrategy
            return SeleniumStrategy(**kwargs)
        elif strategy_type.lower() == "playwright":
            from .playwright_strategy import PlaywrightStrategy
            return PlaywrightStrategy(**kwargs)
        else:
            raise ValueError(f"不支持的浏览器策略类型: {strategy_type}")


# 向后兼容性别名
BrowserStrategy = BrowserAutomationStrategy