#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试覆盖率分析模块的单元测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from tests.validation.coverage_analysis_tests import (
    CodeAnalyzer,
    CoverageAnalyzer,
    FunctionCoverage,
    ClassCoverage,
    FileCoverage,
    CoverageAnalysisResult
)


class TestCodeAnalyzer:
    """代码分析器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.analyzer = CodeAnalyzer()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """测试清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extract_functions_from_simple_file(self):
        """测试从简单文件中提取函数"""
        # 创建测试文件
        test_file = self.temp_dir / "test_simple.py"
        test_content = '''def simple_function():
    """简单函数"""
    return "hello"

def another_function(param):
    """另一个函数"""
    result = param * 2
    return result
'''
        test_file.write_text(test_content, encoding='utf-8')
        
        functions = self.analyzer.extract_functions_from_file(test_file)
        
        assert len(functions) == 2
        assert functions[0].function_name == "simple_function"
        assert functions[1].function_name == "another_function"
        assert functions[0].line_start == 1
        assert functions[1].line_start == 5
    
    def test_extract_classes_from_file(self):
        """测试从文件中提取类"""
        # 创建测试文件
        test_file = self.temp_dir / "test_class.py"
        test_content = '''
class SimpleClass:
    """简单类"""
    
    def method_one(self):
        return "method_one"
    
    def method_two(self, param):
        return param * 2

class AnotherClass:
    def another_method(self):
        return "another"
'''
        test_file.write_text(test_content, encoding='utf-8')
        
        classes = self.analyzer.extract_classes_from_file(test_file)
        
        assert len(classes) == 2
        assert classes[0].class_name == "SimpleClass"
        assert classes[1].class_name == "AnotherClass"
        assert len(classes[0].methods) == 2
        assert len(classes[1].methods) == 1
        assert classes[0].methods[0].function_name == "method_one"
        assert classes[0].methods[1].function_name == "method_two"
    
    def test_calculate_complexity(self):
        """测试计算复杂度"""
        # 创建包含复杂结构的测试文件
        test_file = self.temp_dir / "test_complex.py"
        test_content = '''
def complex_function(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                print("even")
            else:
                print("odd")
    return x
'''
        test_file.write_text(test_content, encoding='utf-8')
        
        functions = self.analyzer.extract_functions_from_file(test_file)
        
        assert len(functions) == 1
        assert functions[0].complexity >= 4  # 基础复杂度 + if + for + if


# TODO: TestAnalyzer class doesn't exist in coverage_analysis_tests.py
# Need to implement or fix this test class later
# class TestTestAnalyzer:
#     """测试分析器测试类"""
#
#     def setup_method(self):
#         """测试设置"""
#         self.analyzer = TestAnalyzer()
#         self.temp_dir = Path(tempfile.mkdtemp())
#
#     def teardown_method(self):
#         """测试清理"""
#         if self.temp_dir.exists():
#             shutil.rmtree(self.temp_dir)
#
#     def test_extract_test_targets(self):
#         """测试提取测试目标"""
#         # 创建测试文件
#         test_file = self.temp_dir / "test_example.py"
#         test_content = '''
# import unittest
# from src.services.downloader import Downloader
# from src.core.config import Config
#
# class TestDownloader(unittest.TestCase):
#     """下载器测试类"""
#
#     def test_download_success(self):
#         """测试下载成功"""
#         pass
#
  #     def test_download_failure(self):
#         """测试下载失败"""
#         pass
#
# def test_helper_function():
#     """测试辅助函数"""
#     pass
# '''
#         test_file.write_text(test_content, encoding='utf-8')
#
#         functions, classes = self.analyzer.extract_test_targets(test_file)
#
#         assert "test_download_success" in functions
#         assert "test_download_failure" in functions
#         assert "test_helper_function" in functions
#         assert "TestDownloader" in classes
#
#     def test_find_all_test_files(self):
#         """测试查找所有测试文件"""
#         # 创建测试目录结构
#         test_subdir = self.temp_dir / "subdir"
#         test_subdir.mkdir(parents=True, exist_ok=True)
#
#         # 创建测试文件
#         test_files = [
#             self.temp_dir / "test_example.py",
#             self.temp_dir / "example_test.py",
#             test_subdir / "test_nested.py"
#         ]
#
#         for test_file in test_files:
#             test_file.write_text("# Test file", encoding='utf-8')
#
#         # 临时修改测试分析器的目录
#         original_test_dir = self.analyzer.test_dir
#         self.analyzer.test_dir = self.temp_dir
#
#         try:
#             found_files = self.analyzer.find_all_test_files()
#             found_file_names = [f.name for f in found_files]
#
#             assert "test_example.py" in found_file_names
#             assert "example_test.py" in found_file_names
#             assert "test_nested.py" in found_file_names
#         finally:
#             self.analyzer.test_dir = original_test_dir


