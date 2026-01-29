#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试自动化脚本 - 自动运行完整的测试套件
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class AutomationTool:
    """测试自动化类"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.report_dir = self.project_root / "test_reports"
        self.log_dir = self.project_root / "test_logs"

        # 创建目录
        self.report_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)

        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "test_cases": [],
        }

    def run_command(self, cmd, description=""):
        """运行命令并返回结果"""
        print(f"🚀 {description}")
        print(f"  命令: {' '.join(cmd)}")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )
            end_time = time.time()

            elapsed = end_time - start_time

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed_time": elapsed,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "命令执行超时",
                "elapsed_time": 300,
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "elapsed_time": 0,
            }

    def run_unit_tests(self):
        """运行单元测试"""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/",
            "-v",
            "--cov=cninfo_activity_downloader",
            "--cov-report=term",
            "--cov-report=xml",
        ]

        result = self.run_command(cmd, "运行单元测试")

        test_case = {
            "name": "unit_tests",
            "type": "unit",
            "success": result["success"],
            "elapsed_time": result["elapsed_time"],
            "output": result["stdout"],
        }

        self.test_results["test_cases"].append(test_case)

        if result["success"]:
            print("✅ 单元测试通过")
        else:
            print("❌ 单元测试失败")
            print(result["stderr"])

        return result["success"]

    def run_integration_tests(self):
        """运行集成测试"""
        cmd = [sys.executable, "-m", "pytest", "tests/integration/", "-v"]

        result = self.run_command(cmd, "运行集成测试")

        test_case = {
            "name": "integration_tests",
            "type": "integration",
            "success": result["success"],
            "elapsed_time": result["elapsed_time"],
            "output": result["stdout"],
        }

        self.test_results["test_cases"].append(test_case)

        if result["success"]:
            print("✅ 集成测试通过")
        else:
            print("❌ 集成测试失败")
            print(result["stderr"])

        return result["success"]

    def run_e2e_tests(self):
        """运行端到端测试"""
        cmd = [sys.executable, "-m", "pytest", "tests/e2e/", "-v"]

        result = self.run_command(cmd, "运行端到端测试")

        test_case = {
            "name": "e2e_tests",
            "type": "e2e",
            "success": result["success"],
            "elapsed_time": result["elapsed_time"],
            "output": result["stdout"],
        }

        self.test_results["test_cases"].append(test_case)

        if result["success"]:
            print("✅ 端到端测试通过")
        else:
            print("❌ 端到端测试失败")
            print(result["stderr"])

        return result["success"]

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🤖 开始自动化测试")
        print("=" * 60)

        start_time = time.time()

        # 运行各层级测试
        unit_success = self.run_unit_tests()
        print()

        integration_success = self.run_integration_tests()
        print()

        e2e_success = self.run_e2e_tests()
        print()

        end_time = time.time()
        total_time = end_time - start_time

        # 统计结果
        all_success = unit_success and integration_success and e2e_success

        self.test_results["total_time"] = total_time
        self.test_results["overall_success"] = all_success

        # 保存报告
        self.save_test_report()

        print("=" * 60)
        print("📊 测试结果汇总:")
        print("=" * 60)
        print(f"单元测试:     {'✅ 通过' if unit_success else '❌ 失败'}")
        print(f"集成测试:     {'✅ 通过' if integration_success else '❌ 失败'}")
        print(f"端到端测试:   {'✅ 通过' if e2e_success else '❌ 失败'}")
        print(f"总耗时:       {total_time:.2f} 秒")
        print(f"总体结果:     {'✅ 所有测试通过!' if all_success else '❌ 测试失败!'}")
        print("=" * 60)

        return all_success

    def save_test_report(self):
        """保存测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON报告
        json_report = self.report_dir / f"test_report_{timestamp}.json"
        with open(json_report, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        # 文本报告
        text_report = self.report_dir / f"test_report_{timestamp}.txt"
        with open(text_report, "w", encoding="utf-8") as f:
            f.write(f"测试报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")

            f.write(
                f"总体结果: {'通过' if self.test_results['overall_success'] else '失败'}\n"
            )
            f.write(f"总耗时: {self.test_results['total_time']:.2f} 秒\n\n")

            for test_case in self.test_results["test_cases"]:
                f.write(
                    f"{test_case['type'].upper()} 测试: {'通过' if test_case['success'] else '失败'}\n"
                )
                f.write(f"耗时: {test_case['elapsed_time']:.2f} 秒\n")
                f.write("-" * 30 + "\n")

        print(f"📝 测试报告已保存到: {json_report}")
        print(f"📝 文本报告已保存到: {text_report}")

    def run_code_quality_checks(self):
        """运行代码质量检查"""
        print("\n🔍 运行代码质量检查")
        print("=" * 40)

        checks = [
            {
                "name": "flake8 代码风格检查",
                "cmd": [
                    sys.executable,
                    "-m",
                    "flake8",
                    ".",
                    "--count",
                    "--max-line-length=127",
                    "--statistics",
                ],
                "required": False,
            },
            {
                "name": "black 代码格式化检查",
                "cmd": [sys.executable, "-m", "black", "--check", "."],
                "required": False,
            },
            {
                "name": "import 排序检查",
                "cmd": [sys.executable, "-m", "isort", "--check-only", "."],
                "required": False,
            },
        ]

        all_passed = True

        for check in checks:
            result = self.run_command(check["cmd"], check["name"])

            if result["success"]:
                print(f"✅ {check['name']} 通过")
            else:
                print(f"⚠️  {check['name']} 发现问题")
                if check["required"]:
                    all_passed = False
                print(result["stdout"])
                print(result["stderr"])

            print()

        return all_passed


def main():
    """主函数"""
    automation = TestAutomation()

    # 运行测试
    test_success = automation.run_all_tests()

    # 运行代码质量检查（可选）
    if "--quality" in sys.argv:
        quality_success = automation.run_code_quality_checks()
        test_success = test_success and quality_success

    # 退出码
    sys.exit(0 if test_success else 1)


if __name__ == "__main__":
    main()
