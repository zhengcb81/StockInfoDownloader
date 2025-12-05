#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一下载器配置管理
集中管理所有下载器相关的配置选项
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
import logging

from src.core.logger import get_logger


@dataclass
class BrowserConfig:
    """浏览器配置"""
    strategy: str = "playwright"  # playwright, selenium
    headless: bool = False
    window_size: tuple = (1920, 1080)
    timeout: int = 30
    page_load_timeout: int = 60
    implicit_wait: int = 10

    # User Agent配置
    user_agent: Optional[str] = None
    user_agents: list = None

    # 代理配置
    proxy_enabled: bool = False
    proxy_host: Optional[str] = None
    proxy_port: int = 8080
    proxy_type: str = "http"

    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59"
            ]


@dataclass
class AntiCrawlerConfig:
    """反爬虫配置"""
    enabled: bool = True
    base_delay: float = 1.0
    random_delay_range: tuple = (0.5, 2.0)
    session_limit: int = 50
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

    # 模拟人类行为
    simulate_typing: bool = False
    simulate_mouse_movement: bool = False
    random_scrolling: bool = False

    # 请求头配置
    referer_enabled: bool = True
    custom_headers: Dict[str, str] = None

    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }


@dataclass
class DownloadConfig:
    """下载配置"""
    max_pages: int = 5
    timeout: int = 180
    download_delay: float = 0.5
    concurrent_downloads: int = 3
    chunk_size: int = 8192

    # 文件配置
    file_name_format: str = "{stock_name}_{date}_{description}.pdf"
    save_directory: str = "downloads"
    create_subdirs: bool = True
    delete_after_analysis: bool = False

    # 验证配置
    validate_downloads: bool = True
    min_file_size: int = 1024  # 1KB
    allowed_extensions: list = None

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    log_to_file: bool = True
    log_file: str = "logs/downloader.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True

    # 性能日志
    enable_performance_logging: bool = True
    performance_log_file: str = "logs/performance.log"

    # 错误日志
    enable_error_tracking: bool = True
    error_log_file: str = "logs/errors.log"


