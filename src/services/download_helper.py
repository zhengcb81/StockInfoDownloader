#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
下载辅助器模块
提供基于不同浏览器策略的文件下载辅助功能
"""

from pathlib import Path

from ..core.logger import get_logger

logger = get_logger(__name__)


class BaseDownloadHelper:
    """下载辅助器基类"""

    def __init__(self, browser_strategy):
        """
        初始化下载辅助器

        Args:
            browser_strategy: 浏览器策略实例
        """
        self.browser_strategy = browser_strategy
        self.logger = logger

    def download_from_detail_page(
        self, url: str, save_path: str, timeout: int = 60
    ) -> bool:
        """
        从详情页下载文件

        Args:
            url: 详情页URL
            save_path: 文件保存路径
            timeout: 超时时间（秒）

        Returns:
            bool: 下载是否成功
        """
        raise NotImplementedError("子类必须实现此方法")


class PlaywrightDownloadHelper(BaseDownloadHelper):
    """Playwright下载辅助器"""

    def download_from_detail_page(
        self, url: str, save_path: str, timeout: int = 60
    ) -> bool:
        """
        使用Playwright从详情页下载文件

        Args:
            url: 详情页URL
            save_path: 文件保存路径
            timeout: 超时时间（秒）

        Returns:
            bool: 下载是否成功
        """
        try:
            # 确保保存目录存在
            save_dir = Path(save_path).parent
            save_dir.mkdir(parents=True, exist_ok=True)

            # 使用浏览器策略的download_file方法
            if hasattr(self.browser_strategy, "download_file"):
                success = self.browser_strategy.download_file(url, save_path, timeout)
                if success:
                    self.logger.info(f"Playwright下载成功: {save_path}")
                    return True
                else:
                    self.logger.error(f"Playwright下载失败: {url}")
                    return False
            else:
                self.logger.error("浏览器策略不支持download_file方法")
                return False

        except Exception as e:
            self.logger.error(f"Playwright下载异常: {str(e)}")
            return False


class SeleniumDownloadHelper(BaseDownloadHelper):
    """Selenium下载辅助器"""

    def __init__(self, browser_strategy, download_dir: str):
        """
        初始化Selenium下载辅助器

        Args:
            browser_strategy: 浏览器策略实例
            download_dir: 下载目录路径
        """
        super().__init__(browser_strategy)
        self.download_dir = download_dir

    def download_from_detail_page(
        self, url: str, save_path: str, timeout: int = 60
    ) -> bool:
        """
        使用Selenium从详情页下载文件

        Args:
            url: 详情页URL
            save_path: 文件保存路径
            timeout: 超时时间（秒）

        Returns:
            bool: 下载是否成功
        """
        try:
            # 确保保存目录存在
            save_dir = Path(save_path).parent
            save_dir.mkdir(parents=True, exist_ok=True)

            # 使用浏览器策略的download_file方法
            if hasattr(self.browser_strategy, "download_file"):
                success = self.browser_strategy.download_file(url, save_path, timeout)
                if success:
                    self.logger.info(f"Selenium下载成功: {save_path}")
                    return True
                else:
                    self.logger.error(f"Selenium下载失败: {url}")
                    return False
            else:
                self.logger.error("浏览器策略不支持download_file方法")
                return False

        except Exception as e:
            self.logger.error(f"Selenium下载异常: {str(e)}")
            return False
