#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Anti-crawler protection package.
Provides comprehensive protection against bot detection systems.
"""

from src.web.anti_crawler.types import (
    FingerprintType,
    BehaviorPattern,
    AntiCrawlerLevel,
    FingerprintProfile,
)
from src.web.anti_crawler.behavior import BehaviorSimulator
from src.web.anti_crawler.rate_limiter import AdaptiveRateLimiter
from src.web.anti_crawler.captcha import CaptchaHandler
from src.web.anti_crawler.core import EnhancedAntiCrawler

__all__ = [
    # Types
    "FingerprintType",
    "BehaviorPattern",
    "AntiCrawlerLevel",
    "FingerprintProfile",
    # Components
    "BehaviorSimulator",
    "AdaptiveRateLimiter",
    "CaptchaHandler",
    # Main class
    "EnhancedAntiCrawler",
]
