#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试清理工具模块
提供智能的测试目录清理功能
"""

import os
import shutil
import json
import time
from pathlib import Path
from typing import Dict, List, Any

def get_test_directory_status(test_dir: str) -> Dict[str, Any]:
    """获取测试目录状态（包含根目录文件）"""
    test_path = Path(test_dir)

    if not test_path.exists():
        return {
            "exists": False,
            "total_files": 0,
            "total_dirs": 0,
            "companies": [],
            "root_files": []
        }

    companies = []
    total_files = 0
    root_files = []

    # 首先检查根目录的PDF文件
    for file_path in test_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() == '.pdf':
            root_files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "path": str(file_path)
            })
            total_files += 1

    # 然后检查公司子目录
    for company_dir in test_path.iterdir():
        if company_dir.is_dir():
            company_files = []
            for file_path in company_dir.iterdir():
                if file_path.is_file():
                    company_files.append({
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "path": str(file_path)
                    })
                    total_files += 1

            companies.append({
                "name": company_dir.name,
                "files": company_files,
                "file_count": len(company_files)
            })

    return {
        "exists": True,
        "total_files": total_files,
        "total_dirs": len(companies),
        "companies": companies,
        "root_files": root_files,
        "root_file_count": len(root_files)
    }

def clean_test_files(test_dir: str, preserve_cases: List[Dict[str, Any]] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    清理测试文件（包含根目录文件清理）

    参数:
        test_dir: 测试目录路径
        preserve_cases: 需要保留的测试用例列表
        dry_run: 是否只预览不实际执行

    返回:
        清理结果统计
    """
    test_path = Path(test_dir)
    cleaned_files = 0
    cleaned_dirs = 0
    cleaned_root_files = 0
    preserved_files = 0
    preserved_dirs = 0
    preserved_root_files = 0

    if not test_path.exists():
        return {
            "cleaned_files": 0,
            "cleaned_dirs": 0,
            "cleaned_root_files": 0,
            "preserved_files": 0,
            "preserved_dirs": 0,
            "preserved_root_files": 0,
            "dry_run": dry_run
        }

    # 获取需要保留的公司名称和对应的股票代码
    preserve_companies = set()
    preserve_stock_codes = set()
    if preserve_cases:
        for case in preserve_cases:
            stock_code = case.get("stock_code")
            if stock_code:
                preserve_stock_codes.add(stock_code)
                # 获取真实的公司名称
                try:
                    from get_stock_name import get_stock_name
                    company_name = get_stock_name(stock_code)
                    if company_name and not company_name.startswith('错误') and not company_name.startswith('网络'):
                        preserve_companies.add(company_name)
                except:
                    preserve_companies.add(f"股票{stock_code}")

    # 1. 清理根目录的PDF文件
    for file_path in test_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() == '.pdf':
            # 检查文件名是否包含需要保留的股票代码
            should_preserve_root = False
            for stock_code in preserve_stock_codes:
                if stock_code in file_path.name:
                    should_preserve_root = True
                    break

            if should_preserve_root:
                preserved_root_files += 1
                continue

            # 清理根目录文件
            if not dry_run:
                try:
                    file_path.unlink()
                    cleaned_root_files += 1
                except Exception as e:
                    print(f"清理根目录文件 {file_path} 失败: {e}")
            else:
                cleaned_root_files += 1

    # 2. 清理公司子目录
    for company_dir in test_path.iterdir():
        if company_dir.is_dir():
            company_name = company_dir.name

            # 检查是否需要保留
            should_preserve = company_name in preserve_companies

            if should_preserve:
                preserved_dirs += 1
                # 计算保留的文件数
                file_count = sum(1 for _ in company_dir.iterdir() if _.is_file())
                preserved_files += file_count
                continue

            # 清理目录
            if not dry_run:
                try:
                    # 检查文件锁
                    lock_file = company_dir / ".lock"
                    if lock_file.exists():
                        print(f"警告: 目录 {company_dir} 有锁文件，跳过清理")
                        continue  # 跳过这个目录的清理

                    # 先计算文件数
                    file_count = sum(1 for _ in company_dir.iterdir() if _.is_file())
                    cleaned_files += file_count

                    # 删除目录，支持重试
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            shutil.rmtree(company_dir)
                            cleaned_dirs += 1
                            break  # 成功则退出重试循环
                        except Exception as e:
                            if attempt < max_retries - 1:
                                time.sleep(0.1 * (attempt + 1))  # 指数退避
                            else:
                                raise  # 最后一次失败则重新抛出异常
                except Exception as e:
                    print(f"清理目录 {company_dir} 失败: {e}")
            else:
                # 干运行时只计数
                file_count = sum(1 for _ in company_dir.iterdir() if _.is_file())
                cleaned_files += file_count
                cleaned_dirs += 1

    return {
        "cleaned_files": cleaned_files,
        "cleaned_dirs": cleaned_dirs,
        "cleaned_root_files": cleaned_root_files,
        "preserved_files": preserved_files,
        "preserved_dirs": preserved_dirs,
        "preserved_root_files": preserved_root_files,
        "dry_run": dry_run
    }

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='测试清理工具')
    parser.add_argument('--test-dir', default='end2end_test/test_results', help='测试目录路径')
    parser.add_argument('--dry-run', action='store_true', help='只预览不实际执行')
    parser.add_argument('--preserve-config', help='配置文件路径，包含需要保留的测试用例')
    parser.add_argument('--status', action='store_true', help='只显示目录状态')

    args = parser.parse_args()

    if args.status:
        # 显示目录状态
        status = get_test_directory_status(args.test_dir)
        print(f"目录状态: {args.test_dir}")
        print(f"存在: {status['exists']}")
        print(f"公司目录数: {status['total_dirs']}")
        print(f"文件总数: {status['total_files']}")
        print(f"根目录文件数: {status.get('root_file_count', 0)}")

        if status.get('root_files'):
            print(f"\n根目录文件:")
            for file in status['root_files']:
                print(f"  - {file['name']} ({file['size']} bytes)")

        if status['companies']:
            print(f"\n公司目录:")
            for company in status['companies']:
                print(f"  - {company['name']}: {company['file_count']} 个文件")
        return

    # 加载需要保留的测试用例
    preserve_cases = []
    if args.preserve_config and os.path.exists(args.preserve_config):
        try:
            with open(args.preserve_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                preserve_cases = config.get('test_cases', [])
                # 只保留 delete_later=False 的用例
                preserve_cases = [case for case in preserve_cases if not case.get('delete_later', True)]
        except Exception as e:
            print(f"加载配置文件失败: {e}")

    # 执行清理
    result = clean_test_files(args.test_dir, preserve_cases, args.dry_run)

    print(f"清理结果:")
    print(f"  清理公司文件: {result['cleaned_files']} 个")
    print(f"  清理公司目录: {result['cleaned_dirs']} 个")
    print(f"  清理根目录文件: {result['cleaned_root_files']} 个")
    print(f"  保留公司文件: {result['preserved_files']} 个")
    print(f"  保留公司目录: {result['preserved_dirs']} 个")
    print(f"  保留根目录文件: {result['preserved_root_files']} 个")
    print(f"  干运行模式: {result['dry_run']}")

if __name__ == "__main__":
    main()