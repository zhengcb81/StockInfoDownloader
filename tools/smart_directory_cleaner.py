#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能目录清理工具
集成真实文档管理功能，提供智能的测试目录清理
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager, DocumentInfo


@dataclass
class CleanupResult:
    """清理结果"""
    cleaned_files: int
    cleaned_dirs: int
    preserved_files: int
    preserved_dirs: int
    errors: List[str]
    dry_run: bool


class SmartDirectoryCleaner:
    """智能目录清理器"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化清理器

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.test_results_dir = self.base_dir / "test_results"
        self.expected_results_dir = self.base_dir / "expected_results"

        # 初始化文档管理器
        self.document_manager = RealDocumentManager(base_dir)

    def get_directory_status(self) -> Dict[str, Any]:
        """获取目录状态"""
        status = {
            "test_results_exists": self.test_results_dir.exists(),
            "expected_results_exists": self.expected_results_dir.exists(),
            "test_results": {
                "total_dirs": 0,
                "total_files": 0,
                "companies": []
            },
            "expected_results": {
                "total_dirs": 0,
                "total_files": 0,
                "companies": []
            }
        }

        # 统计测试结果目录
        if self.test_results_dir.exists():
            for company_dir in self.test_results_dir.iterdir():
                if company_dir.is_dir():
                    company_files = []
                    file_count = 0
                    for file_path in company_dir.rglob("*.pdf"):
                        if file_path.is_file():
                            company_files.append({
                                "name": file_path.name,
                                "size": file_path.stat().st_size,
                                "path": str(file_path.relative_to(self.test_results_dir))
                            })
                            file_count += 1

                    status["test_results"]["companies"].append({
                        "name": company_dir.name,
                        "files": company_files,
                        "file_count": file_count
                    })
                    status["test_results"]["total_dirs"] += 1
                    status["test_results"]["total_files"] += file_count

        # 统计预期结果目录
        if self.expected_results_dir.exists():
            for company_dir in self.expected_results_dir.iterdir():
                if company_dir.is_dir():
                    company_files = []
                    file_count = 0
                    for file_path in company_dir.rglob("*.pdf"):
                        if file_path.is_file():
                            company_files.append({
                                "name": file_path.name,
                                "size": file_path.stat().st_size,
                                "path": str(file_path.relative_to(self.expected_results_dir))
                            })
                            file_count += 1

                    status["expected_results"]["companies"].append({
                        "name": company_dir.name,
                        "files": company_files,
                        "file_count": file_count
                    })
                    status["expected_results"]["total_dirs"] += 1
                    status["expected_results"]["total_files"] += file_count

        return status

    def validate_cleanup_configuration(self, config_file: str) -> Tuple[bool, List[str]]:
        """验证清理配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            return False, [f"加载配置文件失败: {e}"]

        issues = []
        test_cases = config.get("test_cases", [])

        # 验证需要保留的测试用例
        preserve_cases = [case for case in test_cases if not case.get("delete_later", True)]

        for i, case in enumerate(preserve_cases, 1):
            stock_code = case.get("stock_code")
            allowed_keywords = case.get("allowed_keywords", [])

            # 检查是否有对应的预期文档
            matching_docs = self.document_manager.find_matching_documents(stock_code, allowed_keywords)

            if not matching_docs:
                issues.append(
                    f"保留用例 {i} (股票代码: {stock_code}): "
                    f"未找到匹配的预期文档 (关键词: {allowed_keywords})"
                )

        return len(issues) == 0, issues

    def smart_cleanup(self, config_file: str, dry_run: bool = False) -> CleanupResult:
        """
        智能清理

        Args:
            config_file: 配置文件路径
            dry_run: 是否只预览不实际执行

        Returns:
            清理结果
        """
        result = CleanupResult(
            cleaned_files=0,
            cleaned_dirs=0,
            preserved_files=0,
            preserved_dirs=0,
            errors=[],
            dry_run=dry_run
        )

        # 加载配置
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            result.errors.append(f"加载配置文件失败: {e}")
            return result

        test_cases = config.get("test_cases", [])

        # 确定需要保留的测试用例
        preserve_cases = [case for case in test_cases if not case.get("delete_later", True)]
        preserve_companies = set()

        # 获取需要保留的公司名称
        for case in preserve_cases:
            stock_code = case.get("stock_code")
            if stock_code:
                # 从文档目录中获取公司名称
                matching_docs = self.document_manager.find_matching_documents(
                    stock_code, case.get("allowed_keywords", [])
                )
                if matching_docs:
                    company_name = matching_docs[0].stock_name
                    preserve_companies.add(company_name)
                else:
                    # 如果找不到匹配文档，尝试获取股票名称
                    try:
                        from get_stock_name import get_stock_name
                        company_name = get_stock_name(stock_code)
                        if company_name and not company_name.startswith('错误'):
                            preserve_companies.add(company_name)
                    except:
                        preserve_companies.add(f"股票{stock_code}")

        # 执行清理
        if not self.test_results_dir.exists():
            return result

        # 清理测试结果目录
        for company_dir in self.test_results_dir.iterdir():
            if company_dir.is_dir():
                company_name = company_dir.name

                # 检查是否需要保留
                should_preserve = company_name in preserve_companies

                if should_preserve:
                    result.preserved_dirs += 1
                    # 计算保留的文件数
                    file_count = sum(1 for _ in company_dir.rglob("*.pdf") if _.is_file())
                    result.preserved_files += file_count
                    print(f"保留目录: {company_name} ({file_count} 个文件)")
                    continue

                # 清理目录
                if not dry_run:
                    try:
                        # 先统计文件数
                        file_count = sum(1 for _ in company_dir.rglob("*.pdf") if _.is_file())
                        shutil.rmtree(company_dir)
                        result.cleaned_dirs += 1
                        result.cleaned_files += file_count
                        print(f"清理目录: {company_name} ({file_count} 个文件)")
                    except Exception as e:
                        error_msg = f"清理目录 {company_name} 失败: {e}"
                        result.errors.append(error_msg)
                        print(f"错误: {error_msg}")
                else:
                    # 干运行时只计数
                    result.cleaned_dirs += 1
                    file_count = sum(1 for _ in company_dir.rglob("*.pdf") if _.is_file())
                    result.cleaned_files += file_count
                    print(f"[预览] 将清理目录: {company_name} ({file_count} 个文件)")

        return result

    def restore_expected_documents(self, dry_run: bool = False) -> Tuple[int, List[str]]:
        """
        从预期结果目录恢复文档到测试结果目录

        Args:
            dry_run: 是否只预览不实际执行

        Returns:
            (恢复的文件数, 错误列表)
        """
        restored_files = 0
        errors = []

        if not self.expected_results_dir.exists():
            errors.append("预期结果目录不存在")
            return restored_files, errors

        # 扫描预期结果目录中的所有文档
        existing_docs = self.document_manager.scan_existing_documents()

        for doc_info in existing_docs:
            source_path = self.document_manager.get_document_path(doc_info)

            if not source_path.exists():
                errors.append(f"源文件不存在: {source_path}")
                continue

            # 确定目标路径
            target_company_dir = self.test_results_dir / doc_info.stock_name
            target_file = target_company_dir / doc_info.document_name

            # 检查目标文件是否已存在
            if target_file.exists():
                # 验证文件是否相同
                if self.document_manager.calculate_file_hash(target_file) == doc_info.file_hash:
                    print(f"文件已存在且相同: {doc_info.document_name}")
                    continue
                else:
                    print(f"文件已存在但不同，将覆盖: {doc_info.document_name}")

            # 复制文件
            if not dry_run:
                try:
                    target_company_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_file)

                    # 验证复制
                    if target_file.exists():
                        actual_size = target_file.stat().st_size
                        actual_hash = self.document_manager.calculate_file_hash(target_file)

                        if actual_size == doc_info.file_size and actual_hash == doc_info.file_hash:
                            restored_files += 1
                            print(f"成功恢复文档: {doc_info.document_name}")
                        else:
                            errors.append(f"文档验证失败: {doc_info.document_name}")
                            target_file.unlink()
                    else:
                        errors.append(f"复制失败: {doc_info.document_name}")
                except Exception as e:
                    errors.append(f"复制文档时出错: {e}")
            else:
                print(f"[预览] 将恢复文档: {doc_info.document_name}")
                restored_files += 1

        return restored_files, errors


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='智能目录清理工具')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--config', default='config_end2end_test.json', help='配置文件路径')
    parser.add_argument('--dry-run', action='store_true', help='只预览不实际执行')
    parser.add_argument('--status', action='store_true', help='只显示目录状态')
    parser.add_argument('--validate', action='store_true', help='验证清理配置')
    parser.add_argument('--restore', action='store_true', help='从预期结果恢复文档')

    args = parser.parse_args()

    cleaner = SmartDirectoryCleaner(args.base_dir)

    if args.status:
        # 显示目录状态
        status = cleaner.get_directory_status()
        print("=== 目录状态 ===")
        print(f"基础目录: {args.base_dir}")
        print(f"测试结果目录: {status['test_results_exists']}")
        print(f"预期结果目录: {status['expected_results_exists']}")

        print(f"\n测试结果目录:")
        print(f"  公司目录数: {status['test_results']['total_dirs']}")
        print(f"  文件总数: {status['test_results']['total_files']}")
        for company in status['test_results']['companies']:
            print(f"  - {company['name']}: {company['file_count']} 个文件")

        print(f"\n预期结果目录:")
        print(f"  公司目录数: {status['expected_results']['total_dirs']}")
        print(f"  文件总数: {status['expected_results']['total_files']}")
        for company in status['expected_results']['companies']:
            print(f"  - {company['name']}: {company['file_count']} 个文件")
        return

    if args.validate:
        # 验证清理配置
        valid, issues = cleaner.validate_cleanup_configuration(args.config)
        if valid:
            print("清理配置验证通过")
        else:
            print("清理配置验证失败:")
            for issue in issues:
                print(f"  - {issue}")
        return

    if args.restore:
        # 从预期结果恢复文档
        print("从预期结果恢复文档...")
        restored_files, errors = cleaner.restore_expected_documents(args.dry_run)

        print(f"\n恢复结果:")
        print(f"  恢复文件: {restored_files} 个")
        print(f"  错误数: {len(errors)} 个")
        if errors:
            print(f"  错误详情:")
            for error in errors:
                print(f"    - {error}")
        return

    # 执行智能清理
    print("执行智能清理...")
    result = cleaner.smart_cleanup(args.config, args.dry_run)

    print(f"\n清理结果:")
    print(f"  清理文件: {result.cleaned_files} 个")
    print(f"  清理目录: {result.cleaned_dirs} 个")
    print(f"  保留文件: {result.preserved_files} 个")
    print(f"  保留目录: {result.preserved_dirs} 个")
    print(f"  错误数: {len(result.errors)} 个")
    print(f"  干运行模式: {result.dry_run}")

    if result.errors:
        print(f"\n错误详情:")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()