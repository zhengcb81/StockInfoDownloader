#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试运行脚本
运行所有集成测试并生成统一报告
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.unit.test_report_generator import ReportGenerator


def run_integration_tests():
    """运行所有集成测试"""
    print("=" * 60)
    print("开始运行集成测试")
    print("=" * 60)
    
    # 测试文件列表
    test_files = [
        "tests/integration/test_integration.py",
        "tests/integration/test_pagination_integration.py",
        "tests/integration/test_web_scraper_integration.py",
        "tests/integration/test_downloader_integration.py"
    ]
    
    all_results = []
    components_tested = []
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n运行测试: {test_file}")
            
            try:
                # 运行pytest
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    test_file, "-v", "--tb=short"
                ], capture_output=True, text=True, timeout=120)
                
                # 解析结果
                component_name = Path(test_file).stem.replace("test_", "").replace("_integration", "")
                components_tested.append(component_name)
                
                # 简单的结果解析
                success = result.returncode == 0
                output = result.stdout + result.stderr
                
                test_result = {
                    "component": component_name,
                    "test_file": test_file,
                    "success": success,
                    "output": output,
                    "execution_time": 0.0
                }
                
                if success:
                    print(f"[OK] {component_name} 集成测试通过")
                else:
                    print(f"[FAIL] {component_name} 集成测试失败")
                    print(f"   错误信息: {result.stderr[:200]}...")
                
                all_results.append(test_result)
                
            except subprocess.TimeoutExpired:
                print(f"[TIMEOUT] {test_file} 测试超时")
                all_results.append({
                    "component": component_name,
                    "test_file": test_file,
                    "success": False,
                    "error": "测试超时",
                    "execution_time": 120.0
                })
            except Exception as e:
                print(f"[ERROR] {test_file} 测试异常: {e}")
                all_results.append({
                    "component": component_name,
                    "test_file": test_file,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0.0
                })
        else:
            print(f"⚠️  测试文件不存在: {test_file}")
    
    return all_results, components_tested


def main():
    """主函数"""
    print("集成测试套件")
    print("=" * 60)
    
    start_time = time.time()
    
    # 运行集成测试
    test_results, components_tested = run_integration_tests()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 生成报告
    print("\n" + "=" * 60)
    print("生成测试报告")
    print("=" * 60)
    
    generator = ReportGenerator()
    
    # 创建集成测试报告
    report_file = generator.create_integration_report(
        test_results=test_results,
        components_tested=components_tested,
        description="完整的集成测试套件 - 验证各组件间协作"
    )
    
    # 打印报告摘要
    generator.print_report_summary(report_file)
    
    # 输出执行时间
    print(f"\n总执行时间: {execution_time:.2f}秒")
    
    # 输出失败测试详情
    failed_tests = [r for r in test_results if not r["success"]]
    if failed_tests:
        print(f"\n失败的集成测试组件:")
        for test in failed_tests:
            print(f"  - {test['component']}: {test.get('error', '未知错误')}")
    
    return 0 if all(r["success"] for r in test_results) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)