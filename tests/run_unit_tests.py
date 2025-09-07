#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试运行脚本
运行所有单元测试并生成统一报告
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_report_generator import TestReportGenerator


def run_unit_tests():
    """运行所有单元测试"""
    print("=" * 60)
    print("开始运行单元测试")
    print("=" * 60)
    
    # 测试文件列表
    test_files = [
        "tests/unit/test_mapping.py",
        "tests/unit/test_orgid_service.py", 
        "tests/unit/test_logger.py",
        "tests/unit/test_driver.py",
        "tests/unit/test_config.py",
        "tests/unit/test_download_service.py",
        "tests/unit/test_file_utils.py",
        "tests/unit/test_keyword_matcher.py",
        "tests/unit/test_models.py",
        "tests/unit/test_pagination.py"
    ]
    
    all_results = []
    modules_tested = []
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n运行测试: {test_file}")
            
            try:
                # 运行pytest
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    test_file, "-v", "--tb=short"
                ], capture_output=True, text=True, timeout=60)
                
                # 解析结果
                module_name = Path(test_file).stem.replace("test_", "")
                modules_tested.append(module_name)
                
                # 简单的结果解析
                success = result.returncode == 0
                output = result.stdout + result.stderr
                
                test_result = {
                    "module": module_name,
                    "test_file": test_file,
                    "success": success,
                    "output": output,
                    "execution_time": 0.0  # pytest会显示时间
                }
                
                if success:
                    print(f"✅ {module_name} 测试通过")
                else:
                    print(f"❌ {module_name} 测试失败")
                    print(f"   错误信息: {result.stderr[:200]}...")
                
                all_results.append(test_result)
                
            except subprocess.TimeoutExpired:
                print(f"⏰ {test_file} 测试超时")
                all_results.append({
                    "module": module_name,
                    "test_file": test_file,
                    "success": False,
                    "error": "测试超时",
                    "execution_time": 60.0
                })
            except Exception as e:
                print(f"❌ {test_file} 测试异常: {e}")
                all_results.append({
                    "module": module_name,
                    "test_file": test_file,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0.0
                })
        else:
            print(f"⚠️  测试文件不存在: {test_file}")
    
    return all_results, modules_tested


def main():
    """主函数"""
    print("单元测试套件")
    print("=" * 60)
    
    start_time = time.time()
    
    # 运行单元测试
    test_results, modules_tested = run_unit_tests()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 生成报告
    print("\n" + "=" * 60)
    print("生成测试报告")
    print("=" * 60)
    
    generator = TestReportGenerator()
    
    # 创建单元测试报告
    report_file = generator.create_unit_report(
        test_results=test_results,
        modules_tested=modules_tested,
        description="完整的单元测试套件 - 验证所有核心模块功能"
    )
    
    # 打印报告摘要
    generator.print_report_summary(report_file)
    
    # 输出执行时间
    print(f"\n总执行时间: {execution_time:.2f}秒")
    
    # 输出失败测试详情
    failed_tests = [r for r in test_results if not r["success"]]
    if failed_tests:
        print(f"\n失败的测试模块:")
        for test in failed_tests:
            print(f"  - {test['module']}: {test.get('error', '未知错误')}")
    
    return 0 if all(r["success"] for r in test_results) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)