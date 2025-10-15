#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试覆盖率分析模块
分析现有测试对源代码的覆盖情况，识别测试覆盖的盲点
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
import statistics


@dataclass
class FunctionCoverage:
    """函数覆盖率信息"""
    function_name: str
    file_path: str
    line_start: int
    line_end: int
    is_tested: bool
    test_files: List[str]
    complexity: int


@dataclass
class ClassCoverage:
    """类覆盖率信息"""
    class_name: str
    file_path: str
    line_start: int
    line_end: int
    is_tested: bool
    methods: List[FunctionCoverage]
    test_files: List[str]


@dataclass
class FileCoverage:
    """文件覆盖率信息"""
    file_path: str
    total_functions: int
    tested_functions: int
    total_classes: int
    tested_classes: int
    total_lines: int
    functions: List[FunctionCoverage]
    classes: List[ClassCoverage]
    coverage_percentage: float


@dataclass
class CoverageAnalysisResult:
    """覆盖率分析结果"""
    total_files: int
    tested_files: int
    total_functions: int
    tested_functions: int
    total_classes: int
    tested_classes: int
    overall_coverage: float
    file_coverage: Dict[str, FileCoverage]
    untested_functions: List[FunctionCoverage]
    untested_classes: List[ClassCoverage]
    high_complexity_untested: List[FunctionCoverage]


