#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试运行器

提供统一的测试运行入口，支持运行不同类型的测试
"""

import unittest
import sys
import os
import argparse
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_unit_tests():
    """运行单元测试"""
    print("🧪 运行单元测试...")
    
    # 发现并运行单元测试
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加单元测试模块
    from tests.test_orgid_utils import TestOrgidUtils, TestOrgidUtilsIntegration
    from tests.test_cninfo_downloader import (
        TestCninfoDownloader, 
        TestCninfoDownloaderIntegration,
        TestCninfoDownloaderMocked
    )
    
    suite.addTests(loader.loadTestsFromTestCase(TestOrgidUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestOrgidUtilsIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCninfoDownloader))
    suite.addTests(loader.loadTestsFromTestCase(TestCninfoDownloaderIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCninfoDownloaderMocked))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_performance_tests():
    """运行性能测试"""
    print("⚡ 运行性能测试...")
    
    try:
        import psutil
    except ImportError:
        print("❌ 性能测试需要 psutil 库，请运行: pip install psutil")
        return False
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加性能测试模块
    from tests.test_performance import (
        TestOrgidUtilsPerformance,
        TestCninfoDownloaderPerformance,
        TestConcurrencyPerformance,
        TestMemoryLeakage
    )
    
    suite.addTests(loader.loadTestsFromTestCase(TestOrgidUtilsPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestCninfoDownloaderPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestConcurrencyPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryLeakage))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """运行集成测试"""
    print("🔗 运行集成测试...")
    
    # 这里可以添加需要真实网络连接的集成测试
    # 目前集成测试已经包含在单元测试中
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加集成测试
    from tests.test_orgid_utils import TestOrgidUtilsIntegration
    from tests.test_cninfo_downloader import TestCninfoDownloaderIntegration
    
    suite.addTests(loader.loadTestsFromTestCase(TestOrgidUtilsIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCninfoDownloaderIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_all_tests():
    """运行所有测试"""
    print("🚀 运行所有测试...")
    
    start_time = time.time()
    
    results = []
    
    # 运行单元测试
    print("\n" + "="*60)
    results.append(("单元测试", run_unit_tests()))
    
    # 运行集成测试
    print("\n" + "="*60)
    results.append(("集成测试", run_integration_tests()))
    
    # 运行性能测试
    print("\n" + "="*60)
    results.append(("性能测试", run_performance_tests()))
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 输出测试结果摘要
    print("\n" + "="*60)
    print("📊 测试结果摘要")
    print("="*60)
    
    all_passed = True
    for test_type, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_type}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n⏱️  总耗时: {total_time:.2f} 秒")
    
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("💥 部分测试失败！")
    
    return all_passed

def run_specific_test(test_name):
    """运行特定的测试"""
    print(f"🎯 运行特定测试: {test_name}")
    
    loader = unittest.TestLoader()
    
    try:
        # 尝试加载特定测试
        suite = loader.loadTestsFromName(test_name)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()
    except Exception as e:
        print(f"❌ 无法运行测试 {test_name}: {e}")
        return False

def check_dependencies():
    """检查测试依赖"""
    print("🔍 检查测试依赖...")
    
    required_modules = [
        'unittest',
        'json',
        'tempfile',
        'pathlib',
    ]
    
    optional_modules = [
        ('psutil', '性能测试'),
        ('selenium', 'WebDriver测试'),
    ]
    
    missing_required = []
    missing_optional = []
    
    # 检查必需模块
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_required.append(module)
    
    # 检查可选模块
    for module, purpose in optional_modules:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append((module, purpose))
    
    if missing_required:
        print(f"❌ 缺少必需模块: {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        print("⚠️  缺少可选模块:")
        for module, purpose in missing_optional:
            print(f"   - {module} (用于{purpose})")
    
    print("✅ 依赖检查完成")
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="StockInfoDownloader 测试运行器")
    parser.add_argument(
        'test_type',
        nargs='?',
        choices=['unit', 'performance', 'integration', 'all'],
        default='all',
        help='要运行的测试类型 (默认: all)'
    )
    parser.add_argument(
        '--specific',
        help='运行特定的测试 (例如: tests.test_orgid_utils.TestOrgidUtils.test_is_valid_stock_code)'
    )
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='检查测试依赖'
    )
    
    args = parser.parse_args()
    
    # 检查依赖
    if args.check_deps:
        return 0 if check_dependencies() else 1
    
    if not check_dependencies():
        print("❌ 依赖检查失败，请安装缺少的模块")
        return 1
    
    # 运行特定测试
    if args.specific:
        success = run_specific_test(args.specific)
        return 0 if success else 1
    
    # 运行指定类型的测试
    if args.test_type == 'unit':
        success = run_unit_tests()
    elif args.test_type == 'performance':
        success = run_performance_tests()
    elif args.test_type == 'integration':
        success = run_integration_tests()
    elif args.test_type == 'all':
        success = run_all_tests()
    else:
        print(f"❌ 未知的测试类型: {args.test_type}")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 