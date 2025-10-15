#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据验证框架
提供完整的期待数据验证功能
"""

import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager, DocumentInfo


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    file_path: str
    expected_info: DocumentInfo
    actual_info: Optional[DocumentInfo]
    validation_details: Dict[str, Any]
    errors: List[str]


@dataclass
class ValidationSummary:
    """验证汇总"""
    total_files: int
    valid_files: int
    invalid_files: int
    missing_files: int
    validation_rate: float
    total_size: int
    validation_time: float


class DataValidationFramework:
    """数据验证框架"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化验证框架

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.test_results_dir = self.base_dir / "test_results"
        self.expected_results_dir = self.base_dir / "expected_results"

        # 初始化文档管理器
        self.document_manager = RealDocumentManager(base_dir)

        # 验证规则配置
        self.validation_rules = {
            "file_size": {
                "enabled": True,
                "tolerance_percent": 5.0,  # 文件大小容差百分比
                "min_size_kb": 10  # 最小文件大小（KB）
            },
            "content_hash": {
                "enabled": True,
                "algorithm": "md5"
            },
            "filename_pattern": {
                "enabled": True,
                "strict_match": False  # 是否严格匹配文件名
            },
            "document_metadata": {
                "enabled": True,
                "check_pdf_info": True,
                "check_creation_date": False
            }
        }

    def validate_file_compatibility(self, expected_file: Path, actual_file: Path) -> ValidationResult:
        """
        验证文件兼容性

        Args:
            expected_file: 预期文件路径
            actual_file: 实际文件路径

        Returns:
            验证结果
        """
        # 获取预期文件信息
        expected_docs = self.document_manager.scan_existing_documents()
        expected_info = None
        for doc in expected_docs:
            if self.document_manager.get_document_path(doc) == expected_file:
                expected_info = doc
                break

        if not expected_info:
            return ValidationResult(
                is_valid=False,
                file_path=str(actual_file),
                expected_info=None,
                actual_info=None,
                validation_details={},
                errors=[f"未找到预期文件信息: {expected_file}"]
            )

        # 创建实际文件信息
        actual_info = self._create_document_info_from_file(actual_file)

        # 执行验证
        validation_details = {}
        errors = []

        # 1. 文件存在性检查
        if not actual_file.exists():
            errors.append("实际文件不存在")
            return ValidationResult(
                is_valid=False,
                file_path=str(actual_file),
                expected_info=expected_info,
                actual_info=None,
                validation_details=validation_details,
                errors=errors
            )

        # 2. 文件大小验证
        if self.validation_rules["file_size"]["enabled"]:
            size_valid, size_details, size_errors = self._validate_file_size(expected_info, actual_info)
            validation_details["file_size"] = size_details
            errors.extend(size_errors)

        # 3. 内容哈希验证
        if self.validation_rules["content_hash"]["enabled"]:
            hash_valid, hash_details, hash_errors = self._validate_content_hash(expected_info, actual_info)
            validation_details["content_hash"] = hash_details
            errors.extend(hash_errors)

        # 4. 文件名模式验证
        if self.validation_rules["filename_pattern"]["enabled"]:
            filename_valid, filename_details, filename_errors = self._validate_filename_pattern(expected_info, actual_info)
            validation_details["filename_pattern"] = filename_details
            errors.extend(filename_errors)

        # 5. 文档元数据验证
        if self.validation_rules["document_metadata"]["enabled"]:
            metadata_valid, metadata_details, metadata_errors = self._validate_document_metadata(expected_info, actual_info)
            validation_details["document_metadata"] = metadata_details
            errors.extend(metadata_errors)

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            file_path=str(actual_file),
            expected_info=expected_info,
            actual_info=actual_info,
            validation_details=validation_details,
            errors=errors
        )

    def _create_document_info_from_file(self, file_path: Path) -> DocumentInfo:
        """从文件创建文档信息"""
        file_size = file_path.stat().st_size
        file_hash = self.document_manager.calculate_file_hash(file_path)

        # 从文件路径解析信息
        relative_path = file_path.relative_to(self.test_results_dir)
        parts = relative_path.parts

        stock_name = parts[0] if len(parts) > 1 else "未知公司"
        filename = file_path.name

        # 尝试从文件名提取股票代码
        stock_code = None
        document_type = "unknown"

        # 简单的股票代码匹配
        for code in ["300470", "301611", "000001", "002415"]:
            if code in filename:
                stock_code = code
                break

        # 文档类型判断
        if "年报" in filename or "年度报告" in filename:
            document_type = "annual_report"
        elif "半年报" in filename:
            document_type = "semi_annual_report"
        elif "一季度" in filename or "季度报告" in filename:
            document_type = "quarterly_report"
        elif "投资者关系" in filename or "调研" in filename:
            document_type = "research"
        elif "公告" in filename:
            document_type = "announcement"

        # 提取关键词
        expected_keywords = []
        if "投资者关系" in filename:
            expected_keywords.append("投资者关系")
        if "调研" in filename:
            expected_keywords.append("调研")
        if "年报" in filename:
            expected_keywords.append("年报")
        if "季度" in filename:
            expected_keywords.append("季度报告")

        return DocumentInfo(
            stock_code=stock_code,
            stock_name=stock_name,
            document_type=document_type,
            document_name=filename,
            expected_keywords=expected_keywords,
            file_size=file_size,
            file_hash=file_hash
        )

    def _validate_file_size(self, expected_info: DocumentInfo, actual_info: DocumentInfo) -> Tuple[bool, Dict[str, Any], List[str]]:
        """验证文件大小"""
        errors = []
        details = {}

        expected_size = expected_info.file_size
        actual_size = actual_info.file_size
        size_diff = abs(expected_size - actual_size)
        size_diff_percent = (size_diff / expected_size * 100) if expected_size > 0 else 100

        tolerance = self.validation_rules["file_size"]["tolerance_percent"]
        min_size_kb = self.validation_rules["file_size"]["min_size_kb"]

        details = {
            "expected_size": expected_size,
            "actual_size": actual_size,
            "size_diff": size_diff,
            "size_diff_percent": size_diff_percent,
            "tolerance": tolerance
        }

        # 检查最小文件大小
        if actual_size < min_size_kb * 1024:
            errors.append(f"文件过小: {actual_size} bytes (最小: {min_size_kb * 1024} bytes)")

        # 检查大小容差
        if size_diff_percent > tolerance:
            errors.append(f"文件大小差异过大: {size_diff_percent:.1f}% (容差: {tolerance}%)")

        return len(errors) == 0, details, errors

    def _validate_content_hash(self, expected_info: DocumentInfo, actual_info: DocumentInfo) -> Tuple[bool, Dict[str, Any], List[str]]:
        """验证内容哈希"""
        errors = []
        details = {}

        expected_hash = expected_info.file_hash
        actual_hash = actual_info.file_hash

        details = {
            "expected_hash": expected_hash,
            "actual_hash": actual_hash,
            "algorithm": self.validation_rules["content_hash"]["algorithm"],
            "match": expected_hash == actual_hash
        }

        if expected_hash != actual_hash:
            errors.append("文件内容不匹配（哈希值不同）")

        return len(errors) == 0, details, errors

    def _validate_filename_pattern(self, expected_info: DocumentInfo, actual_info: DocumentInfo) -> Tuple[bool, Dict[str, Any], List[str]]:
        """验证文件名模式"""
        errors = []
        details = {}

        expected_name = expected_info.document_name
        actual_name = actual_info.document_name

        details = {
            "expected_name": expected_name,
            "actual_name": actual_name,
            "strict_match": self.validation_rules["filename_pattern"]["strict_match"]
        }

        if self.validation_rules["filename_pattern"]["strict_match"]:
            if expected_name != actual_name:
                errors.append(f"文件名不匹配: 预期 '{expected_name}', 实际 '{actual_name}'")
        else:
            # 宽松匹配：检查核心关键词
            expected_keywords = expected_info.expected_keywords
            actual_keywords = actual_info.expected_keywords

            missing_keywords = []
            for keyword in expected_keywords:
                if keyword not in actual_name:
                    missing_keywords.append(keyword)

            if missing_keywords:
                errors.append(f"文件名缺少关键词: {missing_keywords}")

            details["expected_keywords"] = expected_keywords
            details["actual_keywords"] = actual_keywords
            details["missing_keywords"] = missing_keywords

        return len(errors) == 0, details, errors

    def _validate_document_metadata(self, expected_info: DocumentInfo, actual_info: DocumentInfo) -> Tuple[bool, Dict[str, Any], List[str]]:
        """验证文档元数据"""
        errors = []
        details = {}

        # 检查PDF文件信息
        if self.validation_rules["document_metadata"]["check_pdf_info"]:
            try:
                # 这里可以添加PDF元数据检查
                # 例如检查PDF版本、创建时间等
                details["pdf_info_checked"] = True
            except Exception as e:
                errors.append(f"PDF信息检查失败: {e}")

        # 检查创建日期
        if self.validation_rules["document_metadata"]["check_creation_date"]:
            # 这里可以添加创建时间检查
            details["creation_date_checked"] = True

        return len(errors) == 0, details, errors

    def validate_test_case(self, stock_code: str, allowed_keywords: List[str]) -> Tuple[ValidationSummary, List[ValidationResult]]:
        """
        验证测试用例

        Args:
            stock_code: 股票代码
            allowed_keywords: 允许的关键词

        Returns:
            验证汇总和详细结果
        """
        start_time = datetime.now()

        # 获取预期文档
        expected_docs = self.document_manager.find_matching_documents(stock_code, allowed_keywords)
        if not expected_docs:
            return ValidationSummary(
                total_files=0,
                valid_files=0,
                invalid_files=0,
                missing_files=0,
                validation_rate=0.0,
                total_size=0,
                validation_time=0
            ), []

        # 验证结果
        results = []
        total_size = 0

        for expected_doc in expected_docs:
            expected_path = self.document_manager.get_document_path(expected_doc)

            # 查找对应的实际文件
            actual_file = None
            company_dir = self.test_results_dir / expected_doc.stock_name

            if company_dir.exists():
                # 尝试多种匹配方式
                candidates = []
                candidates.extend(company_dir.glob(expected_doc.document_name))
                candidates.extend(company_dir.glob(f"*{expected_doc.document_name}"))
                candidates.extend(company_dir.glob(f"{expected_doc.document_name}*"))

                for candidate in candidates:
                    if candidate.is_file():
                        actual_file = candidate
                        break

            if actual_file:
                result = self.validate_file_compatibility(expected_path, actual_file)
                results.append(result)
                total_size += actual_file.stat().st_size if actual_file.exists() else 0
            else:
                # 文件缺失
                results.append(ValidationResult(
                    is_valid=False,
                    file_path=str(expected_path),
                    expected_info=expected_doc,
                    actual_info=None,
                    validation_details={},
                    errors=["实际文件不存在"]
                ))

        # 计算汇总信息
        validation_time = (datetime.now() - start_time).total_seconds()
        valid_files = sum(1 for r in results if r.is_valid)
        invalid_files = sum(1 for r in results if not r.is_valid and r.actual_info is not None)
        missing_files = sum(1 for r in results if r.actual_info is None)

        summary = ValidationSummary(
            total_files=len(results),
            valid_files=valid_files,
            invalid_files=invalid_files,
            missing_files=missing_files,
            validation_rate=(valid_files / len(results) * 100) if results else 0,
            total_size=total_size,
            validation_time=validation_time
        )

        return summary, results

    def validate_all_test_cases(self, config_file: str) -> Tuple[ValidationSummary, Dict[str, List[ValidationResult]]]:
        """
        验证所有测试用例

        Args:
            config_file: 配置文件路径

        Returns:
            总体验证汇总和详细结果
        """
        # 加载配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        test_cases = config.get("test_cases", [])
        all_results = {}
        total_files = 0
        total_valid = 0
        total_invalid = 0
        total_missing = 0
        total_size = 0
        total_time = 0

        for i, test_case in enumerate(test_cases, 1):
            stock_code = test_case["stock_code"]
            allowed_keywords = test_case.get("allowed_keywords", [])

            print(f"\n验证测试用例 {i}/{len(test_cases)}: {stock_code}")

            summary, results = self.validate_test_case(stock_code, allowed_keywords)
            case_key = f"case_{i}_{stock_code}"

            all_results[case_key] = {
                "test_case": test_case,
                "summary": summary,
                "detailed_results": results
            }

            # 累计统计
            total_files += summary.total_files
            total_valid += summary.valid_files
            total_invalid += summary.invalid_files
            total_missing += summary.missing_files
            total_size += summary.total_size
            total_time += summary.validation_time

        # 计算总体验证汇总
        overall_summary = ValidationSummary(
            total_files=total_files,
            valid_files=total_valid,
            invalid_files=total_invalid,
            missing_files=total_missing,
            validation_rate=(total_valid / total_files * 100) if total_files > 0 else 0,
            total_size=total_size,
            validation_time=total_time
        )

        return overall_summary, all_results

    def generate_validation_report(self, summary: ValidationSummary, results: Dict[str, List[ValidationResult]], output_file: str = None) -> str:
        """
        生成验证报告

        Args:
            summary: 验证汇总
            results: 详细结果
            output_file: 输出文件路径

        Returns:
            报告内容
        """
        report_lines = []

        # 报告标题
        report_lines.append("=" * 80)
        report_lines.append("数据验证报告")
        report_lines.append("=" * 80)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # 总体统计
        report_lines.append("总体统计:")
        report_lines.append(f"  总文件数: {summary.total_files}")
        report_lines.append(f"  有效文件: {summary.valid_files}")
        report_lines.append(f"  无效文件: {summary.invalid_files}")
        report_lines.append(f"  缺失文件: {summary.missing_files}")
        report_lines.append(f"  验证率: {summary.validation_rate:.1f}%")
        report_lines.append(f"  总大小: {summary.total_size / 1024:.1f} KB")
        report_lines.append(f"  验证耗时: {summary.validation_time:.2f}s")
        report_lines.append("")

        # 详细结果
        report_lines.append("详细验证结果:")
        report_lines.append("-" * 80)

        for case_key, case_data in results.items():
            test_case = case_data["test_case"]
            case_summary = case_data["summary"]
            detailed_results = case_data["detailed_results"]

            report_lines.append(f"\n测试用例: {test_case['stock_code']} - {test_case.get('description', '无描述')}")
            report_lines.append(f"  文件数: {case_summary.total_files}, 有效: {case_summary.valid_files}, 无效: {case_summary.invalid_files}, 缺失: {case_summary.missing_files}")
            report_lines.append(f"  验证率: {case_summary.validation_rate:.1f}%")

            for result in detailed_results:
                status = "✓" if result.is_valid else "✗"
                filename = Path(result.file_path).name
                report_lines.append(f"    {status} {filename}")

                if result.errors:
                    for error in result.errors:
                        report_lines.append(f"      错误: {error}")

        # 写入文件
        report_content = "\n".join(report_lines)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"验证报告已保存到: {output_path}")

        return report_content


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='数据验证框架')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--config', default='config_end2end_test_extended.json', help='配置文件路径')
    parser.add_argument('--stock-code', help='指定股票代码验证')
    parser.add_argument('--keywords', nargs='+', help='指定关键词列表')
    parser.add_argument('--report', default=None, help='报告输出文件路径')
    parser.add_argument('--rules', help='验证规则配置文件路径')

    args = parser.parse_args()

    # 创建验证框架
    framework = DataValidationFramework(args.base_dir)

    # 加载验证规则
    if args.rules and os.path.exists(args.rules):
        with open(args.rules, 'r', encoding='utf-8') as f:
            rules = json.load(f)
            framework.validation_rules.update(rules)
        print(f"已加载验证规则: {args.rules}")

    # 执行验证
    if args.stock_code and args.keywords:
        # 验证单个测试用例
        print(f"验证测试用例: {args.stock_code} ({args.keywords})")
        summary, results = framework.validate_test_case(args.stock_code, args.keywords)

        print(f"\n验证结果:")
        print(f"  总文件数: {summary.total_files}")
        print(f"  有效文件: {summary.valid_files}")
        print(f"  无效文件: {summary.invalid_files}")
        print(f"  缺失文件: {summary.missing_files}")
        print(f"  验证率: {summary.validation_rate:.1f}%")

        for result in results:
            status = "✓" if result.is_valid else "✗"
            filename = Path(result.file_path).name
            print(f"  {status} {filename}")
            for error in result.errors:
                print(f"    错误: {error}")

    else:
        # 验证所有测试用例
        print(f"验证所有测试用例: {args.config}")
        summary, all_results = framework.validate_all_test_cases(args.config)

        print(f"\n总体验证结果:")
        print(f"  总文件数: {summary.total_files}")
        print(f"  有效文件: {summary.valid_files}")
        print(f"  无效文件: {summary.invalid_files}")
        print(f"  缺失文件: {summary.missing_files}")
        print(f"  验证率: {summary.validation_rate:.1f}%")

        # 生成报告
        report_file = args.report or f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        framework.generate_validation_report(summary, all_results, report_file)

    return 0 if summary.validation_rate >= 50.0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())