class TestCoverageAnalyzer:
    """覆盖率分析器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.analyzer = CoverageAnalyzer()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # 创建模拟的源代码和测试目录结构
        self.src_dir = self.temp_dir / "src"
        self.test_dir = self.temp_dir / "tests"
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # 临时修改分析器的目录
        self.analyzer.code_analyzer.source_dir = self.src_dir
        self.analyzer.test_analyzer.test_dir = self.test_dir
    
    def teardown_method(self):
        """测试清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_analyze_file_coverage(self):
        """测试分析文件覆盖率"""
        # 创建源代码文件
        source_file = self.src_dir / "example.py"
        source_content = '''def function_one():
    """函数一"""
    return 1

def function_two(x):
    """函数二"""
    return x * 2

class ExampleClass:
    """示例类"""
    
    def method_one(self):
        return "method_one"
    
    def method_two(self):
        return "method_two"
'''
        source_file.write_text(source_content, encoding='utf-8')
        
        coverage = self.analyzer._analyze_file_coverage(source_file)
        
        assert coverage.file_path == str(source_file)
        assert coverage.total_functions == 2  # 只有独立函数，方法不计入独立函数
        assert coverage.total_classes == 1
        assert coverage.total_lines > 0
        assert len(coverage.functions) == 2  # 独立函数
        assert len(coverage.classes) == 1
        assert coverage.classes[0].class_name == "ExampleClass"
        assert len(coverage.classes[0].methods) == 2
    
    def test_match_test_targets(self):
        """测试匹配测试目标"""
        # 创建源代码文件
        source_file = self.src_dir / "service.py"
        source_content = '''
class Service:
    def method_a(self):
        return "a"
    
    def method_b(self):
        return "b"

def utility_function():
    return "utility"
'''
        source_file.write_text(source_content, encoding='utf-8')
        
        # 创建文件覆盖率数据
        file_coverage = {}
        file_coverage[str(source_file)] = self.analyzer._analyze_file_coverage(source_file)
        
        # 创建测试目标数据
        test_targets = {
            "test_service.py": {
                "functions": ["test_method_a", "test_method_b"],
                "classes": ["TestService"]
            }
        }
        
        # 执行匹配
        updated_coverage = self.analyzer._match_test_targets(file_coverage, test_targets)
        
        coverage = updated_coverage[str(source_file)]
        
        # 检查方法是否被标记为已测试
        service_class = coverage.classes[0]
        assert service_class.class_name == "Service"
        
        # 方法应该被标记为已测试
        method_a = next(m for m in service_class.methods if m.function_name == "method_a")
        method_b = next(m for m in service_class.methods if m.function_name == "method_b")
        
        assert method_a.is_tested is True
        assert method_b.is_tested is True
        assert "test_service.py" in method_a.test_files
        assert "test_service.py" in method_b.test_files
    
    def test_calculate_overall_coverage(self):
        """测试计算总体覆盖率"""
        # 创建模拟的文件覆盖率数据
        file_coverage = {}
        
        # 文件1：部分测试
        file1_coverage = FileCoverage(
            file_path="file1.py",
            total_functions=5,
            tested_functions=3,
            total_classes=2,
            tested_classes=1,
            total_lines=100,
            functions=[],
            classes=[],
            coverage_percentage=60.0
        )
        file_coverage["file1.py"] = file1_coverage
        
        # 文件2：完全未测试
        file2_coverage = FileCoverage(
            file_path="file2.py",
            total_functions=3,
            tested_functions=0,
            total_classes=1,
            tested_classes=0,
            total_lines=50,
            functions=[],
            classes=[],
            coverage_percentage=0.0
        )
        file_coverage["file2.py"] = file2_coverage
        
        # 计算总体覆盖率
        result = self.analyzer._calculate_overall_coverage(file_coverage)
        
        assert result.total_files == 2
        assert result.tested_files == 1  # 只有file1有测试覆盖
        assert result.total_functions == 8
        assert result.tested_functions == 3
        assert result.total_classes == 3
        assert result.tested_classes == 1
        
        # 总体覆盖率 = (3+1)/(8+3) * 100 = 4/11 * 100 ≈ 36.36%
        expected_coverage = (4 / 11) * 100
        assert abs(result.overall_coverage - expected_coverage) < 0.01
    
    def test_generate_coverage_report(self):
        """测试生成覆盖率报告"""
        # 创建模拟的分析结果
        function1 = FunctionCoverage(
            function_name="function1",
            file_path="src/service.py",
            line_start=10,
            line_end=15,
            is_tested=True,
            test_files=["tests/test_service.py"],
            complexity=2
        )
        
        function2 = FunctionCoverage(
            function_name="function2",
            file_path="src/service.py",
            line_start=20,
            line_end=25,
            is_tested=False,
            test_files=[],
            complexity=6  # 高复杂度
        )
        
        class1 = ClassCoverage(
            class_name="Service",
            file_path="src/service.py",
            line_start=5,
            line_end=30,
            is_tested=True,
            methods=[function1],
            test_files=["tests/test_service.py"]
        )
        
        file_coverage = FileCoverage(
            file_path="src/service.py",
            total_functions=2,
            tested_functions=1,
            total_classes=1,
            tested_classes=1,
            total_lines=50,
            functions=[function1, function2],
            classes=[class1],
            coverage_percentage=66.67
        )
        
        analysis_result = CoverageAnalysisResult(
            total_files=1,
            tested_files=1,
            total_functions=2,
            tested_functions=1,
            total_classes=1,
            tested_classes=1,
            overall_coverage=66.67,
            file_coverage={"src/service.py": file_coverage},
            untested_functions=[function2],
            untested_classes=[],
            high_complexity_untested=[function2]
        )
        
        report = self.analyzer.generate_coverage_report(analysis_result)
        
        assert "# 测试覆盖率分析报告" in report
        assert "总体覆盖率: 66.67%" in report
        assert "function2" in report  # 未测试函数
        assert "高复杂度" in report  # 高复杂度警告


