#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
期待数据验证器
提供标准化的期待数据与实际数据比较机制
支持文件内容、大小、哈希值、目录结构的全面比较
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ComparisonMode(Enum):
    """比较模式枚举"""

    STRICT = "strict"  # 严格模式：所有属性必须完全匹配
    LENIENT = "lenient"  # 宽松模式：允许某些差异
    CONTENT_ONLY = "content_only"  # 仅比较内容
    STRUCTURE_ONLY = "structure_only"  # 仅比较结构


@dataclass
class FileComparisonResult:
    """文件比较结果"""

    file_path: str
    expected_exists: bool
    actual_exists: bool
    size_match: Optional[bool] = None
    hash_match: Optional[bool] = None
    content_match: Optional[bool] = None
    error_message: Optional[str] = None

    def is_match(self) -> bool:
        """判断文件是否匹配"""
        if not self.expected_exists or not self.actual_exists:
            return False

        # 如果任何比较结果为False，则不匹配
        if self.size_match is False:
            return False
        if self.hash_match is False:
            return False
        if self.content_match is False:
            return False

        return True


@dataclass
class DirectoryComparisonResult:
    """目录比较结果"""

    directory_path: str
    expected_exists: bool
    actual_exists: bool
    file_count_match: Optional[bool] = None
    file_list_match: Optional[bool] = None
    structure_match: Optional[bool] = None
    file_comparisons: List[FileComparisonResult] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.file_comparisons is None:
            self.file_comparisons = []

    def is_match(self) -> bool:
        """判断目录是否匹配"""
        if not self.expected_exists or not self.actual_exists:
            return False

        # 如果任何比较结果为False，则不匹配
        if self.file_count_match is False:
            return False
        if self.file_list_match is False:
            return False
        if self.structure_match is False:
            return False

        # 检查所有文件的匹配情况
        for file_comp in self.file_comparisons:
            if not file_comp.is_match():
                return False

        return True


@dataclass
class ValidationResult:
    """验证结果"""

    overall_success: bool
    comparison_mode: ComparisonMode
    directory_results: List[DirectoryComparisonResult]
    total_files_compared: int
    files_matched: int
    files_mismatched: int
    files_missing: int
    files_extra: int
    error_messages: List[str]

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_success": self.overall_success,
            "comparison_mode": self.comparison_mode.value,
            "total_files_compared": self.total_files_compared,
            "files_matched": self.files_matched,
            "files_mismatched": self.files_mismatched,
            "files_missing": self.files_missing,
            "files_extra": self.files_extra,
            "success_rate": self.success_rate,
            "error_messages": self.error_messages,
            "directory_results": [
                {
                    "directory_path": dr.directory_path,
                    "expected_exists": dr.expected_exists,
                    "actual_exists": dr.actual_exists,
                    "file_count_match": dr.file_count_match,
                    "file_list_match": dr.file_list_match,
                    "structure_match": dr.structure_match,
                    "file_comparisons": [
                        {
                            "file_path": fc.file_path,
                            "expected_exists": fc.expected_exists,
                            "actual_exists": fc.actual_exists,
                            "size_match": fc.size_match,
                            "hash_match": fc.hash_match,
                            "content_match": fc.content_match,
                            "is_match": fc.is_match(),
                        }
                        for fc in dr.file_comparisons
                    ],
                }
                for dr in self.directory_results
            ],
        }

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_files_compared == 0:
            return 0.0
        return (self.files_matched / self.total_files_compared) * 100


