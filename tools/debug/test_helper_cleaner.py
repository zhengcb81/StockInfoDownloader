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
    """获取测试目录状态"""
    test_path = Path(test_dir)
    
    if not test_path.exists():
        return {
            "exists": False,
            "total_files": 0,
            "total_dirs": 0,
            "companies": []
        }
    
    companies = []
    total_files = 0
    
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
        "companies": companies
    }

def clean_test_files(test_dir: str, preserve_cases: List[Dict[str, Any]] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    清理测试文件
    
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
    preserved_files = 0
    preserved_dirs = 0
    
    if not test_path.exists():
        return {
            "cleaned_files": 0,
            "cleaned_dirs": 0,
            "preserved_files": 0,
            "preserved_dirs": 0,
            "dry_run": dry_run
        }
    
    # 获取需要保留的公司名称
    preserve_companies = set()
    if preserve_cases:
        for case in preserve_cases:
            stock_code = case.get("stock_code")
            if stock_code:
                # 获取真实的公司名称
                try:
                    from get_stock_name import get_stock_name
                    company_name = get_stock_name(stock_code)
                    if company_name and not company_name.startswith('错误') and not company_name.startswith('网络'):
                        preserve_companies.add(company_name)
                except:
                    preserve_companies.add(f"股票{stock_code}")
    
    # 清理目录
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
        "preserved_files": preserved_files,
        "preserved_dirs": preserved_dirs,
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
    print(f"  清理文件: {result['cleaned_files']} 个")
    print(f"  清理目录: {result['cleaned_dirs']} 个")
    print(f"  保留文件: {result['preserved_files']} 个")
    print(f"  保留目录: {result['preserved_dirs']} 个")
    print(f"  干运行模式: {result['dry_run']}")

if __name__ == "__main__":
    main()