#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试排除关键词功能
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.downloader_v2 import DownloadServiceV2 as DownloadService
from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig

def test_excluded_keywords():
    """测试排除关键词功能"""
    print("=== 测试排除关键词功能 ===")

    # 创建下载服务
    downloader = DownloadService(save_dir="downloads", mapping_file="stock_orgid_mapping.json", browser_strategy="playwright")

    # 测试用例
    test_cases = [
        # 定期报告页面 - 应该排除"摘要"
        {
            "text": "海康威视：2022年年度报告摘要",
            "allowed_keywords": None,
            "excluded_keywords": ["摘要"],
            "expected": False
        },
        {
            "text": "海康威视：2022年年度报告",
            "allowed_keywords": None,
            "excluded_keywords": ["摘要"],
            "expected": True
        },
        {
            "text": "海康威视：2023年第一季度报告",
            "allowed_keywords": None,
            "excluded_keywords": ["摘要"],
            "expected": True
        },
        # 最新公告页面 - 应该只包含"招股说明书"或"问询函"
        {
            "text": "海康威视：招股说明书",
            "allowed_keywords": ["招股说明书", "问询函"],
            "excluded_keywords": None,
            "expected": True
        },
        {
            "text": "海康威视：问询函回复",
            "allowed_keywords": ["招股说明书", "问询函"],
            "excluded_keywords": None,
            "expected": True
        },
        {
            "text": "海康威视：2025年第一季度报告",
            "allowed_keywords": ["招股说明书", "问询函"],
            "excluded_keywords": None,
            "expected": False
        },
        {
            "text": "海康威视：关于回购注销部分限制性股票的公告",
            "allowed_keywords": ["招股说明书", "问询函"],
            "excluded_keywords": None,
            "expected": False
        }
    ]

    print("\n--- 测试 KeywordMatcher ---")
    for i, case in enumerate(test_cases, 1):
        config = KeywordConfig(
            allowed_keywords=case["allowed_keywords"],
            exclude_keywords=case["excluded_keywords"]
        )
        matcher = KeywordMatcher(config)
        result = matcher.matches(text=case["text"], title=case["text"])
        status = "PASS" if result == case["expected"] else "FAIL"
        print(f"{status} 测试 {i}: '{case['text']}'")
        print(f"     允许关键词: {case['allowed_keywords']}")
        print(f"     排除关键词: {case['excluded_keywords']}")
        print(f"     期望: {case['expected']}, 实际: {result}")
        print()

    # 测试页面配置
    print("--- 测试页面配置 ---")
    pages = downloader.config.get('pages', [])
    for page in pages:
        if page.get('suffix') == 'periodicReports':
            print(f"periodicReports页面配置:")
            print(f"  允许关键词: {page.get('allowed_keywords')}")
            print(f"  排除关键词: {page.get('excluded_keywords')}")
            break

if __name__ == "__main__":
    test_excluded_keywords()