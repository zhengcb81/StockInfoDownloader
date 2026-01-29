#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一下载器接口
定义所有下载器实现必须遵循的标准接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class DownloadRequest:
    """下载请求配置"""

    stock_code: str
    stock_name: Optional[str] = None
    org_id: Optional[str] = None
    suffix: Optional[str] = None
    allowed_keywords: Optional[List[str]] = None
    max_pages: int = 5
    delete_later: bool = False
    timeout_seconds: int = 180
    save_dir: Optional[Union[str, Path]] = None


@dataclass
class DownloadResult:
    """下载结果"""

    success: bool
    downloaded_files: List[str]
    total_files: int
    errors: List[str]
    duration_seconds: float
    metadata: Dict[str, Any]


@dataclass
class DownloadStatus:
    """下载状态"""

    is_running: bool
    current_page: int
    total_pages: int
    downloaded_count: int
    error_count: int
    last_error: Optional[str] = None


class IDownloader(ABC):
    """
    统一下载器接口
    所有下载器实现必须实现此接口
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化下载器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._status = DownloadStatus(
            is_running=False,
            current_page=0,
            total_pages=0,
            downloaded_count=0,
            error_count=0,
        )

    @abstractmethod
    def download_stock_pdfs(self, request: DownloadRequest) -> DownloadResult:
        """
        下载股票PDF文件

        Args:
            request: 下载请求配置

        Returns:
            DownloadResult: 下载结果
        """

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        配置下载器

        Args:
            config: 配置字典
        """

    def get_status(self) -> DownloadStatus:
        """
        获取当前下载状态

        Returns:
            DownloadStatus: 当前状态
        """
        return self._status

    @abstractmethod
    def cleanup(self) -> None:
        """
        清理资源
        """

    @abstractmethod
    def get_supported_browsers(self) -> List[str]:
        """
        获取支持的浏览器列表

        Returns:
            List[str]: 支持的浏览器名称
        """

    def validate_request(self, request: DownloadRequest) -> List[str]:
        """
        验证下载请求

        Args:
            request: 下载请求

        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        errors = []

        if not request.stock_code:
            errors.append("股票代码不能为空")

        if request.max_pages <= 0:
            errors.append("最大页数必须大于0")

        if request.timeout_seconds <= 0:
            errors.append("超时时间必须大于0")

        return errors


class IBrowserStrategy(ABC):
    """
    浏览器策略接口
    定义浏览器操作的统一接口
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化浏览器

        Returns:
            bool: 初始化是否成功
        """

    @abstractmethod
    def cleanup(self) -> None:
        """
        清理浏览器资源
        """

    def close(self) -> None:
        """
        关闭浏览器（cleanup 的别名）
        """
        self.cleanup()

    @abstractmethod
    def navigate(self, url: str) -> bool:
        """
        导航到指定页面

        Args:
            url: 目标URL

        Returns:
            bool: 导航是否成功
        """

    def navigate_to_page(self, url: str) -> bool:
        """兼容旧接口"""
        return self.navigate(url)

    @abstractmethod
    def restart(self) -> bool:
        """重启浏览器"""

    @abstractmethod
    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """
        查找页面元素

        Args:
            selector: 选择器字符串
            by: 选择策略 ('css' or 'xpath')

        Returns:
            List[Any]: 元素列表
        """

    @abstractmethod
    def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """
        等待元素出现

        Args:
            selector: CSS选择器
            timeout: 超时时间（秒）

        Returns:
            bool: 是否找到元素
        """

    @abstractmethod
    def execute_script(self, script: str) -> Any:
        """执行JavaScript脚本"""

    @abstractmethod
    def take_screenshot(self, path: str) -> bool:
        """截图"""

    @abstractmethod
    def download_file(self, url: str, save_path: str) -> bool:
        """下载文件"""

    @abstractmethod
    def go_to_next_page(self) -> bool:
        """翻到下一页"""

    @abstractmethod
    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """获取元素属性"""

    @abstractmethod
    def get_text(self, element: Any) -> str:
        """获取元素文本"""



class IAntiCrawlerStrategy(ABC):
    """
    反爬虫策略接口
    """

    @abstractmethod
    def before_request(self, request_info: Dict[str, Any]) -> None:
        """
        请求前的反爬虫处理
        """

    @abstractmethod
    def after_request(self, response_info: Dict[str, Any]) -> None:
        """
        请求后的反爬虫处理
        """

    @abstractmethod
    def should_retry(self, error: Exception) -> bool:
        """
        判断是否应该重试

        Args:
            error: 错误对象

        Returns:
            bool: 是否应该重试
        """
