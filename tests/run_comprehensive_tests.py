#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
综合测试运行器 - 运行所有层级的测试
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


def run_tests(test_type, verbose=False, coverage=False):
    """运行指定类型的测试"""
    test_dirs = {
        'unit': 'tests/unit',
        'integration': 'tests/integration',
        'e2e': 'tests/e2e',
        'all': 'tests'
    }
    
    if test_type not in test_dirs:
        print(f"错误: 未知的测试类型 '{test_type}'")
        print(f"可用的类型: {', '.join(test_dirs.keys())}")
        return False
    
    test_dir = test_dirs[test_type]
    
    # 构建pytest命令
    cmd = [sys.executable, '-m', 'pytest', test_dir]
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=cninfo_activity_downloader', '--cov-report=term'])
    
    print(f"运行 {test_type} 测试...")
    print(f"命令: {' '.join(cmd)}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        end_time = time.time()
        
        # 输出结果
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print("=" * 60)
        print(f"测试完成! 耗时: {end_time - start_time:.2f} 秒")
        print(f"退出码: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ 所有测试通过!")
        else:
            print("❌ 测试失败!")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行测试时发生错误: {e}")
        return False


def run_specific_test(test_path, verbose=False):
    """运行特定的测试文件"""
    if not os.path.exists(test_path):
        print(f"错误: 测试文件 '{test_path}' 不存在")
        return False
    
    cmd = [sys.executable, '-m', 'pytest', test_path]
    if verbose:
        cmd.append('-v')
    
    print(f"运行特定测试: {test_path}")
    print(f"命令: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print("=" * 60)
        print(f"退出码: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行测试时发生错误: {e}")
        return False


def generate_test_report():
    """生成测试报告"""
    report_dir = "test_reports"
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(report_dir, f"test_report_{timestamp}.txt")
    
    print(f"生成测试报告: {report_file}")
    
    # 运行所有测试并捕获输出
    cmd = [sys.executable, '-m', 'pytest', 'tests', '-v', '--tb=short']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"测试报告 - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            f.write(result.stdout)
            
            if result.stderr:
                f.write("\n错误输出:\n")
                f.write("=" * 20 + "\n")
                f.write(result.stderr)
            
            f.write(f"\n\n退出码: {result.returncode}")
            
            if result.returncode == 0:
                f.write("\n✅ 所有测试通过!")
            else:
                f.write("\n❌ 测试失败!")
        
        print(f"报告已保存到: {report_file}")
        return True
        
    except Exception as e:
        print(f"生成报告时发生错误: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行综合测试')
    parser.add_argument('test_type', nargs='?', default='all', 
                       choices=['unit', 'integration', 'e2e', 'all'],
                       help='测试类型 (unit, integration, e2e, all)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='详细输出')
    parser.add_argument('-c', '--coverage', action='store_true',
                       help='生成覆盖率报告')
    parser.add_argument('-f', '--file', 
                       help='运行特定的测试文件')
    parser.add_argument('-r', '--report', action='store_true',
                       help='生成测试报告')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("股票信息下载器 - 综合测试运行器")
    print("=" * 60)
    
    if args.report:
        success = generate_test_report()
        sys.exit(0 if success else 1)
    
    if args.file:
        success = run_specific_test(args.file, args.verbose)
        sys.exit(0 if success else 1)
    
    success = run_tests(args.test_type, args.verbose, args.coverage)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()