class TestCoverageAnalysisIntegration:
    """覆盖率分析集成测试"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # 创建完整的模拟项目结构
        self.src_dir = self.temp_dir / "src"
        self.test_dir = self.temp_dir / "tests"
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """测试清理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_integration_analysis(self):
        """集成测试：完整的覆盖率分析"""
        # 创建源代码
        service_file = self.src_dir / "service.py"
        service_content = '''class DataService:
    def process_data(self, data):
        """处理数据"""
        if not data:
            return None
        return data.upper()
    
    def validate_data(self, data):
        """验证数据"""
        if len(data) > 100:
            return False
        return True

def helper_function():
    """辅助函数"""
    return "helper"
'''
        service_file.write_text(service_content, encoding='utf-8')
        
        # 创建测试文件
        test_service_file = self.test_dir / "test_service.py"
        test_service_content = '''from src.service import DataService

def test_process_data():
    """测试数据处理"""
    service = DataService()
    result = service.process_data("test")
    assert result == "TEST"

def test_validate_data():
    """测试数据验证"""
    service = DataService()
    assert service.validate_data("short") is True
    assert service.validate_data("a" * 101) is False

class TestDataService:
    def test_process_empty_data(self):
        """测试处理空数据"""
        service = DataService()
        assert service.process_data("") is None
'''
        test_service_file.write_text(test_service_content, encoding='utf-8')
        
        # 创建覆盖率分析器并临时修改目录
        analyzer = CoverageAnalyzer()
        
        # 重写_find_source_files方法，使其只分析临时目录
        original_find_source_files = analyzer._find_source_files
        def mock_find_source_files():
            source_files = []
            for pattern in ['**/*.py']:
                source_files.extend(self.src_dir.rglob(pattern))
            return source_files
        
        analyzer._find_source_files = mock_find_source_files
        
        # 重写find_all_test_files方法
        original_find_all_test_files = analyzer.test_analyzer.find_all_test_files
        def mock_find_all_test_files():
            test_files = []
            for pattern in ['**/test_*.py', '**/*_test.py']:
                test_files.extend(self.test_dir.rglob(pattern))
            return test_files
        
        analyzer.test_analyzer.find_all_test_files = mock_find_all_test_files
        
        try:
            # 运行分析
            result = analyzer.analyze_coverage()
            
            # 验证结果
            assert result.total_files == 1
            assert result.tested_files == 1
            assert result.total_functions == 1  # 只有独立函数，方法不计入独立函数
            assert result.total_classes == 1
            assert result.tested_classes == 1
            
            # helper_function 应该未被测试
            assert len(result.untested_functions) == 1
            assert result.untested_functions[0].function_name == "helper_function"
        finally:
            # 恢复原始方法
            analyzer._find_source_files = original_find_source_files
            analyzer.test_analyzer.find_all_test_files = original_find_all_test_files


if __name__ == "__main__":
    pytest.main([__file__, "-v"])