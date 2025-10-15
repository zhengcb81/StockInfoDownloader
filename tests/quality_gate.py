#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试质量门禁
定义测试质量标准和门禁规则
"""

import os
import sys
import json
import pytest
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger

logger = get_logger(__name__)


class TestQualityGate:
    """测试质量门禁类"""

    def __init__(self):
        self.quality_standards = {
            'coverage_threshold': 80.0,  # 覆盖率阈值
            'test_pass_rate': 95.0,      # 测试通过率阈值
            'max_execution_time': 300,   # 最大执行时间（秒）
            'min_test_count': 100,       # 最小测试数量
            'required_test_categories': [
                'unit', 'integration', 'e2e'
            ]
        }

        self.test_results = {}
        self.quality_report = {}

    def collect_test_results(self) -> Dict[str, Any]:
        """收集测试结果"""
        logger.info("开始收集测试结果...")

        # 运行测试并收集结果
        try:
            import subprocess
            result = subprocess.run([
                'python', '-m', 'pytest',
                'tests/',
                '--tb=short',
                '--json-report',
                '--json-report-file=test_results.json'
            ], capture_output=True, text=True, timeout=600)

            # 读取测试结果文件
            if os.path.exists('test_results.json'):
                with open('test_results.json', 'r', encoding='utf-8') as f:
                    self.test_results = json.load(f)
                os.remove('test_results.json')

            return self.test_results

        except Exception as e:
            logger.error(f"收集测试结果失败: {e}")
            return {}

    def check_coverage(self) -> Dict[str, Any]:
        """检查测试覆盖率"""
        logger.info("检查测试覆盖率...")

        try:
            import coverage

            # 运行覆盖率测试
            cov = coverage.Coverage()
            cov.start()

            # 运行测试
            pytest.main(['tests/', '--tb=short'])

            cov.stop()
            cov.save()

            # 生成覆盖率报告
            coverage_data = cov.report()

            # 计算覆盖率百分比
            total_statements = cov.get_data().measured_files()
            covered_statements = cov.get_data().executed_files()

            coverage_percentage = (len(covered_statements) / len(total_statements)) * 100

            return {
                'coverage_percentage': coverage_percentage,
                'total_files': len(total_statements),
                'covered_files': len(covered_statements),
                'meets_standard': coverage_percentage >= self.quality_standards['coverage_threshold']
            }

        except Exception as e:
            logger.error(f"检查覆盖率失败: {e}")
            return {'coverage_percentage': 0, 'meets_standard': False}

    def check_test_pass_rate(self) -> Dict[str, Any]:
        """检查测试通过率"""
        logger.info("检查测试通过率...")

        if not self.test_results:
            self.collect_test_results()

        if 'summary' in self.test_results:
            summary = self.test_results['summary']
            total = summary.get('total', 0)
            passed = summary.get('passed', 0)

            if total > 0:
                pass_rate = (passed / total) * 100
            else:
                pass_rate = 0

            return {
                'pass_rate': pass_rate,
                'total_tests': total,
                'passed_tests': passed,
                'meets_standard': pass_rate >= self.quality_standards['test_pass_rate']
            }

        return {'pass_rate': 0, 'meets_standard': False}

    def check_test_categories(self) -> Dict[str, Any]:
        """检查测试分类覆盖"""
        logger.info("检查测试分类覆盖...")

        test_categories = {}

        # 统计不同分类的测试数量
        for category in self.quality_standards['required_test_categories']:
            category_path = f"tests/{category}"
            if os.path.exists(category_path):
                # 计算该分类下的测试文件数量
                test_files = list(Path(category_path).rglob("test_*.py"))
                test_categories[category] = len(test_files)
            else:
                test_categories[category] = 0

        # 检查是否所有必需分类都有测试
        all_categories_covered = all(
            test_categories.get(cat, 0) > 0
            for cat in self.quality_standards['required_test_categories']
        )

        return {
            'test_categories': test_categories,
            'all_categories_covered': all_categories_covered,
            'meets_standard': all_categories_covered
        }

    def check_execution_time(self) -> Dict[str, Any]:
        """检查执行时间"""
        logger.info("检查测试执行时间...")

        if not self.test_results:
            self.collect_test_results()

        if 'summary' in self.test_results:
            duration = self.test_results['summary'].get('duration', 0)
            meets_standard = duration <= self.quality_standards['max_execution_time']

            return {
                'execution_time': duration,
                'max_allowed_time': self.quality_standards['max_execution_time'],
                'meets_standard': meets_standard
            }

        return {'execution_time': 0, 'meets_standard': False}

    def run_quality_check(self) -> Dict[str, Any]:
        """运行完整的质量检查"""
        logger.info("开始运行测试质量检查...")

        self.quality_report = {
            'coverage': self.check_coverage(),
            'pass_rate': self.check_test_pass_rate(),
            'test_categories': self.check_test_categories(),
            'execution_time': self.check_execution_time(),
            'overall_status': 'PASS'
        }

        # 检查总体状态
        all_checks_passed = all(
            check['meets_standard']
            for check in [
                self.quality_report['coverage'],
                self.quality_report['pass_rate'],
                self.quality_report['test_categories'],
                self.quality_report['execution_time']
            ]
        )

        self.quality_report['overall_status'] = 'PASS' if all_checks_passed else 'FAIL'

        return self.quality_report

    def generate_report(self) -> str:
        """生成质量报告"""
        if not self.quality_report:
            self.run_quality_check()

        report_lines = [
            "=== 测试质量门禁报告 ===",
            f"总体状态: {self.quality_report['overall_status']}",
            "",
            "详细检查结果:",
            f"1. 测试覆盖率: {self.quality_report['coverage']['coverage_percentage']:.1f}%",
            f"   状态: {'通过' if self.quality_report['coverage']['meets_standard'] else '失败'}",
            f"2. 测试通过率: {self.quality_report['pass_rate']['pass_rate']:.1f}%",
            f"   状态: {'通过' if self.quality_report['pass_rate']['meets_standard'] else '失败'}",
            f"3. 测试分类覆盖: {self.quality_report['test_categories']['test_categories']}",
            f"   状态: {'通过' if self.quality_report['test_categories']['meets_standard'] else '失败'}",
            f"4. 执行时间: {self.quality_report['execution_time']['execution_time']:.1f}秒",
            f"   状态: {'通过' if self.quality_report['execution_time']['meets_standard'] else '失败'}",
            "",
            "质量门禁标准:",
            f"   - 覆盖率阈值: {self.quality_standards['coverage_threshold']}%",
            f"   - 通过率阈值: {self.quality_standards['test_pass_rate']}%",
            f"   - 最大执行时间: {self.quality_standards['max_execution_time']}秒",
            f"   - 必需测试分类: {self.quality_standards['required_test_categories']}",
        ]

        return '\n'.join(report_lines)

    def enforce_quality_gate(self) -> bool:
        """强制执行质量门禁"""
        logger.info("强制执行测试质量门禁...")

        self.run_quality_check()

        if self.quality_report['overall_status'] == 'FAIL':
            logger.error("测试质量门禁检查失败！")
            print(self.generate_report())
            return False
        else:
            logger.info("测试质量门禁检查通过！")
            print(self.generate_report())
            return True


def main():
    """主函数"""
    quality_gate = TestQualityGate()

    # 运行质量检查
    success = quality_gate.enforce_quality_gate()

    # 根据检查结果退出
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()