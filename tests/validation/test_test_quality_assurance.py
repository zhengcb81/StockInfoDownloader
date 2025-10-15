#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试质量保证模块的单元测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.validation.test_quality_assurance import (
    QualityAnalyzer,
    QualityMetric,
    QualityResult
)


class TestQualityAnalyzer:
    """测试质量分析器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.analyzer = QualityAnalyzer()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.analyzer.test_dir == Path("tests")
        assert self.analyzer.source_dir == Path("src")
        assert self.analyzer.coverage_analyzer is not None
    
    def test_find_test_files(self):
        """测试查找测试文件"""
        test_files = self.analyzer._find_test_files()
        
        # 应该找到一些测试文件
        assert len(test_files) > 0
        
        # 所有文件都应该是测试文件
        for test_file in test_files:
            assert test_file.name.startswith('test_') or test_file.name.endswith('_test.py')
    
    def test_count_test_files(self):
        """测试统计测试文件数量"""
        file_count = self.analyzer._count_test_files()
        
        # 应该有测试文件存在
        assert file_count > 0
    
    def test_count_total_tests(self):
        """测试统计总测试数量"""
        total_tests = self.analyzer._count_total_tests()
        
        # 应该有测试存在
        assert total_tests > 0
    
    @patch('tests.validation.test_quality_assurance.CoverageAnalyzer')
    def test_analyze_test_coverage(self, mock_coverage_analyzer):
        """测试分析测试覆盖率"""
        # 模拟覆盖率分析结果
        mock_result = MagicMock()
        mock_result.overall_coverage = 85.0
        mock_result.total_files = 10
        mock_result.tested_files = 8
        mock_result.high_complexity_untested = []
        
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_coverage.return_value = mock_result
        mock_coverage_analyzer.return_value = mock_analyzer
        
        # 替换分析器的覆盖率分析器实例
        self.analyzer.coverage_analyzer = mock_analyzer
        
        # 执行分析
        metrics = self.analyzer._analyze_test_coverage()
        
        assert len(metrics) == 3
        assert metrics[0].metric_name == "函数覆盖率"
        assert metrics[0].value == 85.0
        assert metrics[0].status == "pass"
    
    def test_analyze_test_code_quality(self):
        """测试分析测试代码质量"""
        metrics = self.analyzer._analyze_test_code_quality()
        
        # 应该返回一些质量指标
        assert len(metrics) > 0
        
        # 检查指标类型
        metric_names = [metric.metric_name for metric in metrics]
        assert "断言密度" in metric_names or "注释密度" in metric_names
    
    def test_analyze_test_structure(self):
        """测试分析测试结构"""
        metrics = self.analyzer._analyze_test_structure()
        
        # 应该返回一些结构指标
        assert len(metrics) > 0
    
    def test_analyze_test_naming(self):
        """测试分析测试命名规范"""
        metrics = self.analyzer._analyze_test_naming()
        
        # 应该返回命名规范指标
        assert len(metrics) == 1
        assert metrics[0].metric_name == "命名规范符合率"
        assert 0 <= metrics[0].value <= 100
    
    def test_analyze_test_dependencies(self):
        """测试分析测试依赖"""
        metrics = self.analyzer._analyze_test_dependencies()
        
        # 应该返回依赖指标
        assert len(metrics) == 1
        assert metrics[0].metric_name == "外部依赖比例"
        assert 0 <= metrics[0].value <= 100
    
    def test_calculate_quality_score(self):
        """测试计算质量分数"""
        # 创建测试指标
        metrics = [
            QualityMetric("覆盖率", 90.0, 80.0, "pass", "高覆盖率"),
            QualityMetric("密度", 1.5, 2.0, "warning", "中等密度"),
            QualityMetric("长度", 25.0, 20.0, "fail", "函数过长")
        ]
        
        score = self.analyzer._calculate_quality_score(metrics)
        
        # 分数应该在合理范围内
        assert 0 <= score <= 100
    
    def test_identify_issues(self):
        """测试识别问题"""
        metrics = [
            QualityMetric("覆盖率", 50.0, 80.0, "fail", "低覆盖率"),
            QualityMetric("密度", 1.8, 2.0, "warning", "接近阈值"),
            QualityMetric("长度", 15.0, 20.0, "pass", "长度合适")
        ]
        
        issues = self.analyzer._identify_issues(metrics)
        
        # 应该识别出fail和warning的问题
        assert len(issues) == 2
        assert "覆盖率" in issues[0]
        assert "密度" in issues[1]
    
    def test_generate_recommendations(self):
        """测试生成改进建议"""
        metrics = [
            QualityMetric("函数覆盖率", 50.0, 80.0, "fail", "低覆盖率"),
            QualityMetric("断言密度", 0.5, 2.0, "fail", "低密度")
        ]
        issues = ["覆盖率低", "密度不足"]
        
        recommendations = self.analyzer._generate_recommendations(metrics, issues)
        
        # 应该生成具体的改进建议
        assert len(recommendations) >= 2
        assert "提高函数覆盖率" in recommendations[0]
        assert "增加断言密度" in recommendations[1]
    
    @patch('tests.validation.test_quality_assurance.CoverageAnalyzer')
    def test_analyze_test_quality_integration(self, mock_coverage_analyzer):
        """测试集成分析测试质量"""
        # 模拟覆盖率分析结果
        mock_result = MagicMock()
        mock_result.overall_coverage = 85.0
        mock_result.total_files = 10
        mock_result.tested_files = 8
        mock_result.high_complexity_untested = []
        
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_coverage.return_value = mock_result
        mock_coverage_analyzer.return_value = mock_analyzer
        
        # 替换分析器的覆盖率分析器实例
        self.analyzer.coverage_analyzer = mock_analyzer
        
        # 执行完整分析
        result = self.analyzer.analyze_test_quality()
        
        assert isinstance(result, QualityResult)
        assert result.total_tests > 0
        assert result.test_files > 0
        assert 0 <= result.quality_score <= 100
        assert len(result.metrics) > 0
    
    def test_generate_quality_report(self):
        """测试生成质量报告"""
        # 创建测试结果
        metrics = [
            QualityMetric("函数覆盖率", 85.0, 80.0, "pass", "高覆盖率"),
            QualityMetric("断言密度", 1.8, 2.0, "warning", "接近阈值")
        ]
        
        result = QualityResult(
            total_tests=100,
            test_files=20,
            quality_score=85.0,
            metrics=metrics,
            issues=["断言密度接近阈值"],
            recommendations=["增加断言密度"]
        )
        
        report = self.analyzer.generate_quality_report(result)
        
        assert isinstance(report, str)
        assert "# 测试质量保证报告" in report
        assert "函数覆盖率" in report
        assert "断言密度" in report
        assert "85.0" in report


class TestQualityAnalyzerEdgeCases:
    """测试质量分析器边缘情况测试"""
    
    def test_empty_test_directory(self):
        """测试空测试目录的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = QualityAnalyzer()
            analyzer.test_dir = Path(temp_dir)
            
            # 应该处理空目录的情况
            test_files = analyzer._find_test_files()
            assert len(test_files) == 0
            
            file_count = analyzer._count_test_files()
            assert file_count == 0
            
            total_tests = analyzer._count_total_tests()
            assert total_tests == 0
    
    def test_calculate_quality_score_empty_metrics(self):
        """测试空指标列表的质量分数计算"""
        analyzer = QualityAnalyzer()
        
        score = analyzer._calculate_quality_score([])
        assert score == 0.0
    
    def test_identify_issues_no_issues(self):
        """测试没有问题时的问题识别"""
        analyzer = QualityAnalyzer()
        
        metrics = [
            QualityMetric("覆盖率", 90.0, 80.0, "pass", "高覆盖率"),
            QualityMetric("密度", 2.5, 2.0, "pass", "高密度")
        ]
        
        issues = analyzer._identify_issues(metrics)
        assert len(issues) == 0
    
    def test_generate_recommendations_no_issues(self):
        """测试没有问题时生成建议"""
        analyzer = QualityAnalyzer()
        
        metrics = [
            QualityMetric("覆盖率", 90.0, 80.0, "pass", "高覆盖率"),
            QualityMetric("密度", 2.5, 2.0, "pass", "高密度")
        ]
        issues = []
        
        recommendations = analyzer._generate_recommendations(metrics, issues)
        
        # 应该生成保持现状的建议
        assert len(recommendations) == 1
        assert "继续保持" in recommendations[0]


