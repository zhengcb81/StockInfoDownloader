#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化测试质量指标系统
基于测试结构分析的质量评估体系
"""

import os
import sys
import time
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# 添加当前目录到Python路径
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from src.core.logger import get_logger

def log(message):
    """记录日志"""
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
    except UnicodeEncodeError:
        # 处理编码问题
        safe_message = message.encode('gbk', errors='replace').decode('gbk')
        print(f"[{time.strftime('%H:%M:%S')}] {safe_message}")

@dataclass
class TestQualityMetric:
    """测试质量指标"""
    metric_name: str
    value: float
    target_value: float
    weight: float
    score: float
    status: str
    description: str

@dataclass
class TestQualityScore:
    """测试质量评分"""
    overall_score: float
    weighted_score: float
    metrics: List[TestQualityMetric]
    quality_level: str
    recommendations: List[str]

class SimpleTestQualityMetrics:
    """简化测试质量指标系统"""

    def __init__(self):
        self.logger = get_logger("simple_test_quality_metrics")

    def calculate_test_coverage(self) -> TestQualityMetric:
        """计算测试覆盖率"""
        log("计算测试覆盖率...")

        try:
            # 分析测试文件数量
            test_dirs = ["tests/unit", "tests/integration", "tests/e2e", "tests/validation", "tests/optimization"]
            total_test_files = 0

            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    test_files = list(test_path.rglob("test_*.py")) + list(test_path.rglob("*_test.py"))
                    total_test_files += len(test_files)

            # 分析源代码文件数量
            src_dirs = ["src"]
            total_src_files = 0

            for src_dir in src_dirs:
                src_path = Path(src_dir)
                if src_path.exists():
                    src_files = list(src_path.rglob("*.py"))
                    total_src_files += len(src_files)

            # 计算覆盖率（基于文件数量比例）
            if total_src_files > 0:
                coverage_percentage = (total_test_files / total_src_files) * 100
            else:
                coverage_percentage = 0

            target_coverage = 80.0  # 目标覆盖率80%

            # 计算得分
            if coverage_percentage >= target_coverage:
                score = 100.0
            else:
                score = (coverage_percentage / target_coverage) * 100

            status = "优秀" if score >= 90 else "良好" if score >= 70 else "一般" if score >= 50 else "需要改进"

            metric = TestQualityMetric(
                metric_name="测试覆盖率",
                value=coverage_percentage,
                target_value=target_coverage,
                weight=0.25,  # 25%权重
                score=score,
                status=status,
                description=f"测试文件数: {total_test_files}, 源代码文件数: {total_src_files}"
            )

            log(f"  测试覆盖率: {coverage_percentage:.1f}% (得分: {score:.1f})")
            return metric

        except Exception as e:
            log(f"❌ 计算测试覆盖率失败: {e}")
            return TestQualityMetric(
                metric_name="测试覆盖率",
                value=0,
                target_value=80.0,
                weight=0.25,
                score=0,
                status="计算失败",
                description=f"错误: {e}"
            )

    def calculate_test_success_rate(self) -> TestQualityMetric:
        """计算测试成功率（基于测试文件分析）"""
        log("计算测试成功率...")

        try:
            # 基于测试文件结构估算成功率
            test_dirs = ["tests/unit", "tests/integration", "tests/e2e"]
            total_test_files = 0
            estimated_success_files = 0

            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    test_files = list(test_path.rglob("test_*.py")) + list(test_path.rglob("*_test.py"))
                    total_test_files += len(test_files)

                    # 基于文件命名和结构估算成功率
                    for test_file in test_files:
                        # 简单估算：文件名包含"test"且不是调试文件的成功率较高
                        if "debug" not in test_file.name.lower() and "temp" not in test_file.name.lower():
                            estimated_success_files += 1

            if total_test_files > 0:
                success_rate = (estimated_success_files / total_test_files) * 100
            else:
                success_rate = 0

            target_success_rate = 95.0  # 目标成功率95%

            # 计算得分
            if success_rate >= target_success_rate:
                score = 100.0
            else:
                score = (success_rate / target_success_rate) * 100

            status = "优秀" if score >= 95 else "良好" if score >= 85 else "一般" if score >= 70 else "需要改进"

            metric = TestQualityMetric(
                metric_name="测试成功率",
                value=success_rate,
                target_value=target_success_rate,
                weight=0.20,  # 20%权重
                score=score,
                status=status,
                description=f"估算成功率基于测试文件结构分析"
            )

            log(f"  估算测试成功率: {success_rate:.1f}% (得分: {score:.1f})")
            return metric

        except Exception as e:
            log(f"❌ 计算测试成功率失败: {e}")
            return TestQualityMetric(
                metric_name="测试成功率",
                value=0,
                target_value=95.0,
                weight=0.20,
                score=0,
                status="计算失败",
                description=f"错误: {e}"
            )

    def calculate_test_maintainability(self) -> TestQualityMetric:
        """计算测试可维护性"""
        log("计算测试可维护性...")

        try:
            # 分析测试文件结构
            test_dirs = ["tests/unit", "tests/integration", "tests/e2e"]

            total_test_files = 0
            total_test_lines = 0

            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    test_files = list(test_path.rglob("test_*.py")) + list(test_path.rglob("*_test.py"))
                    total_test_files += len(test_files)

                    for test_file in test_files:
                        try:
                            with open(test_file, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                total_test_lines += len(lines)
                        except:
                            pass

            # 计算平均文件大小
            if total_test_files > 0:
                avg_lines_per_file = total_test_lines / total_test_files
            else:
                avg_lines_per_file = 0

            target_avg_lines = 200  # 目标平均行数200行

            # 计算得分（文件越小得分越高）
            if avg_lines_per_file <= target_avg_lines:
                score = 100.0
            else:
                score = max(0, 100 - ((avg_lines_per_file - target_avg_lines) / target_avg_lines) * 100)

            status = "优秀" if score >= 90 else "良好" if score >= 70 else "一般" if score >= 50 else "需要改进"

            metric = TestQualityMetric(
                metric_name="测试可维护性",
                value=avg_lines_per_file,
                target_value=target_avg_lines,
                weight=0.15,  # 15%权重
                score=score,
                status=status,
                description=f"测试文件数: {total_test_files}, 总代码行数: {total_test_lines}"
            )

            log(f"  平均文件大小: {avg_lines_per_file:.1f}行/文件 (得分: {score:.1f})")
            return metric

        except Exception as e:
            log(f"❌ 计算测试可维护性失败: {e}")
            return TestQualityMetric(
                metric_name="测试可维护性",
                value=999,
                target_value=200,
                weight=0.15,
                score=0,
                status="计算失败",
                description=f"错误: {e}"
            )

    def calculate_test_diversity(self) -> TestQualityMetric:
        """计算测试多样性"""
        log("计算测试多样性...")

        try:
            # 分析不同类型的测试分布
            test_types = {
                "单元测试": "tests/unit",
                "集成测试": "tests/integration",
                "端到端测试": "tests/e2e",
                "验证测试": "tests/validation",
                "优化测试": "tests/optimization"
            }

            type_counts = {}
            total_tests = 0

            for test_type, test_dir in test_types.items():
                test_path = Path(test_dir)
                if test_path.exists():
                    test_files = list(test_path.rglob("test_*.py")) + list(test_path.rglob("*_test.py"))
                    count = len(test_files)
                    type_counts[test_type] = count
                    total_tests += count
                else:
                    type_counts[test_type] = 0

            # 计算多样性得分（基于测试类型分布）
            if total_tests > 0:
                # 计算标准差，标准差越小表示分布越均匀
                counts = list(type_counts.values())
                mean = sum(counts) / len(counts)
                variance = sum((x - mean) ** 2 for x in counts) / len(counts)
                std_dev = math.sqrt(variance)

                # 计算多样性得分（标准差越小得分越高）
                max_std_dev = mean * 0.8  # 假设最大标准差为平均值的80%
                if std_dev <= max_std_dev:
                    diversity_score = 100.0
                else:
                    diversity_score = max(0, 100 - ((std_dev - max_std_dev) / max_std_dev) * 100)
            else:
                diversity_score = 0

            target_diversity = 80.0

            status = "优秀" if diversity_score >= 90 else "良好" if diversity_score >= 70 else "一般" if diversity_score >= 50 else "需要改进"

            metric = TestQualityMetric(
                metric_name="测试多样性",
                value=diversity_score,
                target_value=target_diversity,
                weight=0.10,  # 10%权重
                score=diversity_score,
                status=status,
                description=f"测试类型分布: {type_counts}"
            )

            log(f"  测试多样性得分: {diversity_score:.1f} (得分: {diversity_score:.1f})")
            return metric

        except Exception as e:
            log(f"❌ 计算测试多样性失败: {e}")
            return TestQualityMetric(
                metric_name="测试多样性",
                value=0,
                target_value=80.0,
                weight=0.10,
                score=0,
                status="计算失败",
                description=f"错误: {e}"
            )

    def calculate_test_completeness(self) -> TestQualityMetric:
        """计算测试完整性"""
        log("计算测试完整性...")

        try:
            # 检查测试目录结构完整性
            required_test_dirs = ["tests/unit", "tests/integration", "tests/e2e"]
            existing_dirs = 0

            for test_dir in required_test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    existing_dirs += 1

            completeness_percentage = (existing_dirs / len(required_test_dirs)) * 100

            target_completeness = 100.0

            # 计算得分
            if completeness_percentage >= target_completeness:
                score = 100.0
            else:
                score = (completeness_percentage / target_completeness) * 100

            status = "优秀" if score >= 100 else "良好" if score >= 80 else "一般" if score >= 60 else "需要改进"

            metric = TestQualityMetric(
                metric_name="测试完整性",
                value=completeness_percentage,
                target_value=target_completeness,
                weight=0.15,  # 15%权重
                score=score,
                status=status,
                description=f"现有测试目录: {existing_dirs}/{len(required_test_dirs)}"
            )

            log(f"  测试完整性: {completeness_percentage:.1f}% (得分: {score:.1f})")
            return metric

        except Exception as e:
            log(f"❌ 计算测试完整性失败: {e}")
            return TestQualityMetric(
                metric_name="测试完整性",
                value=0,
                target_value=100.0,
                weight=0.15,
                score=0,
                status="计算失败",
                description=f"错误: {e}"
            )

    def calculate_test_organization(self) -> TestQualityMetric:
        """计算测试组织性"""
        log("计算测试组织性...")

        try:
            # 检查测试文件命名规范
            test_dirs = ["tests/unit", "tests/integration", "tests/e2e"]
            total_test_files = 0
            well_named_files = 0

            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    test_files = list(test_path.rglob("*.py"))
                    total_test_files += len(test_files)

                    for test_file in test_files:
                        # 检查文件名是否符合测试命名规范
                        if test_file.name.startswith("test_") or test_file.name.endswith("_test.py"):
                            well_named_files += 1

            if total_test_files > 0:
                organization_percentage = (well_named_files / total_test_files) * 100
            else:
                organization_percentage = 0

            target_organization = 90.0

            # 计算得分
            if organization_percentage >= target_organization:
                score = 100.0
            else:
                score = (organization_percentage / target_organization) * 100

            status = "优秀" if score >= 95 else "良好" if score >= 85 else "一般" if score >= 70 else "需要改进"

            metric = TestQualityMetric(
                metric_name="测试组织性",
                value=organization_percentage,
                target_value=target_organization,
                weight=0.15,  # 15%权重
                score=score,
                status=status,
                description=f"规范命名文件: {well_named_files}/{total_test_files}"
            )

            log(f"  测试组织性: {organization_percentage:.1f}% (得分: {score:.1f})")
            return metric

        except Exception as e:
            log(f"❌ 计算测试组织性失败: {e}")
            return TestQualityMetric(
                metric_name="测试组织性",
                value=0,
                target_value=90.0,
                weight=0.15,
                score=0,
                status="计算失败",
                description=f"错误: {e}"
            )

    def calculate_overall_quality_score(self, metrics: List[TestQualityMetric]) -> TestQualityScore:
        """计算总体质量评分"""
        log("计算总体质量评分...")

        # 计算加权平均分
        total_weighted_score = 0
        total_weight = 0

        for metric in metrics:
            total_weighted_score += metric.score * metric.weight
            total_weight += metric.weight

        if total_weight > 0:
            weighted_score = total_weighted_score / total_weight
        else:
            weighted_score = 0

        # 计算简单平均分
        if metrics:
            overall_score = sum(metric.score for metric in metrics) / len(metrics)
        else:
            overall_score = 0

        # 确定质量等级
        if weighted_score >= 90:
            quality_level = "优秀"
        elif weighted_score >= 80:
            quality_level = "良好"
        elif weighted_score >= 70:
            quality_level = "一般"
        elif weighted_score >= 60:
            quality_level = "需要改进"
        else:
            quality_level = "较差"

        # 生成改进建议
        recommendations = self._generate_recommendations(metrics, weighted_score)

        quality_score = TestQualityScore(
            overall_score=overall_score,
            weighted_score=weighted_score,
            metrics=metrics,
            quality_level=quality_level,
            recommendations=recommendations
        )

        log(f"  总体质量评分: {overall_score:.1f}")
        log(f"  加权质量评分: {weighted_score:.1f}")
        log(f"  质量等级: {quality_level}")

        return quality_score

    def _generate_recommendations(self, metrics: List[TestQualityMetric], weighted_score: float) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于总体评分的一般建议
        if weighted_score < 70:
            recommendations.append("测试质量需要显著改进，建议全面审查测试策略")
        elif weighted_score < 80:
            recommendations.append("测试质量良好，但仍有改进空间")
        elif weighted_score < 90:
            recommendations.append("测试质量优秀，继续保持")
        else:
            recommendations.append("测试质量卓越，可以作为最佳实践")

        # 基于具体指标的改进建议
        for metric in metrics:
            if metric.score < 70:
                if metric.metric_name == "测试覆盖率":
                    recommendations.append(f"提高{metric.metric_name}: 当前{metric.value:.1f}%，目标{metric.target_value}%")
                elif metric.metric_name == "测试成功率":
                    recommendations.append(f"提高{metric.metric_name}: 修复失败的测试用例")
                elif metric.metric_name == "测试可维护性":
                    recommendations.append(f"优化{metric.metric_name}: 重构大型测试文件")
                elif metric.metric_name == "测试多样性":
                    recommendations.append(f"增强{metric.metric_name}: 平衡不同类型测试的比例")
                elif metric.metric_name == "测试完整性":
                    recommendations.append(f"完善{metric.metric_name}: 建立缺失的测试目录结构")
                elif metric.metric_name == "测试组织性":
                    recommendations.append(f"改进{metric.metric_name}: 统一测试文件命名规范")

        return recommendations

def main():
    """主函数"""
    log("开始简化测试质量指标分析...")

    quality_metrics = SimpleTestQualityMetrics()

    # 计算各项质量指标
    metrics = [
        quality_metrics.calculate_test_coverage(),
        quality_metrics.calculate_test_success_rate(),
        quality_metrics.calculate_test_maintainability(),
        quality_metrics.calculate_test_diversity(),
        quality_metrics.calculate_test_completeness(),
        quality_metrics.calculate_test_organization()
    ]

    # 计算总体质量评分
    quality_score = quality_metrics.calculate_overall_quality_score(metrics)

    # 保存分析结果
    result_data = {
        "quality_score": asdict(quality_score),
        "timestamp": time.time(),
        "system_info": {
            "platform": sys.platform,
            "python_version": sys.version
        }
    }

    result_file = "simple_test_quality_metrics_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    log(f"✅ 简化测试质量指标结果已保存: {result_file}")

    # 创建质量报告
    report_file = "simple_test_quality_metrics_report.md"
    create_quality_report(result_data, report_file)

    log(f"✅ 简化测试质量指标报告已生成: {report_file}")

    # 显示质量评分
    log("\n" + "="*50)
    log("简化测试质量指标分析完成:")
    log(f"总体评分: {quality_score.overall_score:.1f}")
    log(f"加权评分: {quality_score.weighted_score:.1f}")
    log(f"质量等级: {quality_score.quality_level}")

    log("\n改进建议:")
    for recommendation in quality_score.recommendations:
        log(f"  • {recommendation}")

    return quality_score.weighted_score >= 70

def create_quality_report(result_data: Dict[str, Any], report_file: str):
    """创建质量报告"""
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 简化测试质量指标报告\n\n")
        f.write("## 概述\n")
        f.write("本报告基于测试结构分析总结了测试质量指标的评估结果和改进建议。\n\n")

        quality_score = result_data["quality_score"]

        f.write("## 质量评分摘要\n\n")
        f.write(f"- **总体评分**: {quality_score['overall_score']:.1f}\n")
        f.write(f"- **加权评分**: {quality_score['weighted_score']:.1f}\n")
        f.write(f"- **质量等级**: {quality_score['quality_level']}\n\n")

        f.write("## 详细指标分析\n\n")
        f.write("| 指标 | 当前值 | 目标值 | 权重 | 得分 | 状态 |\n")
        f.write("|------|--------|--------|------|------|------|\n")

        for metric in quality_score['metrics']:
            f.write(f"| {metric['metric_name']} | {metric['value']:.1f} | {metric['target_value']:.1f} | {metric['weight']*100:.0f}% | {metric['score']:.1f} | {metric['status']} |\n")

        f.write("\n## 改进建议\n\n")
        for recommendation in quality_score['recommendations']:
            f.write(f"- {recommendation}\n")

        f.write("\n## 持续质量改进\n\n")
        f.write("1. **定期评估**: 每周运行质量指标分析\n")
        f.write("2. **目标设定**: 为每个指标设定改进目标\n")
        f.write("3. **监控趋势**: 跟踪质量指标的变化趋势\n")
        f.write("4. **团队协作**: 建立质量改进的团队机制\n")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)