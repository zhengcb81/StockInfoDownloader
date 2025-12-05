#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
遗留下载器适配器
为现有代码提供向后兼容的接口
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from src.interfaces.downloader_interface import (
    DownloadRequest,
    DownloadResult,
    DownloadStatus
)
from src.services.unified_downloader import UnifiedDownloader
from src.core.logger import get_logger


class CninfoDownloaderAdapter:
    """
    CninfoDownloader 适配器
    为旧的 CninfoDownloader 类提供兼容接口
    """

    def __init__(self, save_dir: Optional[str] = None, **kwargs):
        """
        初始化适配器

        Args:
            save_dir: 保存目录
            **kwargs: 其他配置参数
        """
        self.logger = get_logger("CninfoDownloaderAdapter")

        # 创建统一下载器
        config = {'save_directory': save_dir, **kwargs}
        self._unified_downloader = UnifiedDownloader(config)

        # 为了兼容性，保留旧的方法签名
        self.save_dir = save_dir or "downloads"

        self.logger.info("CninfoDownloader 适配器初始化完成")

    def download_stock_pdfs(
        self,
        stock_code: str,
        target_pages: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        下载股票PDF文件 (兼容旧接口)

        Args:
            stock_code: 股票代码
            target_pages: 目标页数
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 兼容旧格式的结果
        """
        try:
            # 创建新的请求对象
            request = DownloadRequest(
                stock_code=stock_code,
                max_pages=target_pages,
                save_dir=self.save_dir,
                **kwargs
            )

            # 使用统一下载器执行下载
            result = self._unified_downloader.download_stock_pdfs(request)

            # 转换为旧格式返回
            return {
                'success': result.success,
                'downloaded_files': result.downloaded_files,
                'total_files': result.total_files,
                'errors': result.errors,
                'duration_seconds': result.duration_seconds,
                'metadata': result.metadata
            }

        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            return {
                'success': False,
                'downloaded_files': [],
                'total_files': 0,
                'errors': [str(e)],
                'duration_seconds': 0,
                'metadata': {}
            }

    # 保留一些可能有用的旧方法
    def cleanup(self) -> None:
        """清理资源"""
        if self._unified_downloader:
            self._unified_downloader.cleanup()

    def configure(self, config: Dict[str, Any]) -> None:
        """配置下载器"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


class DownloadServiceV1Adapter:
    """
    DownloadService (v1) 适配器
    为旧版本的 DownloadService 类提供兼容接口
    """

    def __init__(self, save_dir: Optional[str] = None, **kwargs):
        """
        初始化适配器

        Args:
            save_dir: 保存目录
            **kwargs: 其他配置参数
        """
        self.logger = get_logger("DownloadServiceV1Adapter")

        # 创建统一下载器
        config = {'save_directory': save_dir, **kwargs}
        self._unified_downloader = UnifiedDownloader(config)

        # 为了兼容性，保留旧的方法签名
        self.save_dir = save_dir or "downloads"

        self.logger.info("DownloadServiceV1 适配器初始化完成")

    def download_stock_pdfs(
        self,
        stock_code: str,
        max_retries: int = 3,
        **kwargs
    ) -> DownloadResult:
        """
        下载股票PDF文件 (兼容旧接口)

        Args:
            stock_code: 股票代码
            max_retries: 最大重试次数
            **kwargs: 其他参数

        Returns:
            DownloadResult: 下载结果
        """
        try:
            # 创建新的请求对象
            request = DownloadRequest(
                stock_code=stock_code,
                max_pages=kwargs.get('max_pages', 5),
                save_dir=self.save_dir,
                timeout_seconds=kwargs.get('timeout', 180),
                **kwargs
            )

            # 设置重试次数
            self._unified_downloader.config['retry_count'] = max_retries

            # 使用统一下载器执行下载
            result = self._unified_downloader.download_stock_pdfs(request)

            return result

        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            return DownloadResult(
                success=False,
                downloaded_files=[],
                total_files=0,
                errors=[str(e)],
                duration_seconds=0,
                metadata={'adapter_error': str(e)}
            )

    def get_status(self) -> DownloadStatus:
        """获取下载状态"""
        return self._unified_downloader.get_status()

    def configure(self, config: Dict[str, Any]) -> None:
        """配置下载器"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


class DownloadServiceV2Adapter:
    """
    DownloadServiceV2 适配器
    为 DownloadServiceV2 类提供兼容接口
    """

    def __init__(self, browser_strategy: str = "playwright", **kwargs):
        """
        初始化适配器

        Args:
            browser_strategy: 浏览器策略
            **kwargs: 其他配置参数
        """
        self.logger = get_logger("DownloadServiceV2Adapter")

        # 创建统一下载器
        config = {'browser_strategy': browser_strategy, **kwargs}
        self._unified_downloader = UnifiedDownloader(config)

        # 为了兼容性，保留旧的方法签名
        self.browser_strategy = browser_strategy

        self.logger.info(f"DownloadServiceV2 适配器初始化完成，使用策略: {browser_strategy}")

    def download_stock_pdfs(
        self,
        stock_code: str,
        max_pages: int = 5,
        timeout_seconds: int = 180,
        **kwargs
    ) -> DownloadResult:
        """
        下载股票PDF文件 (兼容旧接口)

        Args:
            stock_code: 股票代码
            max_pages: 最大页数
            timeout_seconds: 超时时间
            **kwargs: 其他参数

        Returns:
            DownloadResult: 下载结果
        """
        try:
            # 创建新的请求对象
            request = DownloadRequest(
                stock_code=stock_code,
                max_pages=max_pages,
                timeout_seconds=timeout_seconds,
                save_dir=kwargs.get('save_dir', "downloads"),
                **kwargs
            )

            # 使用统一下载器执行下载
            result = self._unified_downloader.download_stock_pdfs(request)

            return result

        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            return DownloadResult(
                success=False,
                downloaded_files=[],
                total_files=0,
                errors=[str(e)],
                duration_seconds=0,
                metadata={'adapter_error': str(e)}
            )

    def get_status(self) -> DownloadStatus:
        """获取下载状态"""
        return self._unified_downloader.get_status()

    def configure(self, config: Dict[str, Any]) -> None:
        """配置下载器"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


class RefactoredDownloaderAdapter:
    """
    RefactoredDownloader 适配器
    为 RefactoredDownloader 类提供兼容接口
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, save_dir: Optional[str] = None, **kwargs):
        """
        初始化适配器

        Args:
            config: 配置字典
            save_dir: 保存目录（向后兼容）
            **kwargs: 其他参数
        """
        self.logger = get_logger("RefactoredDownloaderAdapter")

        # 合并配置参数
        merged_config = config or {}
        if save_dir:
            merged_config['save_directory'] = save_dir
        merged_config.update(kwargs)

        # 创建统一下载器
        self._unified_downloader = UnifiedDownloader(merged_config)

        self.logger.info("RefactoredDownloader 适配器初始化完成")

    def download_stock_pdfs(
        self,
        stock_code: str,
        stock_name: str,
        suffix: str,
        allowed_keywords: List[str],
        max_pages: int = 5,
        **kwargs
    ) -> DownloadResult:
        """
        下载股票PDF文件 (兼容旧接口)

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            suffix: 后缀
            allowed_keywords: 允许的关键词
            max_pages: 最大页数
            **kwargs: 其他参数

        Returns:
            DownloadResult: 下载结果
        """
        try:
            # 创建新的请求对象
            request = DownloadRequest(
                stock_code=stock_code,
                stock_name=stock_name,
                suffix=suffix,
                allowed_keywords=allowed_keywords,
                max_pages=max_pages,
                save_dir=kwargs.get('save_dir', "downloads"),
                **kwargs
            )

            # 使用统一下载器执行下载
            result = self._unified_downloader.download_stock_pdfs(request)

            return result

        except Exception as e:
            self.logger.error(f"下载失败: {e}")
            return DownloadResult(
                success=False,
                downloaded_files=[],
                total_files=0,
                errors=[str(e)],
                duration_seconds=0,
                metadata={'adapter_error': str(e)}
            )

    def get_status(self) -> DownloadStatus:
        """获取下载状态"""
        return self._unified_downloader.get_status()

    def configure(self, config: Dict[str, Any]) -> None:
        """配置下载器"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


def create_legacy_adapter(class_name: str, **kwargs) -> Any:
    """
    创建遗留下载器适配器的工厂函数

    Args:
        class_name: 类名称
        **kwargs: 构造参数

    Returns:
        Any: 适配器实例
    """
    adapters = {
        'CninfoDownloader': CninfoDownloaderAdapter,
        'DownloadService': DownloadServiceV1Adapter,
        'DownloadServiceV2': DownloadServiceV2Adapter,
        'RefactoredDownloader': RefactoredDownloaderAdapter
    }

    adapter_class = adapters.get(class_name)
    if not adapter_class:
        raise ValueError(f"不支持的下载器类型: {class_name}")

    return adapter_class(**kwargs)


# 为了最大兼容性，创建一个通用的兼容包装器
class UniversalDownloaderWrapper:
    """
    通用下载器包装器
    可以根据参数自动选择合适的适配器
    """

    def __init__(self, downloader_type: str = "auto", **kwargs):
        """
        初始化通用包装器

        Args:
            downloader_type: 下载器类型，"auto"表示自动选择
            **kwargs: 构造参数
        """
        self.logger = get_logger("UniversalDownloaderWrapper")

        if downloader_type == "auto":
            # 自动检测应该使用哪个适配器
            if 'browser_strategy' in kwargs:
                self._downloader = DownloadServiceV2Adapter(**kwargs)
            elif 'max_retries' in kwargs:
                self._downloader = DownloadServiceV1Adapter(**kwargs)
            elif 'allowed_keywords' in kwargs:
                self._downloader = RefactoredDownloaderAdapter(**kwargs)
            else:
                # 默认使用 DownloadServiceV2
                self._downloader = DownloadServiceV2Adapter(**kwargs)
        else:
            # 使用指定的适配器
            self._downloader = create_legacy_adapter(downloader_type, **kwargs)

        self.logger.info(f"通用包装器初始化完成，使用类型: {downloader_type}")

    def __getattr__(self, name: str):
        """
        委托所有未定义的方法到内部下载器
        """
        return getattr(self._downloader, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self._downloader, 'cleanup'):
            self._downloader.cleanup()