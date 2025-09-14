#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试DownloadServiceV2的排除关键词功能
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.downloader_v2 import DownloadServiceV2

def test_download_service_v2():
    """测试DownloadServiceV2的关键词匹配功能"""
    print("=== 测试DownloadServiceV2排除关键词功能 ===")

    # 创建DownloadServiceV2实例
    downloader = DownloadServiceV2(save_dir="test_downloads", browser_strategy="playwright")

    # 测试数据
    test_links = [
        {"text": "海康威视：2022年年度报告摘要", "should_match": False},
        {"text": "海康威视：2022年年度报告", "should_match": True},
        {"text": "海康威视：招股说明书", "should_match": True},
        {"text": "海康威视：问询函回复", "should_match": True},
    ]

    # 测试periodicReports页面配置（排除"摘要"）
    page_config = {
        "suffix": "periodicReports",
        "allowed_keywords": None,
        "excluded_keywords": ["摘要"]
    }

    print("\n--- 测试periodicReports页面配置 ---")
    for i, link in enumerate(test_links, 1):
        # 模拟_find_download_links方法的关键词匹配逻辑
        allowed_keywords = page_config.get('allowed_keywords')
        excluded_keywords = page_config.get('excluded_keywords')

        from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig
        keyword_config = KeywordConfig(
            allowed_keywords=allowed_keywords,
            exclude_keywords=excluded_keywords
        )
        keyword_matcher = KeywordMatcher(keyword_config)

        result = keyword_matcher.matches(text=link["text"], title=link["text"])
        status = "PASS" if result == link["should_match"] else "FAIL"
        print(f"{status} 测试 {i}: '{link['text']}'")
        print(f"     期望: {link['should_match']}, 实际: {result}")
        print()

    # 测试latestAnnouncement页面配置（只允许"招股说明书"、"问询函"）
    page_config = {
        "suffix": "latestAnnouncement",
        "allowed_keywords": ["招股说明书", "问询函"],
        "excluded_keywords": None
    }

    print("--- 测试latestAnnouncement页面配置 ---")
    for i, link in enumerate(test_links, 1):
        allowed_keywords = page_config.get('allowed_keywords')
        excluded_keywords = page_config.get('excluded_keywords')

        from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig
        keyword_config = KeywordConfig(
            allowed_keywords=allowed_keywords,
            exclude_keywords=excluded_keywords
        )
        keyword_matcher = KeywordMatcher(keyword_config)

        result = keyword_matcher.matches(text=link["text"], title=link["text"])
        # latestAnnouncement页面的期望结果
        expected_results = [False, False, True, True]  # 只有招股说明书和问询函应该匹配
        should_match = expected_results[i-1]

        status = "PASS" if result == should_match else "FAIL"
        print(f"{status} 测试 {i}: '{link['text']}'")
        print(f"     期望: {should_match}, 实际: {result}")
        print()

if __name__ == "__main__":
    test_download_service_v2()