#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回归测试运行脚本
运行所有回归测试并生成统一报告
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_report_generator import TestReportGenerator


def run_regression_tests():
    """运行所有回归测试"""
    print("=" * 60)
    print("开始运行回归测试")
    print("=" * 60)
    
    # 回归测试文件列表
    test_files = [
        "tests/regression/test_regression.py"
    ]
    
    all_results = []
    bugs_tested = []
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"\n运行测试: {test_file}")
            
            try:
                # 运行pytest
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    test_file, "-v", "--tb=short"
                ], capture_output=True, text=True, timeout=180)
                
                # 解析结果
                test_name = Path(test_file).stem.replace("test_", "")
                bugs_tested.append(f"{test_name}_regression")
                
                # 简单的结果解析
                success = result.returncode == 0
                output = result.stdout + result.stderr
                
                test_result = {
                    "bug_category": test_name,
                    "test_file": test_file,
                    "success": success,
                    "output": output,
                    "execution_time": 0.0
                }
                
                if success:
                    print(f"✅ {test_name} 回归测试通过")
                else:
                    print(f"❌ {test_name} 回归测试失败")
                    print(f"   错误信息: {result.stderr[:300]}...")
                
                all_results.append(test_result)
                
            except subprocess.TimeoutExpired:
                print(f"⏰ {test_file} 测试超时")
                all_results.append({
                    "bug_category": test_name,
                    "test_file": test_file,
                    "success": False,
                    "error": "测试超时",
                    "execution_time": 180.0
                })
            except Exception as e:
                print(f"❌ {test_file} 测试异常: {e}")
                all_results.append({
                    "bug_category": test_name,
                    "test_file": test_file,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0.0
                })
        else:
            print(f"⚠️  测试文件不存在: {test_file}")
    
    return all_results, bugs_tested


def analyze_regression_results(results):
    """分析回归测试结果"""
    print("\n" + "=" * 60)
    print("回归测试分析")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"总回归测试: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    # 分析失败的测试
    if failed_tests > 0:
        print(f"\n失败的回归测试:")
        for result in results:
            if not result["success"]:
                bug_category = result["bug_category"]
                error = result.get("error", "未知错误")
                print(f"  - {bug_category}: {error}")
    
    # 回归风险评估
    if failed_tests == 0:
        print(f"\n✅ 回归风险评估: 低风险")
        print(f"   所有已修复的bug都没有重新出现")
    elif failed_tests <= 2:
        print(f"\n⚠️  回归风险评估: 中等风险")
        print(f"   有少数已修复的bug重新出现，需要关注")
    else:
        print(f"\n❌ 回归风险评估: 高风险")
        print(f"   有多个已修复的bug重新出现，需要立即处理")
    
    return failed_tests == 0


def main():
    """主函数"""
    print("回归测试套件")
    print("=" * 60)
    print("目的: 确保已修复的bug不会重新出现")
    print("=" * 60)
    
    start_time = time.time()
    
    # 运行回归测试
    test_results, bugs_tested = run_regression_tests()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 分析结果
    is_low_risk = analyze_regression_results(test_results)
    
    # 生成报告
    print("\n" + "=" * 60)
    print("生成测试报告")
    print("=" * 60)
    
    generator = TestReportGenerator()
    
    # 创建回归测试报告
    report_file = generator.create_regression_report(
        test_results=test_results,
        bugs_tested=bugs_tested,
        description="完整的回归测试套件 - 验证已修复bug的稳定性"
    )
    
    # 打印报告摘要
    generator.print_report_summary(report_file)
    
    # 输出执行时间
    print(f"\n总执行时间: {execution_time:.2f}秒")
    
    # 输出风险等级
    risk_level = "低" if is_low_risk else "高"
    print(f"回归风险等级: {risk_level}")
    
    return 0 if is_low_risk else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)