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

# 导入 BrowserStrategy 以避免循环导入
from src.web.browser_strategy import BrowserStrategy


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
    reverse_order: bool = False  # 是否从最后一页开始（用于latestAnnouncement）


@dataclass
class DownloadResult:
    """下载结果"""

    success: bool
    downloaded_files: List[str]
    total_files: int
    errors: List[str]
    duration_seconds: float
    metadata: Dict[str, Any]
    # 行为验证字段 (E2E 测试用)
    skipped_files: List[str] = None  # type: ignore[assignment]  # 跳过的已存在文件
    pages_traversed: int = 0  # 实际遍历的页数

    def __post_init__(self) -> None:
        if self.skipped_files is None:
            self.skipped_files = []


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


class IBrowserStrategy(BrowserStrategy):
    """
    浏览器策略接口
    定义浏览器操作的统一接口

    此接口继承自 BrowserStrategy 以保持向后兼容。
    所有方法签名与 BrowserStrategy 一致。
    """

    # 所有方法都从 BrowserStrategy 继承，无需重新定义
    pass


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
