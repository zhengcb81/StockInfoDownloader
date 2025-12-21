#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件放置诊断工具
分析Selenium下载过程中文件放置的根本原因
"""

import os
import json
from pathlib import Path
from datetime import datetime

def analyze_file_placement():
    """分析文件放置问题"""

    test_results_dir = Path("end2end_test/test_results")
    expected_dir = Path("end2end_test/expected_results")

    print("=" * 80)
    print("文件放置诊断分析")
    print("=" * 80)

    # 1. 检查实际目录结构
    print("\n1. 实际目录结构:")
    if test_results_dir.exists():
        for item in test_results_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(test_results_dir)
                size = item.stat().st_size
                print(f"  {rel_path} ({size} bytes)")
    else:
        print("  测试结果目录不存在")

    # 2. 检查预期目录结构
    print("\n2. 预期目录结构:")
    if expected_dir.exists():
        for item in expected_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(expected_dir)
                size = item.stat().st_size
                print(f"  {rel_path} ({size} bytes)")
    else:
        print("  预期结果目录不存在")

    # 3. 分析问题
    print("\n3. 问题分析:")

    # 检查根目录文件
    root_files = []
    if test_results_dir.exists():
        for item in test_results_dir.iterdir():
            if item.is_file():
                root_files.append(item.name)

    if root_files:
        print(f"  [ERROR] 发现根目录文件: {root_files}")
        print("  这些文件应该在公司子目录中")
    else:
        print("  [OK] 根目录没有文件")

    # 检查公司目录
    company_dirs = []
    if test_results_dir.exists():
        for item in test_results_dir.iterdir():
            if item.is_dir():
                company_dirs.append(item.name)

    print(f"\n  公司目录: {company_dirs}")

    # 检查每个公司目录的文件
    for company in company_dirs:
        company_path = test_results_dir / company
        files = list(company_path.glob("*.pdf"))
        print(f"\n  {company}/: {len(files)} 个文件")
        for f in files:
            print(f"    - {f.name}")

    # 4. 与预期对比
    print("\n4. 与预期对比:")
    if expected_dir.exists() and test_results_dir.exists():
        expected_files = set(f.relative_to(expected_dir) for f in expected_dir.rglob("*.pdf"))
        actual_files = set(f.relative_to(test_results_dir) for f in test_results_dir.rglob("*.pdf"))

        missing = expected_files - actual_files
        extra = actual_files - expected_files

        if missing:
            print(f"  [MISSING] 缺失文件: {len(missing)} 个")
            for f in missing:
                print(f"    - {f}")
        else:
            print("  [OK] 没有缺失文件")

        if extra:
            print(f"  [EXTRA] 多余文件: {len(extra)} 个")
            for f in extra:
                print(f"    - {f}")
        else:
            print("  [OK] 没有多余文件")

    # 5. 检查调试日志
    print("\n5. 检查最近的调试日志:")
    debug_log_dir = Path("logs/debug_markers")
    if debug_log_dir.exists():
        jsonl_files = list(debug_log_dir.glob("*.jsonl"))
        if jsonl_files:
            latest_log = max(jsonl_files, key=lambda x: x.stat().st_mtime)
            print(f"  最近的调试日志: {latest_log.name}")

            # 读取最后几行查看下载记录
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-20:]  # 最后20行
                download_related = [line for line in lines if 'download' in line.lower() or '文件' in line]

                if download_related:
                    print("  下载相关记录:")
                    for line in download_related:
                        try:
                            data = json.loads(line)
                            if data.get('step') == 'download_success':
                                print(f"    - {data.get('details', {})}")
                        except:
                            pass

    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == "__main__":
    analyze_file_placement()