class DownloaderConfigManager:
    """下载器配置管理器"""

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        self.logger = get_logger("DownloaderConfigManager")
        self.config_file = Path(config_file) if config_file else Path("config/downloader_config.json")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # 默认配置
        self.browser = BrowserConfig()
        self.anti_crawler = AntiCrawlerConfig()
        self.download = DownloadConfig()
        self.logging = LoggingConfig()

        # 加载配置
        self.load_config()

    def load_config(self) -> None:
        """从文件加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 更新配置对象
                if 'browser' in data:
                    self.browser = BrowserConfig(**data['browser'])
                if 'anti_crawler' in data:
                    self.anti_crawler = AntiCrawlerConfig(**data['anti_crawler'])
                if 'download' in data:
                    self.download = DownloadConfig(**data['download'])
                if 'logging' in data:
                    self.logging = LoggingConfig(**data['logging'])

                self.logger.info(f"配置已从 {self.config_file} 加载")
            else:
                self.logger.info("配置文件不存在，使用默认配置")
                self.save_config()  # 保存默认配置

        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            self.logger.warning("使用默认配置")

    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            config_data = {
                'browser': asdict(self.browser),
                'anti_crawler': asdict(self.anti_crawler),
                'download': asdict(self.download),
                'logging': asdict(self.logging)
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"配置已保存到 {self.config_file}")

        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")

    def get_browser_config(self) -> Dict[str, Any]:
        """获取浏览器配置"""
        return asdict(self.browser)

    def get_anti_crawler_config(self) -> Dict[str, Any]:
        """获取反爬虫配置"""
        return asdict(self.anti_crawler)

    def get_download_config(self) -> Dict[str, Any]:
        """获取下载配置"""
        return asdict(self.download)

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return asdict(self.logging)

    def update_browser_config(self, **kwargs) -> None:
        """更新浏览器配置"""
        for key, value in kwargs.items():
            if hasattr(self.browser, key):
                setattr(self.browser, key, value)
        self.save_config()

    def update_anti_crawler_config(self, **kwargs) -> None:
        """更新反爬虫配置"""
        for key, value in kwargs.items():
            if hasattr(self.anti_crawler, key):
                setattr(self.anti_crawler, key, value)
        self.save_config()

    def update_download_config(self, **kwargs) -> None:
        """更新下载配置"""
        for key, value in kwargs.items():
            if hasattr(self.download, key):
                setattr(self.download, key, value)
        self.save_config()

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            'browser': asdict(self.browser),
            'anti_crawler': asdict(self.anti_crawler),
            'download': asdict(self.download),
            'logging': asdict(self.logging)
        }

    def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        self.browser = BrowserConfig()
        self.anti_crawler = AntiCrawlerConfig()
        self.download = DownloadConfig()
        self.logging = LoggingConfig()
        self.save_config()
        self.logger.info("配置已重置为默认值")

    def validate_config(self) -> bool:
        """验证配置有效性"""
        try:
            # 验证浏览器配置
            if self.browser.strategy not in ['playwright', 'selenium']:
                raise ValueError("浏览器策略必须是 'playwright' 或 'selenium'")

            if self.browser.timeout <= 0:
                raise ValueError("超时时间必须大于0")

            # 验证下载配置
            if self.download.max_pages <= 0:
                raise ValueError("最大页数必须大于0")

            if self.download.timeout <= 0:
                raise ValueError("下载超时时间必须大于0")

            # 验证反爬虫配置
            if self.anti_crawler.base_delay < 0:
                raise ValueError("基础延迟不能为负数")

            # 验证日志配置
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if self.logging.level not in valid_log_levels:
                raise ValueError(f"日志级别必须是: {valid_log_levels}")

            return True

        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False

    def export_config(self, export_file: Union[str, Path]) -> None:
        """导出配置到指定文件"""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            config_data = self.get_all_config()
            config_data['export_info'] = {
                'timestamp': self._get_timestamp(),
                'version': '1.0',
                'source': self.config_file.name
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"配置已导出到: {export_path}")

        except Exception as e:
            self.logger.error(f"导出配置失败: {e}")

    def import_config(self, import_file: Union[str, Path]) -> None:
        """从指定文件导入配置"""
        try:
            import_path = Path(import_file)
            if not import_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {import_path}")

            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 移除导出信息
            data.pop('export_info', None)

            # 更新配置
            if 'browser' in data:
                self.browser = BrowserConfig(**data['browser'])
            if 'anti_crawler' in data:
                self.anti_crawler = AntiCrawlerConfig(**data['anti_crawler'])
            if 'download' in data:
                self.download = DownloadConfig(**data['download'])
            if 'logging' in data:
                self.logging = LoggingConfig(**data['logging'])

            # 验证并保存
            if self.validate_config():
                self.save_config()
                self.logger.info(f"配置已从 {import_path} 导入")
            else:
                raise ValueError("导入的配置验证失败")

        except Exception as e:
            self.logger.error(f"导入配置失败: {e}")

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_environment_overrides(self) -> Dict[str, Any]:
        """获取环境变量覆盖的配置"""
        overrides = {}

        # 浏览器策略覆盖
        browser_strategy = os.getenv('DOWNLOADER_BROWSER_STRATEGY')
        if browser_strategy:
            overrides['browser_strategy'] = browser_strategy

        # 超时覆盖
        timeout = os.getenv('DOWNLOADER_TIMEOUT')
        if timeout:
            try:
                overrides['timeout'] = int(timeout)
            except ValueError:
                pass

        # 最大页数覆盖
        max_pages = os.getenv('DOWNLOADER_MAX_PAGES')
        if max_pages:
            try:
                overrides['max_pages'] = int(max_pages)
            except ValueError:
                pass

        # 反爬虫开关
        anti_crawler = os.getenv('DOWNLOADER_ANTI_CRAWLER')
        if anti_crawler:
            overrides['anti_crawler_enabled'] = anti_crawler.lower() in ('true', '1', 'yes')

        return overrides


# 全局配置管理器实例
config_manager = DownloaderConfigManager()