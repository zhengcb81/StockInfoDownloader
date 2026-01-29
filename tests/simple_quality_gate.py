#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化版测试质量门禁
快速检查基本测试质量
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_basic_tests() -> Dict[str, Any]:
    """运行基本测试并收集结果"""
    print("运行基本测试...")

    # 只运行单元测试和部分集成测试，避免超时
    test_paths = [
        "tests/unit/",
        "tests/integration/multi_company/test_config_manager.py",
        "tests/integration/multi_company/test_parallel_download_manager.py",
        "tests/integration/multi_company/test_proxy_manager.py",
        "tests/integration/multi_company/test_enhanced_anti_crawler.py",
    ]

    results = {}

    for test_path in test_paths:
        try:
            print(f"测试 {test_path}...")
            result = subprocess.run(
                ["python", "-m", "pytest", test_path, "--tb=short", "-v"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # 解析输出结果
            lines = result.stdout.split("\n")
            for line in lines:
                if "passed" in line and "failed" in line:
                    # 解析类似 "21 passed, 0 failed in 15.46s" 的行
                    parts = line.split()
                    passed = int(parts[0]) if parts[0].isdigit() else 0
                    failed = int(parts[2]) if parts[2].isdigit() else 0

                    if test_path not in results:
                        results[test_path] = {"passed": 0, "failed": 0}

                    results[test_path]["passed"] += passed
                    results[test_path]["failed"] += failed

        except subprocess.TimeoutExpired:
            print(f"测试 {test_path} 超时")
            results[test_path] = {"passed": 0, "failed": 0, "timeout": True}
        except Exception as e:
            print(f"测试 {test_path} 出错: {e}")
            results[test_path] = {"passed": 0, "failed": 0, "error": str(e)}

    return results


def check_test_quality(results: Dict[str, Any]) -> Dict[str, Any]:
    """检查测试质量"""
    print("检查测试质量...")

    total_passed = 0
    total_failed = 0
    total_timeout = 0
    total_error = 0

    for test_path, result in results.items():
        total_passed += result.get("passed", 0)
        total_failed += result.get("failed", 0)
        if result.get("timeout"):
            total_timeout += 1
        if result.get("error"):
            total_error += 1

    total_tests = total_passed + total_failed

    if total_tests > 0:
        pass_rate = (total_passed / total_tests) * 100
    else:
        pass_rate = 0

    # 质量标准
    quality_standards = {
        "min_pass_rate": 90.0,
        "max_timeout_tests": 2,
        "max_error_tests": 0,
    }

    meets_pass_rate = pass_rate >= quality_standards["min_pass_rate"]
    meets_timeout_standard = total_timeout <= quality_standards["max_timeout_tests"]
    meets_error_standard = total_error <= quality_standards["max_error_tests"]

    overall_status = (
        "PASS"
        if (meets_pass_rate and meets_timeout_standard and meets_error_standard)
        else "FAIL"
    )

    return {
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "timeout": total_timeout,
        "errors": total_error,
        "pass_rate": pass_rate,
        "meets_pass_rate": meets_pass_rate,
        "meets_timeout_standard": meets_timeout_standard,
        "meets_error_standard": meets_error_standard,
        "overall_status": overall_status,
        "quality_standards": quality_standards,
    }


def generate_report(quality_check: Dict[str, Any]) -> str:
    """生成质量报告"""
    report_lines = [
        "=== 简化版测试质量门禁报告 ===",
        f"总体状态: {quality_check['overall_status']}",
        "",
        "测试统计:",
        f"  总测试数: {quality_check['total_tests']}",
        f"  通过数: {quality_check['passed']}",
        f"  失败数: {quality_check['failed']}",
        f"  超时数: {quality_check['timeout']}",
        f"  错误数: {quality_check['errors']}",
        f"  通过率: {quality_check['pass_rate']:.1f}%",
        "",
        "质量检查结果:",
        f"  通过率检查: {'通过' if quality_check['meets_pass_rate'] else '失败'} (要求: ≥{quality_check['quality_standards']['min_pass_rate']}%)",
        f"  超时检查: {'通过' if quality_check['meets_timeout_standard'] else '失败'} (要求: ≤{quality_check['quality_standards']['max_timeout_tests']}个)",
        f"  错误检查: {'通过' if quality_check['meets_error_standard'] else '失败'} (要求: ≤{quality_check['quality_standards']['max_error_tests']}个)",
        "",
        "质量门禁标准:",
        f"  - 最低通过率: {quality_check['quality_standards']['min_pass_rate']}%",
        f"  - 最大超时测试数: {quality_check['quality_standards']['max_timeout_tests']}",
        f"  - 最大错误测试数: {quality_check['quality_standards']['max_error_tests']}",
    ]

    return "\n".join(report_lines)


def main():
    """主函数"""
    print("开始简化版测试质量门禁检查...")

    # 运行基本测试
    test_results = run_basic_tests()

    # 检查质量
    quality_check = check_test_quality(test_results)

    # 生成报告
    report = generate_report(quality_check)
    print(report)

    # 根据检查结果退出
    if quality_check["overall_status"] == "PASS":
        print("\n✅ 测试质量门禁检查通过！")
        sys.exit(0)
    else:
        print("\n❌ 测试质量门禁检查失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