class TestQualityMetric:
    """测试质量指标测试类"""
    
    def test_metric_creation(self):
        """测试指标创建"""
        metric = QualityMetric(
            metric_name="测试覆盖率",
            value=85.0,
            threshold=80.0,
            status="pass",
            description="高覆盖率"
        )
        
        assert metric.metric_name == "测试覆盖率"
        assert metric.value == 85.0
        assert metric.threshold == 80.0
        assert metric.status == "pass"
        assert metric.description == "高覆盖率"
    
    def test_metric_comparison(self):
        """测试指标比较"""
        metric1 = QualityMetric("覆盖率", 90.0, 80.0, "pass", "高")
        metric2 = QualityMetric("覆盖率", 70.0, 80.0, "fail", "低")
        
        # 检查状态判断逻辑
        assert metric1.status == "pass"
        assert metric2.status == "fail"


class TestQualityResult:
    """测试质量结果测试类"""
    
    def test_result_creation(self):
        """测试结果创建"""
        metrics = [
            QualityMetric("覆盖率", 85.0, 80.0, "pass", "高覆盖率")
        ]
        
        result = QualityResult(
            total_tests=100,
            test_files=20,
            quality_score=85.0,
            metrics=metrics,
            issues=["无重大问题"],
            recommendations=["继续保持"]
        )
        
        assert result.total_tests == 100
        assert result.test_files == 20
        assert result.quality_score == 85.0
        assert len(result.metrics) == 1
        assert len(result.issues) == 1
        assert len(result.recommendations) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])