class CodeAnalyzer:
    """代码分析器"""
    
    def __init__(self):
        self.source_dir = Path("src")
        self.test_dir = Path("tests")
    
    def extract_functions_from_file(self, file_path: Path) -> List[FunctionCoverage]:
        """从文件中提取函数信息"""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 检查是否是类方法（有父节点且父节点是类）
                    is_method = False
                    parent = None
                    for parent_node in ast.walk(tree):
                        if hasattr(parent_node, 'body') and node in parent_node.body:
                            parent = parent_node
                            if isinstance(parent_node, ast.ClassDef):
                                is_method = True
                            break
                    
                    # 只提取独立函数，不提取类方法
                    if not is_method:
                        # 计算函数复杂度（简单方法：嵌套深度）
                        complexity = self._calculate_complexity(node)
                        
                        function = FunctionCoverage(
                            function_name=node.name,
                            file_path=str(file_path),
                            line_start=node.lineno,
                            line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                            is_tested=False,
                            test_files=[],
                            complexity=complexity
                        )
                        functions.append(function)
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"解析文件 {file_path} 时出错: {e}")
        
        return functions
    
    def extract_classes_from_file(self, file_path: Path) -> List[ClassCoverage]:
        """从文件中提取类信息"""
        classes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 提取类中的方法
                    methods = []
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            complexity = self._calculate_complexity(child)
                            method = FunctionCoverage(
                                function_name=child.name,
                                file_path=str(file_path),
                                line_start=child.lineno,
                                line_end=child.end_lineno if hasattr(child, 'end_lineno') else child.lineno,
                                is_tested=False,
                                test_files=[],
                                complexity=complexity
                            )
                            methods.append(method)
                    
                    class_info = ClassCoverage(
                        class_name=node.name,
                        file_path=str(file_path),
                        line_start=node.lineno,
                        line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                        is_tested=False,
                        methods=methods,
                        test_files=[]
                    )
                    classes.append(class_info)
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"解析文件 {file_path} 时出错: {e}")
        
        return classes
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """计算代码复杂度（简化版）"""
        complexity = 1  # 基础复杂度
        
        def count_complexity_nodes(n):
            nonlocal complexity
            if isinstance(n, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            for child in ast.iter_child_nodes(n):
                count_complexity_nodes(child)
        
        count_complexity_nodes(node)
        return complexity


class CoverageAnalyzer:
    """测试分析器"""
    
    def __init__(self):
        self.test_dir = Path("tests")
    
    def extract_test_targets(self, test_file_path: Path) -> Tuple[List[str], List[str]]:
        """从测试文件中提取测试目标"""
        tested_functions = []
        tested_classes = []
        
        try:
            with open(test_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用正则表达式匹配测试函数和类
            # 匹配测试函数：test_开头的函数
            function_pattern = r'def\s+(test_[a-zA-Z0-9_]+)\s*\('
            tested_functions = re.findall(function_pattern, content)
            
            # 匹配测试类：Test开头的类
            class_pattern = r'class\s+(Test[A-Za-z0-9_]+)\s*\('
            tested_classes = re.findall(class_pattern, content)
            
            # 提取导入的模块和类
            import_pattern = r'from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_,\s]+)'
            imports = re.findall(import_pattern, content)
            
            # 分析测试目标
            for import_module, import_items in imports:
                items = [item.strip() for item in import_items.split(',')]
                for item in items:
                    if item.startswith('Test'):
                        tested_classes.append(item)
                    elif item.startswith('test_'):
                        tested_functions.append(item)
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"解析测试文件 {test_file_path} 时出错: {e}")
        
        return tested_functions, tested_classes
    
    def find_all_test_files(self) -> List[Path]:
        """查找所有测试文件"""
        test_files = []
        
        for pattern in ['**/test_*.py', '**/*_test.py']:
            test_files.extend(self.test_dir.rglob(pattern))
        
        return test_files


class CoverageAnalysisTool:
    """覆盖率分析工具"""

    def __init__(self):
        self.code_analyzer = CodeAnalyzer()
        self.test_analyzer = CoverageAnalyzer()
    
    def analyze_coverage(self) -> CoverageAnalysisResult:
        """分析测试覆盖率"""
        print("开始分析测试覆盖率...")
        
        # 1. 分析源代码
        source_files = self._find_source_files()
        file_coverage = {}
        
        for source_file in source_files:
            print(f"分析源代码文件: {source_file}")
            file_coverage[str(source_file)] = self._analyze_file_coverage(source_file)
        
        # 2. 分析测试文件
        test_files = self.test_analyzer.find_all_test_files()
        test_targets = {}
        
        for test_file in test_files:
            print(f"分析测试文件: {test_file}")
            functions, classes = self.test_analyzer.extract_test_targets(test_file)
            test_targets[str(test_file)] = {'functions': functions, 'classes': classes}
        
        # 3. 匹配测试目标
        file_coverage = self._match_test_targets(file_coverage, test_targets)
        
        # 4. 计算总体覆盖率
        return self._calculate_overall_coverage(file_coverage)
    
    def _find_source_files(self) -> List[Path]:
        """查找所有源代码文件"""
        source_files = []
        source_dir = Path("src")
        
        for pattern in ['**/*.py']:
            source_files.extend(source_dir.rglob(pattern))
        
        return source_files
    
    def _analyze_file_coverage(self, file_path: Path) -> FileCoverage:
        """分析单个文件的覆盖率"""
        functions = self.code_analyzer.extract_functions_from_file(file_path)
        classes = self.code_analyzer.extract_classes_from_file(file_path)
        
        # 计算总行数
        total_lines = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                total_lines = len(f.readlines())
        except UnicodeDecodeError:
            pass
        
        return FileCoverage(
            file_path=str(file_path),
            total_functions=len(functions),
            tested_functions=0,
            total_classes=len(classes),
            tested_classes=0,
            total_lines=total_lines,
            functions=functions,
            classes=classes,
            coverage_percentage=0.0
        )
    
    def _match_test_targets(self, file_coverage: Dict[str, FileCoverage], 
                           test_targets: Dict[str, Dict[str, List[str]]]) -> Dict[str, FileCoverage]:
        """匹配测试目标"""
        
        for test_file, targets in test_targets.items():
            for function_name in targets['functions']:
                for file_path, coverage in file_coverage.items():
                    # 检查函数是否在源代码中
                    for function in coverage.functions:
                        if function.function_name == function_name.replace('test_', ''):
                            function.is_tested = True
                            function.test_files.append(test_file)
                    
                    # 检查类方法
                    for class_info in coverage.classes:
                        for method in class_info.methods:
                            if method.function_name == function_name.replace('test_', ''):
                                method.is_tested = True
                                method.test_files.append(test_file)
            
            for class_name in targets['classes']:
                for file_path, coverage in file_coverage.items():
                    for class_info in coverage.classes:
                        if class_info.class_name == class_name.replace('Test', ''):
                            class_info.is_tested = True
                            class_info.test_files.append(test_file)
        
        # 更新覆盖率统计
        for file_path, coverage in file_coverage.items():
            tested_functions = sum(1 for f in coverage.functions if f.is_tested)
            tested_classes = sum(1 for c in coverage.classes if c.is_tested)
            
            total_entities = coverage.total_functions + coverage.total_classes
            tested_entities = tested_functions + tested_classes
            
            coverage_percentage = (tested_entities / total_entities * 100) if total_entities > 0 else 0.0
            
            coverage.tested_functions = tested_functions
            coverage.tested_classes = tested_classes
            coverage.coverage_percentage = coverage_percentage
        
        return file_coverage
    
    def _calculate_overall_coverage(self, file_coverage: Dict[str, FileCoverage]) -> CoverageAnalysisResult:
        """计算总体覆盖率"""
        total_files = len(file_coverage)
        tested_files = sum(1 for coverage in file_coverage.values() if coverage.coverage_percentage > 0)
        
        total_functions = sum(coverage.total_functions for coverage in file_coverage.values())
        tested_functions = sum(coverage.tested_functions for coverage in file_coverage.values())
        
        total_classes = sum(coverage.total_classes for coverage in file_coverage.values())
        tested_classes = sum(coverage.tested_classes for coverage in file_coverage.values())
        
        total_entities = total_functions + total_classes
        tested_entities = tested_functions + tested_classes
        overall_coverage = (tested_entities / total_entities * 100) if total_entities > 0 else 0.0
        
        # 收集未测试的函数和类
        untested_functions = []
        untested_classes = []
        high_complexity_untested = []
        
        for coverage in file_coverage.values():
            for function in coverage.functions:
                if not function.is_tested:
                    untested_functions.append(function)
                    if function.complexity >= 5:  # 高复杂度阈值
                        high_complexity_untested.append(function)
            
            for class_info in coverage.classes:
                if not class_info.is_tested:
                    untested_classes.append(class_info)
        
        return CoverageAnalysisResult(
            total_files=total_files,
            tested_files=tested_files,
            total_functions=total_functions,
            tested_functions=tested_functions,
            total_classes=total_classes,
            tested_classes=tested_classes,
            overall_coverage=overall_coverage,
            file_coverage=file_coverage,
            untested_functions=untested_functions,
            untested_classes=untested_classes,
            high_complexity_untested=high_complexity_untested
        )
    
    def generate_coverage_report(self, analysis_result: CoverageAnalysisResult) -> str:
        """生成覆盖率报告"""
        report_lines = ["# 测试覆盖率分析报告\n"]
        
        # 总体统计
        report_lines.append("## 总体覆盖率统计\n")
        report_lines.append(f"- 源代码文件总数: {analysis_result.total_files}")
        report_lines.append(f"- 有测试覆盖的文件数: {analysis_result.tested_files}")
        report_lines.append(f"- 函数总数: {analysis_result.total_functions}")
        report_lines.append(f"- 已测试函数数: {analysis_result.tested_functions}")
        report_lines.append(f"- 类总数: {analysis_result.total_classes}")
        report_lines.append(f"- 已测试类数: {analysis_result.tested_classes}")
        report_lines.append(f"- 总体覆盖率: {analysis_result.overall_coverage:.2f}%\n")
        
        # 文件级覆盖率
        report_lines.append("## 文件级覆盖率详情\n")
        report_lines.append("| 文件路径 | 函数覆盖率 | 类覆盖率 | 总体覆盖率 |")
        report_lines.append("|---------|-----------|----------|------------|")
        
        for file_path, coverage in analysis_result.file_coverage.items():
            func_coverage = (coverage.tested_functions / coverage.total_functions * 100) if coverage.total_functions > 0 else 0.0
            class_coverage = (coverage.tested_classes / coverage.total_classes * 100) if coverage.total_classes > 0 else 0.0
            
            report_lines.append(
                f"| {file_path} | {func_coverage:.1f}% | {class_coverage:.1f}% | {coverage.coverage_percentage:.1f}% |"
            )
        
        # 未测试的高复杂度函数
        if analysis_result.high_complexity_untested:
            report_lines.append("\n## 未测试的高复杂度函数（需要优先关注）\n")
            report_lines.append("| 函数名 | 文件路径 | 复杂度 |")
            report_lines.append("|-------|---------|--------|")
            
            for function in analysis_result.high_complexity_untested:
                report_lines.append(f"| {function.function_name} | {function.file_path} | {function.complexity} |")
        
        # 未测试的函数
        if analysis_result.untested_functions:
            report_lines.append("\n## 未测试的函数\n")
            report_lines.append("| 函数名 | 文件路径 |")
            report_lines.append("|-------|---------|")
            
            for function in analysis_result.untested_functions[:20]:  # 只显示前20个
                report_lines.append(f"| {function.function_name} | {function.file_path} |")
            
            if len(analysis_result.untested_functions) > 20:
                report_lines.append(f"\n... 还有 {len(analysis_result.untested_functions) - 20} 个未测试函数")
        
        # 未测试的类
        if analysis_result.untested_classes:
            report_lines.append("\n## 未测试的类\n")
            report_lines.append("| 类名 | 文件路径 |")
            report_lines.append("|-----|---------|")
            
            for class_info in analysis_result.untested_classes:
                report_lines.append(f"| {class_info.class_name} | {class_info.file_path} |")
        
        # 改进建议
        report_lines.append("\n## 改进建议\n")
        
        if analysis_result.overall_coverage < 70:
            report_lines.append("- ⚠️ 总体覆盖率较低，建议增加测试用例")
        else:
            report_lines.append("- ✅ 总体覆盖率良好")
        
        if analysis_result.high_complexity_untested:
            report_lines.append("- ⚠️ 存在高复杂度未测试函数，建议优先编写测试")
        
        if len(analysis_result.untested_functions) > 50:
            report_lines.append("- ⚠️ 未测试函数数量较多，建议制定测试计划")
        
        return "\n".join(report_lines)


# 覆盖率分析运行器
coverage_analyzer = CoverageAnalysisTool()


def run_coverage_analysis() -> CoverageAnalysisResult:
    """运行覆盖率分析"""
    analyzer = CoverageAnalysisTool()
    result = analyzer.analyze_coverage()
    report = analyzer.generate_coverage_report(result)
    
    print(report)
    
    # 保存报告到文件
    with open("coverage_analysis_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n覆盖率报告已保存到 coverage_analysis_report.md")
    
    return result


if __name__ == "__main__":
    run_coverage_analysis()