class ExpectedDataValidator:
    """期待数据验证器"""

    def __init__(self, comparison_mode: ComparisonMode = ComparisonMode.STRICT):
        """
        初始化验证器

        Args:
            comparison_mode: 比较模式
        """
        self.comparison_mode = comparison_mode

    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希值"""
        if not file_path.exists():
            return ""

        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def compare_files_content(self, file1: Path, file2: Path) -> bool:
        """比较两个文件内容是否相同"""
        if not file1.exists() or not file2.exists():
            return False

        # 比较大小
        if file1.stat().st_size != file2.stat().st_size:
            return False

        # 比较哈希值
        return self.calculate_file_hash(file1) == self.calculate_file_hash(file2)

    def compare_file(
        self, expected_file: Path, actual_file: Path
    ) -> FileComparisonResult:
        """比较单个文件"""
        result = FileComparisonResult(
            file_path=str(
                expected_file.relative_to(expected_file.parent.parent)
                if expected_file.exists()
                else str(actual_file.relative_to(actual_file.parent.parent))
            ),
            expected_exists=expected_file.exists(),
            actual_exists=actual_file.exists(),
        )

        if not result.expected_exists:
            result.error_message = "期待文件不存在"
            return result

        if not result.actual_exists:
            result.error_message = "实际文件不存在"
            return result

        # 比较文件大小
        expected_size = expected_file.stat().st_size
        actual_size = actual_file.stat().st_size
        result.size_match = expected_size == actual_size

        # 比较文件哈希值
        expected_hash = self.calculate_file_hash(expected_file)
        actual_hash = self.calculate_file_hash(actual_file)
        result.hash_match = expected_hash == actual_hash

        # 根据比较模式决定是否进行内容比较
        if self.comparison_mode in [ComparisonMode.STRICT, ComparisonMode.CONTENT_ONLY]:
            result.content_match = self.compare_files_content(
                expected_file, actual_file
            )
        else:
            result.content_match = True  # 在宽松模式下假设内容匹配

        return result

    def compare_directories(
        self, expected_dir: Path, actual_dir: Path
    ) -> DirectoryComparisonResult:
        """比较两个目录"""
        result = DirectoryComparisonResult(
            directory_path=str(
                expected_dir.relative_to(expected_dir.parent.parent)
                if expected_dir.exists()
                else str(actual_dir.relative_to(actual_dir.parent.parent))
            ),
            expected_exists=expected_dir.exists(),
            actual_exists=actual_dir.exists(),
        )

        if not result.expected_exists:
            result.error_message = "期待目录不存在"
            return result

        if not result.actual_exists:
            result.error_message = "实际目录不存在"
            return result

        # 获取文件列表
        expected_files = sorted(expected_dir.rglob("*.pdf"))
        actual_files = sorted(actual_dir.rglob("*.pdf"))

        # 比较文件数量
        result.file_count_match = len(expected_files) == len(actual_files)

        # 比较文件列表
        expected_names = {f.relative_to(expected_dir) for f in expected_files}
        actual_names = {f.relative_to(actual_dir) for f in actual_files}
        result.file_list_match = expected_names == actual_names

        # 比较目录结构（仅比较PDF文件）
        expected_structure = {
            f.relative_to(expected_dir).parent for f in expected_files
        }
        actual_structure = {f.relative_to(actual_dir).parent for f in actual_files}
        result.structure_match = expected_structure == actual_structure

        # 比较每个文件
        for expected_file in expected_files:
            relative_path = expected_file.relative_to(expected_dir)
            actual_file = actual_dir / relative_path

            file_result = self.compare_file(expected_file, actual_file)
            result.file_comparisons.append(file_result)

        return result

    def validate_expected_data(
        self, expected_base_dir: Path, actual_base_dir: Path
    ) -> ValidationResult:
        """
        验证期待数据与实际数据

        Args:
            expected_base_dir: 期待数据基础目录
            actual_base_dir: 实际数据基础目录

        Returns:
            ValidationResult: 验证结果
        """
        if not expected_base_dir.exists():
            return ValidationResult(
                overall_success=False,
                comparison_mode=self.comparison_mode,
                directory_results=[],
                total_files_compared=0,
                files_matched=0,
                files_mismatched=0,
                files_missing=0,
                files_extra=0,
                error_messages=[f"期待数据目录不存在: {expected_base_dir}"],
            )

        if not actual_base_dir.exists():
            return ValidationResult(
                overall_success=False,
                comparison_mode=self.comparison_mode,
                directory_results=[],
                total_files_compared=0,
                files_matched=0,
                files_mismatched=0,
                files_missing=0,
                files_extra=0,
                error_messages=[f"实际数据目录不存在: {actual_base_dir}"],
            )

        # 获取所有公司目录
        expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()]
        actual_company_dirs = [d for d in actual_base_dir.iterdir() if d.is_dir()]

        directory_results = []
        total_files_compared = 0
        files_matched = 0
        files_mismatched = 0
        files_missing = 0
        files_extra = 0
        error_messages = []

        # 比较每个公司目录
        for expected_company_dir in expected_company_dirs:
            company_name = expected_company_dir.name
            actual_company_dir = actual_base_dir / company_name

            dir_result = self.compare_directories(
                expected_company_dir, actual_company_dir
            )
            directory_results.append(dir_result)

            # 统计文件比较结果
            for file_comp in dir_result.file_comparisons:
                total_files_compared += 1

                if file_comp.is_match():
                    files_matched += 1
                else:
                    files_mismatched += 1

                if not file_comp.actual_exists:
                    files_missing += 1

                if file_comp.error_message:
                    error_messages.append(
                        f"{file_comp.file_path}: {file_comp.error_message}"
                    )

        # 检查多余的文件（在实际目录中但不在期待目录中）
        for actual_company_dir in actual_company_dirs:
            company_name = actual_company_dir.name
            expected_company_dir = expected_base_dir / company_name

            if not expected_company_dir.exists():
                # 这个公司目录在期待数据中不存在
                actual_files = list(actual_company_dir.rglob("*.pdf"))
                files_extra += len(actual_files)

                error_messages.append(
                    f"多余的公司目录: {company_name} (包含 {len(actual_files)} 个文件)"
                )

        # 判断整体成功
        overall_success = (
            files_mismatched == 0
            and files_missing == 0
            and files_extra == 0
            and len(error_messages) == 0
        )

        return ValidationResult(
            overall_success=overall_success,
            comparison_mode=self.comparison_mode,
            directory_results=directory_results,
            total_files_compared=total_files_compared,
            files_matched=files_matched,
            files_mismatched=files_mismatched,
            files_missing=files_missing,
            files_extra=files_extra,
            error_messages=error_messages,
        )

    def validate_single_test_case(
        self, test_case: Dict[str, Any], expected_base_dir: Path, actual_base_dir: Path
    ) -> ValidationResult:
        """
        验证单个测试用例的期待数据

        Args:
            test_case: 测试用例配置
            expected_base_dir: 期待数据基础目录
            actual_base_dir: 实际数据基础目录

        Returns:
            ValidationResult: 验证结果
        """
        stock_code = test_case.get("stock_code")
        if not stock_code:
            return ValidationResult(
                overall_success=False,
                comparison_mode=self.comparison_mode,
                directory_results=[],
                total_files_compared=0,
                files_matched=0,
                files_mismatched=0,
                files_missing=0,
                files_extra=0,
                error_messages=["测试用例缺少股票代码"],
            )

        # 查找对应的公司目录
        expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()]
        target_expected_dir = None

        for expected_company_dir in expected_company_dirs:
            # 检查目录中的文件是否包含该股票代码
            for expected_file in expected_company_dir.glob("*.pdf"):
                if stock_code in expected_file.name:
                    target_expected_dir = expected_company_dir
                    break
            if target_expected_dir:
                break

        if not target_expected_dir:
            return ValidationResult(
                overall_success=False,
                comparison_mode=self.comparison_mode,
                directory_results=[],
                total_files_compared=0,
                files_matched=0,
                files_mismatched=0,
                files_missing=0,
                files_extra=0,
                error_messages=[f"未找到股票代码 {stock_code} 对应的期待数据"],
            )

        # 查找对应的实际公司目录
        company_name = target_expected_dir.name
        target_actual_dir = actual_base_dir / company_name

        if not target_actual_dir.exists():
            return ValidationResult(
                overall_success=False,
                comparison_mode=self.comparison_mode,
                directory_results=[],
                total_files_compared=0,
                files_matched=0,
                files_mismatched=0,
                files_missing=0,
                files_extra=0,
                error_messages=[f"未找到实际数据目录: {company_name}"],
            )

        # 比较单个目录
        dir_result = self.compare_directories(target_expected_dir, target_actual_dir)

        # 统计结果
        total_files_compared = len(dir_result.file_comparisons)
        files_matched = sum(1 for fc in dir_result.file_comparisons if fc.is_match())
        files_mismatched = total_files_compared - files_matched
        files_missing = sum(
            1 for fc in dir_result.file_comparisons if not fc.actual_exists
        )
        files_extra = 0  # 单目录验证不检查多余文件

        error_messages = []
        for fc in dir_result.file_comparisons:
            if fc.error_message:
                error_messages.append(f"{fc.file_path}: {fc.error_message}")

        overall_success = dir_result.is_match()

        return ValidationResult(
            overall_success=overall_success,
            comparison_mode=self.comparison_mode,
            directory_results=[dir_result],
            total_files_compared=total_files_compared,
            files_matched=files_matched,
            files_mismatched=files_mismatched,
            files_missing=files_missing,
            files_extra=files_extra,
            error_messages=error_messages,
        )


# 便捷函数
def validate_expected_vs_actual(
    expected_dir: str, actual_dir: str, mode: str = "strict"
) -> ValidationResult:
    """
    便捷函数：验证期待数据与实际数据

    Args:
        expected_dir: 期待数据目录路径
        actual_dir: 实际数据目录路径
        mode: 比较模式（strict/lenient/content_only/structure_only）

    Returns:
        ValidationResult: 验证结果
    """
    comparison_mode = ComparisonMode(mode)
    validator = ExpectedDataValidator(comparison_mode)

    return validator.validate_expected_data(Path(expected_dir), Path(actual_dir))


def validate_test_case(
    test_case: Dict[str, Any], expected_dir: str, actual_dir: str, mode: str = "strict"
) -> ValidationResult:
    """
    便捷函数：验证单个测试用例

    Args:
        test_case: 测试用例配置
        expected_dir: 期待数据目录路径
        actual_dir: 实际数据目录路径
        mode: 比较模式

    Returns:
        ValidationResult: 验证结果
    """
    comparison_mode = ComparisonMode(mode)
    validator = ExpectedDataValidator(comparison_mode)

    return validator.validate_single_test_case(
        test_case, Path(expected_dir), Path(actual_dir)
    )
