#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试质量保证模块
实施测试质量标准和最佳实践，确保测试代码的质量和可靠性
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from tests.validation.coverage_analysis_tests import (
    CoverageAnalyzer,
)


@dataclass
class QualityMetric:
    """测试质量指标"""

    metric_name: str
    value: float
    threshold: float
    status: str  # "pass", "warning", "fail"
    description: str


@dataclass
class QualityResult:
    """测试质量分析结果"""

    total_tests: int
    test_files: int
    quality_score: float
    metrics: List[QualityMetric]
    issues: List[str]
    recommendations: List[str]


class QualityAnalyzer:
    """测试质量分析器"""

    def __init__(self):
        self.test_dir = Path("tests")
        self.source_dir = Path("src")
        self.coverage_analyzer = CoverageAnalyzer()

    def analyze_test_quality(self) -> QualityResult:
        """分析测试质量"""
        print("开始分析测试质量...")

        metrics = []
        issues = []
        recommendations = []

        # 1. 测试覆盖率分析
        coverage_metrics = self._analyze_test_coverage()
        metrics.extend(coverage_metrics)

        # 2. 测试代码质量分析
        code_quality_metrics = self._analyze_test_code_quality()
        metrics.extend(code_quality_metrics)

        # 3. 测试结构分析
        structure_metrics = self._analyze_test_structure()
        metrics.extend(structure_metrics)

        # 4. 测试命名规范分析
        naming_metrics = self._analyze_test_naming()
        metrics.extend(naming_metrics)

        # 5. 测试依赖分析
        dependency_metrics = self._analyze_test_dependencies()
        metrics.extend(dependency_metrics)

        # 计算总体质量分数
        quality_score = self._calculate_quality_score(metrics)

        # 生成问题和建议
        issues = self._identify_issues(metrics)
        recommendations = self._generate_recommendations(metrics, issues)

        # 统计测试文件数量
        test_files = self._count_test_files()

        return QualityResult(
            total_tests=self._count_total_tests(),
            test_files=test_files,
            quality_score=quality_score,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations,
        )

    def _analyze_test_coverage(self) -> List[QualityMetric]:
        """分析测试覆盖率"""
        metrics = []

        try:
            # 运行覆盖率分析
            coverage_result = self.coverage_analyzer.analyze_coverage()

            # 函数覆盖率
            func_coverage_metric = QualityMetric(
                metric_name="函数覆盖率",
                value=coverage_result.overall_coverage,
                threshold=80.0,
                status=(
                    "pass"
                    if coverage_result.overall_coverage >= 80.0
                    else (
                        "warning"
                        if coverage_result.overall_coverage >= 60.0
                        else "fail"
                    )
                ),
                description=f"源代码函数覆盖率: {coverage_result.overall_coverage:.1f}%",
            )
            metrics.append(func_coverage_metric)

            # 文件覆盖率
            file_coverage = (
                (coverage_result.tested_files / coverage_result.total_files * 100)
                if coverage_result.total_files > 0
                else 0.0
            )
            file_coverage_metric = QualityMetric(
                metric_name="文件覆盖率",
                value=file_coverage,
                threshold=90.0,
                status=(
                    "pass"
                    if file_coverage >= 90.0
                    else "warning" if file_coverage >= 70.0 else "fail"
                ),
                description=f"源代码文件覆盖率: {file_coverage:.1f}%",
            )
            metrics.append(file_coverage_metric)

            # 高复杂度函数覆盖率
            high_complexity_total = len(coverage_result.high_complexity_untested)
            high_complexity_covered = sum(
                1 for func in coverage_result.high_complexity_untested if func.is_tested
            )
            high_complexity_coverage = (
                (high_complexity_covered / high_complexity_total * 100)
                if high_complexity_total > 0
                else 100.0
            )

            high_complexity_metric = QualityMetric(
                metric_name="高复杂度函数覆盖率",
                value=high_complexity_coverage,
                threshold=95.0,
                status=(
                    "pass"
                    if high_complexity_coverage >= 95.0
                    else "warning" if high_complexity_coverage >= 80.0 else "fail"
                ),
                description=f"高复杂度函数覆盖率: {high_complexity_coverage:.1f}%",
            )
            metrics.append(high_complexity_metric)

        except Exception as e:
            print(f"覆盖率分析失败: {e}")
            metrics.append(
                QualityMetric(
                    metric_name="覆盖率分析",
                    value=0.0,
                    threshold=0.0,
                    status="fail",
                    description=f"覆盖率分析失败: {e}",
                )
            )

        return metrics

    def _analyze_test_code_quality(self) -> List[QualityMetric]:
        """分析测试代码质量"""
        metrics = []

        test_files = self._find_test_files()

        # 分析测试代码质量指标
        total_lines = 0
        total_functions = 0
        total_comments = 0
        total_asserts = 0

        for test_file in test_files:
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 统计行数
                lines = content.split("\n")
                total_lines += len(lines)

                # 统计函数数量
                function_count = len(re.findall(r"def\s+test_", content))
                total_functions += function_count

                # 统计注释行数
                comment_lines = len(
                    [
                        line
                        for line in lines
                        if line.strip().startswith("#")
                        or line.strip().startswith('"""')
                    ]
                )
                total_comments += comment_lines

                # 统计断言数量
                assert_count = len(re.findall(r"assert\s+", content))
                total_asserts += assert_count

            except Exception as e:
                print(f"分析测试文件 {test_file} 失败: {e}")

        # 计算指标
        if total_functions > 0:
            # 断言密度
            assert_density = total_asserts / total_functions
            assert_density_metric = QualityMetric(
                metric_name="断言密度",
                value=assert_density,
                threshold=2.0,
                status=(
                    "pass"
                    if assert_density >= 2.0
                    else "warning" if assert_density >= 1.0 else "fail"
                ),
                description=f"平均每个测试函数包含 {assert_density:.1f} 个断言",
            )
            metrics.append(assert_density_metric)

            # 注释密度
            comment_density = (
                total_comments / total_lines * 100 if total_lines > 0 else 0.0
            )
            comment_density_metric = QualityMetric(
                metric_name="注释密度",
                value=comment_density,
                threshold=10.0,
                status=(
                    "pass"
                    if comment_density >= 10.0
                    else "warning" if comment_density >= 5.0 else "fail"
                ),
                description=f"测试代码注释密度: {comment_density:.1f}%",
            )
            metrics.append(comment_density_metric)

        # 测试函数平均长度
        if total_functions > 0:
            avg_function_length = total_lines / total_functions
            function_length_metric = QualityMetric(
                metric_name="测试函数平均长度",
                value=avg_function_length,
                threshold=20.0,
                status=(
                    "pass"
                    if avg_function_length <= 20.0
                    else "warning" if avg_function_length <= 30.0 else "fail"
                ),
                description=f"测试函数平均长度: {avg_function_length:.1f} 行",
            )
            metrics.append(function_length_metric)

        return metrics

    def _analyze_test_structure(self) -> List[QualityMetric]:
        """分析测试结构"""
        metrics = []

        test_files = self._find_test_files()

        # 分析测试结构指标
        total_test_classes = 0
        total_test_functions = 0
        setup_methods = 0
        teardown_methods = 0

        for test_file in test_files:
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 统计测试类
                test_classes = len(re.findall(r"class\s+Test[A-Za-z0-9_]+", content))
                total_test_classes += test_classes

                # 统计测试函数
                test_functions = len(re.findall(r"def\s+test_", content))
                total_test_functions += test_functions

                # 统计setup/teardown方法
                setup_count = len(re.findall(r"def\s+setup_", content, re.IGNORECASE))
                teardown_count = len(
                    re.findall(r"def\s+teardown_", content, re.IGNORECASE)
                )
                setup_methods += setup_count
                teardown_methods += teardown_count

            except Exception as e:
                print(f"分析测试文件 {test_file} 失败: {e}")

        # 计算结构指标
        if total_test_functions > 0:
            # 测试组织度
            organization_ratio = (
                total_test_classes / total_test_functions
                if total_test_functions > 0
                else 0.0
            )
            organization_metric = QualityMetric(
                metric_name="测试组织度",
                value=organization_ratio,
                threshold=0.3,
                status=(
                    "pass"
                    if organization_ratio >= 0.3
                    else "warning" if organization_ratio >= 0.1 else "fail"
                ),
                description=f"测试组织度: {organization_ratio:.2f} (测试类/测试函数比例)",
            )
            metrics.append(organization_metric)

            # setup/teardown覆盖率
            setup_coverage = (
                (setup_methods / total_test_classes * 100)
                if total_test_classes > 0
                else 0.0
            )
            setup_metric = QualityMetric(
                metric_name="Setup方法覆盖率",
                value=setup_coverage,
                threshold=80.0,
                status=(
                    "pass"
                    if setup_coverage >= 80.0
                    else "warning" if setup_coverage >= 60.0 else "fail"
                ),
                description=f"测试类Setup方法覆盖率: {setup_coverage:.1f}%",
            )
            metrics.append(setup_metric)

        return metrics

    def _analyze_test_naming(self) -> List[QualityMetric]:
        """分析测试命名规范"""
        metrics = []

        test_files = self._find_test_files()

        # 分析命名规范
        total_test_functions = 0
        well_named_functions = 0

        for test_file in test_files:
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 提取测试函数名
                function_matches = re.findall(r"def\s+(test_[a-zA-Z0-9_]+)", content)
                total_test_functions += len(function_matches)

                # 检查命名规范
                for function_name in function_matches:
                    # 检查是否使用下划线分隔，描述性名称
                    if len(function_name.split("_")) >= 3:  # test_ + 至少两个描述词
                        well_named_functions += 1

            except Exception as e:
                print(f"分析测试文件 {test_file} 失败: {e}")

        # 命名规范符合率
        naming_conformance = (
            (well_named_functions / total_test_functions * 100)
            if total_test_functions > 0
            else 0.0
        )
        naming_metric = QualityMetric(
            metric_name="命名规范符合率",
            value=naming_conformance,
            threshold=80.0,
            status=(
                "pass"
                if naming_conformance >= 80.0
                else "warning" if naming_conformance >= 60.0 else "fail"
            ),
            description=f"测试函数命名规范符合率: {naming_conformance:.1f}%",
        )
        metrics.append(naming_metric)

        return metrics

    def _analyze_test_dependencies(self) -> List[QualityMetric]:
        """分析测试依赖"""
        metrics = []

        test_files = self._find_test_files()

        # 分析测试依赖
        total_imports = 0
        external_imports = 0

        for test_file in test_files:
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 提取导入语句
                import_pattern = r"^\s*(import|from)\s+([a-zA-Z0-9_.]+)"
                imports = re.findall(import_pattern, content, re.MULTILINE)
                total_imports += len(imports)

                # 检查外部依赖
                for import_type, module_name in imports:
                    if not module_name.startswith(
                        "tests."
                    ) and not module_name.startswith("src."):
                        external_imports += 1

            except Exception as e:
                print(f"分析测试文件 {test_file} 失败: {e}")

        # 外部依赖比例
        external_dependency_ratio = (
            (external_imports / total_imports * 100) if total_imports > 0 else 0.0
        )
        dependency_metric = QualityMetric(
            metric_name="外部依赖比例",
            value=external_dependency_ratio,
            threshold=30.0,
            status=(
                "pass"
                if external_dependency_ratio <= 30.0
                else "warning" if external_dependency_ratio <= 50.0 else "fail"
            ),
            description=f"测试外部依赖比例: {external_dependency_ratio:.1f}%",
        )
        metrics.append(dependency_metric)

        return metrics

    def _calculate_quality_score(self, metrics: List[QualityMetric]) -> float:
        """计算总体质量分数"""
        if not metrics:
            return 0.0

        # 根据指标状态计算分数
        total_weight = 0
        weighted_score = 0

        for metric in metrics:
            # 分配权重
            weight = 1.0
            if "覆盖率" in metric.metric_name:
                weight = 2.0  # 覆盖率指标权重更高
            elif "密度" in metric.metric_name:
                weight = 1.5

            # 根据状态计算分数
            if metric.status == "pass":
                score = 100.0
            elif metric.status == "warning":
                score = 70.0
            else:  # fail
                score = 30.0

            weighted_score += score * weight
            total_weight += weight

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _identify_issues(self, metrics: List[QualityMetric]) -> List[str]:
        """识别问题"""
        issues = []

        for metric in metrics:
            if metric.status == "fail":
                issues.append(
                    f"{metric.metric_name}: {metric.description} (阈值: {metric.threshold})"
                )
            elif metric.status == "warning":
                issues.append(
                    f"{metric.metric_name}: {metric.description} (接近阈值: {metric.threshold})"
                )

        return issues

    def _generate_recommendations(
        self, metrics: List[QualityMetric], issues: List[str]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 根据问题生成具体建议
        for metric in metrics:
            if metric.status == "fail":
                if "覆盖率" in metric.metric_name:
                    recommendations.append(
                        f"提高{metric.metric_name}，目标达到{metric.threshold}%以上"
                    )
                elif "密度" in metric.metric_name:
                    recommendations.append(
                        f"增加{metric.metric_name}，提高测试代码质量"
                    )
                elif "长度" in metric.metric_name:
                    recommendations.append(f"减少{metric.metric_name}，提高测试可读性")

        # 通用建议
        if len(issues) > 5:
            recommendations.append("测试质量存在多个问题，建议制定全面的测试改进计划")

        if not recommendations:
            recommendations.append("测试质量良好，继续保持现有标准和实践")

        return recommendations

    def _find_test_files(self) -> List[Path]:
        """查找所有测试文件"""
        test_files = []

        for pattern in ["**/test_*.py", "**/*_test.py"]:
            test_files.extend(self.test_dir.rglob(pattern))

        return test_files

    def _count_test_files(self) -> int:
        """统计测试文件数量"""
        return len(self._find_test_files())

    def _count_total_tests(self) -> int:
        """统计总测试数量"""
        test_files = self._find_test_files()
        total_tests = 0

        for test_file in test_files:
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 统计测试函数
                test_functions = len(re.findall(r"def\s+test_", content))
                total_tests += test_functions

            except Exception as e:
                print(f"统计测试文件 {test_file} 失败: {e}")

        return total_tests

    def generate_quality_report(self, quality_result: QualityResult) -> str:
        """生成质量报告"""
        report_lines = ["# 测试质量保证报告\n"]

        # 总体概况
        report_lines.append("## 总体概况\n")
        report_lines.append(f"- 测试文件数量: {quality_result.test_files}")
        report_lines.append(f"- 总测试数量: {quality_result.total_tests}")
        report_lines.append(f"- 总体质量分数: {quality_result.quality_score:.1f}/100\n")

        # 质量指标
        report_lines.append("## 质量指标分析\n")
        report_lines.append("| 指标名称 | 当前值 | 阈值 | 状态 | 描述 |")
        report_lines.append("|---------|--------|------|------|------|")

        for metric in quality_result.metrics:
            status_text = (
                "PASS"
                if metric.status == "pass"
                else "WARN" if metric.status == "warning" else "FAIL"
            )
            report_lines.append(
                f"| {metric.metric_name} | {metric.value:.1f} | {metric.threshold} | {status_text} | {metric.description} |"
            )

        # 问题识别
        if quality_result.issues:
            report_lines.append("\n## 识别的问题\n")
            for issue in quality_result.issues:
                report_lines.append(f"- {issue}")

        # 改进建议
        if quality_result.recommendations:
            report_lines.append("\n## 改进建议\n")
            for recommendation in quality_result.recommendations:
                report_lines.append(f"- {recommendation}")

        # 质量评级
        report_lines.append("\n## 质量评级\n")
        if quality_result.quality_score >= 90:
            report_lines.append("### 优秀 (A级)")
            report_lines.append("- 测试质量非常高")
            report_lines.append("- 继续保持现有标准")
        elif quality_result.quality_score >= 80:
            report_lines.append("### 良好 (B级)")
            report_lines.append("- 测试质量良好")
            report_lines.append("- 有少量改进空间")
        elif quality_result.quality_score >= 70:
            report_lines.append("### 一般 (C级)")
            report_lines.append("- 测试质量需要改进")
            report_lines.append("- 建议制定改进计划")
        else:
            report_lines.append("### 需要改进 (D级)")
            report_lines.append("- 测试质量存在显著问题")
            report_lines.append("- 需要立即采取行动改进")

        return "\n".join(report_lines)


# 测试质量保证运行器
test_quality_analyzer = QualityAnalyzer()


def run_test_quality_analysis() -> QualityResult:
    """运行测试质量分析"""
    analyzer = QualityAnalyzer()
    result = analyzer.analyze_test_quality()
    report = analyzer.generate_quality_report(result)

    print(report)

    # 保存报告到文件
    with open("test_quality_assurance_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("\n测试质量报告已保存到 test_quality_assurance_report.md")

    return result


class TestQualityAnalyzer:
    """QualityAnalyzer 测试类"""

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = QualityAnalyzer()
        assert analyzer.test_dir == Path("tests")
        assert analyzer.source_dir == Path("src")
        assert analyzer.coverage_analyzer is not None

    def test_calculate_quality_score(self):
        """测试计算质量分数"""
        analyzer = QualityAnalyzer()

        # 测试空指标
        assert analyzer._calculate_quality_score([]) == 0.0

        # 测试混合指标
        metrics = [
            QualityMetric("指标1", 100, 100, "pass", ""),
            QualityMetric("指标2", 50, 100, "fail", ""),
        ]

        # 权重默认为1.0
        # (100 * 1.0 + 30 * 1.0) / 2.0 = 65.0
        score = analyzer._calculate_quality_score(metrics)
        assert score == 65.0


if __name__ == "__main__":
    run_test_quality_analysis()
