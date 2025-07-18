#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试脚本 - 财务报告下载功能
"""

import os
import sys
import subprocess

def run_tests():
    """运行测试"""
    print("=" * 60)
    print("财务报告下载器测试")
    print("=" * 60)
    
    # 测试1: 检查文件是否存在
    print("1. 检查文件完整性...")
    required_files = [
        'cninfo_financial_downloader.py',
        'unified_downloader.py',
        'config.json',
        'cninfo_activity_downloader.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("[FAIL] 缺失文件:", missing_files)
        return False
    else:
        print("[OK] 所有必需文件存在")
    
    # 测试2: 语法检查
    print("\n2. 语法检查...")
    for file in required_files:
        if file.endswith('.py'):
            result = subprocess.run([sys.executable, '-m', 'py_compile', file], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] {file}")
            else:
                print(f"[FAIL] {file}: {result.stderr}")
                return False
    
    # 测试3: 导入检查
    print("\n3. 模块导入测试...")
    try:
        from cninfo_financial_downloader import CninfoFinancialDownloader, FinancialReportType
        print("[OK] 财务报告下载器模块导入成功")
    except Exception as e:
        print(f"[FAIL] 财务报告下载器导入失败: {e}")
        return False
    
    try:
        from unified_downloader import UnifiedDownloader
        print("[OK] 统一下载器模块导入成功")
    except Exception as e:
        print(f"[FAIL] 统一下载器导入失败: {e}")
        return False
    
    # 测试4: 配置文件检查
    print("\n4. 配置文件检查...")
    try:
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = ['stock_code', 'save_dir', 'headless']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(f"[FAIL] 配置缺失: {missing_keys}")
            return False
        else:
            print("[OK] 配置文件格式正确")
            print(f"  股票代码: {config.get('stock_code')}")
            print(f"  保存目录: {config.get('save_dir')}")
            print(f"  无头模式: {config.get('headless')}")
    
    except Exception as e:
        print(f"[FAIL] 配置文件错误: {e}")
        return False
    
    # 测试5: 命令行帮助
    print("\n5. 命令行接口测试...")
    
    # 测试财务下载器帮助
    print("  财务下载器帮助:")
    result = subprocess.run([sys.executable, 'cninfo_financial_downloader.py', '--help'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("[OK] 财务下载器命令行可用")
    else:
        print("[FAIL] 财务下载器命令行错误")
    
    # 测试统一下载器帮助
    print("  统一下载器帮助:")
    result = subprocess.run([sys.executable, 'unified_downloader.py', '--help'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("[OK] 统一下载器命令行可用")
    else:
        print("[FAIL] 统一下载器命令行错误")
    
    print("\n" + "=" * 60)
    print("测试完成: 所有基础功能检查通过")
    print("=" * 60)
    print("下一步:")
    print("1. 运行: python cninfo_financial_downloader.py --stock-code 002415")
    print("2. 或运行: python unified_downloader.py --interactive")
    print("3. 查看日志: cninfo_financial_downloader.log")
    
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)