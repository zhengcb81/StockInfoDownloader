#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试关键词匹配功能
"""

import sys
import json
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.downloader_v2 import DownloadServiceV2 as DownloadService
from src.core.config import ConfigManager

def test_keyword_matching():
    """测试关键词匹配功能"""
    print("=== 测试关键词匹配功能 ===")

    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.load_config("config.json")

    # 创建下载服务
    downloader = DownloadService(save_dir="downloads", mapping_file="stock_orgid_mapping.json", browser_strategy="playwright")

    # 测试关键词匹配方法
    test_cases = [
        ("海康威视：2017年年度报告.PDF", ["招股说明书", "问询函"], False),
        ("海康威视：招股说明书.PDF", ["招股说明书", "问询函"], True),
        ("海康威视：问询函回复.PDF", ["招股说明书", "问询函"], True),
        ("海康威视：2018年年度报告.PDF", ["招股说明书", "问询函"], False),
        ("海康威视：首次公开发行招股说明书.PDF", ["招股说明书", "问询函"], True),
        ("海康威视：2018年10月22日投资者关系活动记录表.PDF", ["招股说明书", "问询函"], False),
    ]

    print("\n--- 测试 _matches_keywords 方法 ---")
    for text, keywords, expected in test_cases:
        result = downloader._matches_keywords(text, keywords)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status} 文本: '{text[:30]}...' 关键词: {keywords} 期望: {expected} 实际: {result}")

    print("\n--- 检查现有配置 ---")
    pages = config.get('pages', [])
    for page in pages:
        if page.get('suffix') == 'latestAnnouncement':
            print(f"latestAnnouncement页面配置:")
            print(f"  允许的关键词: {page.get('allowed_keywords')}")
            print(f"  排除的关键词: {page.get('excluded_keywords')}")
            break

    print("\n--- 检查公司配置 ---")
    companies = config.get('companies', [])
    for company in companies:
        if company.get('stock_code') == '002415':
            print(f"海康威视配置:")
            print(f"  自定义页面: {company.get('custom_pages')}")
            break

if __name__ == "__main__":
    test_keyword_matching()