#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试单个页面的下载，用于调试关键词匹配问题
"""

import sys
import time
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.downloader_v2 import DownloadServiceV2 as DownloadService
from src.data.mapping import MappingManager

def test_single_page():
    """测试单个页面的下载"""
    print("=== 测试海康威视 latestAnnouncement 页面 ===")

    # 创建下载服务
    downloader = DownloadService(save_dir="downloads", mapping_file="stock_orgid_mapping.json", browser_strategy="playwright")

    # 获取组织ID
    mapping_manager = MappingManager()
    org_id = mapping_manager.get_org_id("002415")

    if not org_id:
        print("无法获取海康威视的组织ID")
        return

    print(f"组织ID: {org_id}")

    # 构建测试页面配置
    target_pages = [{
        "suffix": "latestAnnouncement",
        "allowed_keywords": ["招股说明书", "问询函"]
    }]

    print("开始下载...")
    start_time = time.time()

    try:
        records = downloader.download_stock_pdfs(
            stock_code="002415",
            target_pages=target_pages,
            max_retries=1
        )

        duration = time.time() - start_time
        print(f"下载完成，耗时: {duration:.2f} 秒")
        print(f"下载记录数: {len(records)}")

        for record in records:
            print(f"文件: {record.file_name}")
            print(f"路径: {record.file_path}")
            print(f"大小: {record.file_size} bytes")
            print("---")

    except Exception as e:
        print(f"下载失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_page()