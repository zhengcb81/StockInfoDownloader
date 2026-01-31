"""
Web操作模块
提供WebDriver管理、反爬虫策略和网页抓取功能
"""

from .anti_crawler import (
    AntiCrawlerLevel,
    BehaviorSimulator,
    AdaptiveRateLimiter,
    CaptchaHandler,
    EnhancedAntiCrawler,
)
from .anti_crawler_py import AntiCrawlerStrategy
from .driver import WebDriverManager
from .scraper import WebScraper

__all__ = [
    "WebDriverManager",
    "AntiCrawlerStrategy",
    "WebScraper",
    "AntiCrawlerLevel",
    "BehaviorSimulator",
    "AdaptiveRateLimiter",
    "CaptchaHandler",
    "EnhancedAntiCrawler",
]
