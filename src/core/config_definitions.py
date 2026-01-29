#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置定义模块
包含所有配置相关的 Dataclass 定义
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

@dataclass
class BrowserConfig:
    """浏览器配置"""
    strategy: str = "playwright"  # playwright, selenium
    headless: bool = True # 注意：原config.py默认为True，downloader_config默认为False，统一为True
    window_size: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    timeout: int = 30
    page_load_timeout: int = 60
    implicit_wait: int = 10
    user_agent: Optional[str] = None
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59",
    ])
    proxy_enabled: bool = False
    proxy_host: Optional[str] = None
    proxy_port: int = 8080
    proxy_type: str = "http"

@dataclass
class AntiCrawlerConfig:
    """反爬虫配置"""
    enabled: bool = True
    base_delay: float = 1.0
    random_delay_range: tuple = (0.5, 2.0)
    session_limit: int = 50
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    simulate_typing: bool = False
    simulate_mouse_movement: bool = False
    random_scrolling: bool = False
    referer_enabled: bool = True
    custom_headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })

@dataclass
class DownloadConfig:
    """下载配置"""
    max_pages: int = 5
    timeout: int = 180
    download_delay: float = 0.5
    concurrent_downloads: int = 3
    chunk_size: int = 8192
    file_name_format: str = "{stock_name}_{date}_{description}.pdf"
    save_directory: str = "downloads"
    create_subdirs: bool = True
    delete_after_analysis: bool = False
    validate_downloads: bool = True
    min_file_size: int = 1024
    allowed_extensions: List[str] = field(default_factory=lambda: [".pdf", ".doc", ".docx", ".xls", ".xlsx"])

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    log_to_file: bool = True
    log_file: str = "logs/downloader.log"
    max_file_size: int = 10 * 1024 * 1024
    backup_count: int = 5
    console_output: bool = True
    enable_performance_logging: bool = True
    performance_log_file: str = "logs/performance.log"
    enable_error_tracking: bool = True
    error_log_file: str = "logs/errors.log"

@dataclass
class GlobalConfig:
    """全局配置聚合"""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    anti_crawler: AntiCrawlerConfig = field(default_factory=AntiCrawlerConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    companies: List[Dict[str, Any]] = field(default_factory=list)
    
    # 兼容字段，用于直接存储未分类的配置
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        base = asdict(self)
        extra = base.pop("extra", {})
        base.update(extra)
        return base
