#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试关键词匹配器的排除功能
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig

def test_keyword_matcher():
    """测试关键词匹配器"""
    print("=== 测试关键词匹配器 ===")

    # 测试数据：模拟config.json中的periodicReports配置
    test_config = KeywordConfig(
        allowed_keywords=None,
        exclude_keywords=["摘要", "英文版", "（英文版）"]
    )

    matcher = KeywordMatcher(test_config)

    # 测试文件名
    test_files = [
        "海康威视：2022年年度报告摘要.pdf",  # 应该被排除
        "海康威视：2022年年度报告.pdf",     # 应该通过
        "海康威视：2022年年度报告（英文版）.pdf",  # 应该被排除
        "海康威视：2022年年度报告英文版.pdf",  # 应该被排除
        "珂玛科技：2025年半年度报告摘要.pdf",  # 应该被排除
        "珂玛科技：2025年半年度报告.pdf",     # 应该通过
    ]

    print("\n--- 测试periodicReports配置 ---")
    for filename in test_files:
        result = matcher.matches(text=filename, title=filename)
        status = "通过" if result else "排除"
        print(f"{status}: {filename}")

    # 测试latestAnnouncement配置
    test_config2 = KeywordConfig(
        allowed_keywords=["招股说明书", "问询函"],
        exclude_keywords=None
    )

    matcher2 = KeywordMatcher(test_config2)

    print("\n--- 测试latestAnnouncement配置 ---")
    test_files2 = [
        "海康威视：招股说明书.pdf",           # 应该通过
        "海康威视：问询函回复.pdf",           # 应该通过
        "海康威视：2022年年度报告.pdf",       # 应该被排除
        "海康威视：2022年年度报告摘要.pdf",   # 应该被排除
    ]

    for filename in test_files2:
        result = matcher2.matches(text=filename, title=filename)
        status = "通过" if result else "排除"
        print(f"{status}: {filename}")

if __name__ == "__main__":
    test_keyword_matcher()