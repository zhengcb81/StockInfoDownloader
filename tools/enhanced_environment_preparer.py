#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强环境准备工具
确保每次测试前环境完全符合测试说明要求
"""

import os
import sys
import json
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager
from smart_directory_cleaner import SmartDirectoryCleaner
from data_validation_framework import DataValidationFramework


class EnhancedEnvironmentPreparer:
    """增强环境准备器"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化环境准备器

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.test_results_dir = self.base_dir / "test_results"
        self.expected_results_dir = self.base_dir / "expected_results"

        # 初始化工具
        self.document_manager = RealDocumentManager(base_dir)
        self.cleaner = SmartDirectoryCleaner(base_dir)
        self.validator = DataValidationFramework(base_dir)

        # 环境准备检查清单
        self.checklist = {
            "directory_structure": {
                "name": "目录结构检查",
                "description": "确保所有必需的目录存在",
                "required": True,
                "status": "pending"
            },
            "expected_documents": {
                "name": "预期文档检查",
                "description": "确保预期结果目录中有足够的文档",
                "required": True,
                "status": "pending"
            },
            "document_integrity": {
                "name": "文档完整性检查",
                "description": "验证所有文档的完整性和可访问性",
                "required": True,
                "status": "pending"
            },
            "configuration_validation": {
                "name": "配置文件验证",
                "description": "验证测试配置文件的正确性",
                "required": True,
                "status": "pending"
            },
            "clean_state": {
                "name": "清洁状态检查",
                "description": "确保测试结果目录处于清洁状态",
                "required": True,
                "status": "pending"
            },
            "permissions_check": {
                "name": "权限检查",
                "description": "确保有足够的读写权限",
                "required": True,
                "status": "pending"
            }
        }

        # 环境准备结果
        self.preparation_result = {
            "start_time": datetime.now(),
            "end_time": None,
            "duration": None,
            "success": False,
            "checklist_results": {},
            "errors": [],
            "warnings": [],
            "actions_taken": [],
            "environment_state": {}
        }

    def prepare_environment(self, config_file: str = "config_end2end_test.json",
                           force_clean: bool = False) -> Dict[str, Any]:
        """
        准备测试环境

        Args:
            config_file: 配置文件路径
            force_clean: 是否强制清理

        Returns:
            环境准备结果
        """
        print("=== 开始环境准备 ===")
        print(f"开始时间: {self.preparation_result['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"配置文件: {config_file}")
        print(f"强制清理: {force_clean}")

        try:
            # 1. 目录结构检查
            self._check_directory_structure()

            # 2. 权限检查
            self._check_permissions()

            # 3. 预期文档检查
            self._check_expected_documents()

            # 4. 文档完整性检查
            self._check_document_integrity()

            # 5. 配置文件验证
            self._validate_configuration(config_file)

            # 6. 清洁状态准备
            if force_clean or self._needs_cleaning():
                self._prepare_clean_state(config_file)

            # 7. 最终验证
            self._final_verification()

            # 完成准备
            self.preparation_result["end_time"] = datetime.now()
            self.preparation_result["duration"] = (
                self.preparation_result["end_time"] - self.preparation_result["start_time"]
            ).total_seconds()
            self.preparation_result["success"] = all(
                result["status"] == "passed"
                for result in self.preparation_result["checklist_results"].values()
                if self.checklist[result["name"]]["required"]
            )

            print(f"\n=== 环境准备完成 ===")
            print(f"结束时间: {self.preparation_result['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"准备耗时: {self.preparation_result['duration']:.2f}秒")
            print(f"准备状态: {'成功' if self.preparation_result['success'] else '失败'}")

            return self.preparation_result

        except Exception as e:
            self.preparation_result["errors"].append(f"环境准备异常: {e}")
            self.preparation_result["end_time"] = datetime.now()
            self.preparation_result["success"] = False

            print(f"\n环境准备失败: {e}")
            return self.preparation_result

    def _check_directory_structure(self):
        """检查目录结构"""
        print("\n检查目录结构...")

        required_dirs = [
            self.base_dir,
            self.test_results_dir,
            self.expected_results_dir
        ]

        missing_dirs = []
        created_dirs = []

        for dir_path in required_dirs:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                missing_dirs.append(str(dir_path))
                created_dirs.append(str(dir_path))
                print(f"  创建目录: {dir_path}")
            else:
                print(f"  目录已存在: {dir_path}")

        # 检查目录权限
        if not os.access(self.test_results_dir, os.W_OK):
            raise Exception(f"测试结果目录无写入权限: {self.test_results_dir}")

        if not os.access(self.expected_results_dir, os.R_OK):
            raise Exception(f"预期结果目录无读取权限: {self.expected_results_dir}")

        status = "passed" if not missing_dirs else "passed_with_creations"
        self.checklist["directory_structure"]["status"] = status

        self.preparation_result["checklist_results"]["directory_structure"] = {
            "status": status,
            "missing_dirs": missing_dirs,
            "created_dirs": created_dirs,
            "required_dirs": [str(d) for d in required_dirs]
        }

        if created_dirs:
            self.preparation_result["actions_taken"].append(f"创建了 {len(created_dirs)} 个目录")

        print(f"  目录结构检查: {status}")

    def _check_permissions(self):
        """检查权限"""
        print("\n检查权限...")

        permission_issues = []

        # 检查读取权限
        try:
            test_files = [
                self.expected_results_dir,
                self.test_results_dir
            ]
            for test_file in test_files:
                if not os.access(test_file, os.R_OK):
                    permission_issues.append(f"无读取权限: {test_file}")
        except Exception as e:
            permission_issues.append(f"权限检查异常: {e}")

        # 检查写入权限
        if not os.access(self.test_results_dir, os.W_OK):
            permission_issues.append(f"无写入权限: {self.test_results_dir}")

        # 检查执行权限（目录）
        for test_dir in [self.test_results_dir, self.expected_results_dir]:
            if test_dir.exists() and not os.access(test_dir, os.X_OK):
                permission_issues.append(f"无执行权限: {test_dir}")

        status = "passed" if not permission_issues else "failed"
        self.checklist["permissions_check"]["status"] = status

        self.preparation_result["checklist_results"]["permissions_check"] = {
            "status": status,
            "issues": permission_issues
        }

        if permission_issues:
            self.preparation_result["errors"].extend(permission_issues)

        print(f"  权限检查: {status}")
        if permission_issues:
            for issue in permission_issues:
                print(f"    问题: {issue}")

    def _check_expected_documents(self):
        """检查预期文档"""
        print("\n检查预期文档...")

        try:
            documents = self.document_manager.scan_existing_documents()
            doc_count = len(documents)

            print(f"  扫描到 {doc_count} 个预期文档")

            if doc_count < 3:
                self.preparation_result["warnings"].append(f"预期文档数量较少 ({doc_count} 个)，建议增加更多测试文档")

            # 检查文档分布
            stock_codes = set(doc.stock_code for doc in documents)
            document_types = set(doc.document_type for doc in documents)

            print(f"  覆盖股票: {', '.join(stock_codes)}")
            print(f"  文档类型: {', '.join(document_types)}")

            status = "passed" if doc_count >= 1 else "failed"
            self.checklist["expected_documents"]["status"] = status

            self.preparation_result["checklist_results"]["expected_documents"] = {
                "status": status,
                "document_count": doc_count,
                "stock_codes": list(stock_codes),
                "document_types": list(document_types),
                "documents": [
                    {
                        "stock_code": doc.stock_code,
                        "stock_name": doc.stock_name,
                        "document_type": doc.document_type,
                        "document_name": doc.document_name,
                        "file_size": doc.file_size
                    }
                    for doc in documents
                ]
            }

        except Exception as e:
            status = "failed"
            self.checklist["expected_documents"]["status"] = status
            self.preparation_result["errors"].append(f"预期文档检查失败: {e}")

        print(f"  预期文档检查: {status}")

    def _check_document_integrity(self):
        """检查文档完整性"""
        print("\n检查文档完整性...")

        try:
            documents = self.document_manager.scan_existing_documents()
            integrity_issues = []
            valid_docs = 0

            for doc in documents:
                doc_path = self.document_manager.get_document_path(doc)

                if not doc_path.exists():
                    integrity_issues.append(f"文档文件不存在: {doc_path}")
                    continue

                # 检查文件大小
                if doc.file_size == 0:
                    integrity_issues.append(f"文档文件为空: {doc_path}")
                    continue

                # 检查文件哈希
                actual_hash = self.document_manager.calculate_file_hash(doc_path)
                if doc.file_hash != actual_hash:
                    integrity_issues.append(f"文档哈希不匹配: {doc_path}")
                    continue

                valid_docs += 1

            print(f"  有效文档: {valid_docs}/{len(documents)}")

            status = "passed" if not integrity_issues else "failed"
            self.checklist["document_integrity"]["status"] = status

            self.preparation_result["checklist_results"]["document_integrity"] = {
                "status": status,
                "total_documents": len(documents),
                "valid_documents": valid_docs,
                "integrity_issues": integrity_issues
            }

            if integrity_issues:
                self.preparation_result["errors"].extend(integrity_issues)

        except Exception as e:
            status = "failed"
            self.checklist["document_integrity"]["status"] = status
            self.preparation_result["errors"].append(f"文档完整性检查失败: {e}")

        print(f"  文档完整性检查: {status}")

    def _validate_configuration(self, config_file: str):
        """验证配置文件"""
        print("\n验证配置文件...")

        try:
            if not os.path.exists(config_file):
                raise Exception(f"配置文件不存在: {config_file}")

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 验证配置结构
            required_fields = ["save_dir", "expected_result_dir", "test_cases"]
            missing_fields = []

            for field in required_fields:
                if field not in config:
                    missing_fields.append(field)

            if missing_fields:
                raise Exception(f"配置文件缺少必需字段: {missing_fields}")

            # 验证测试用例
            test_cases = config.get("test_cases", [])
            if not test_cases:
                raise Exception("配置文件中没有测试用例")

            print(f"  配置文件: {config_file}")
            print(f"  测试用例数: {len(test_cases)}")

            # 使用文档管理器验证配置
            valid, issues = self.document_manager.validate_test_configuration(config_file)

            status = "passed" if valid else "failed"
            self.checklist["configuration_validation"]["status"] = status

            self.preparation_result["checklist_results"]["configuration_validation"] = {
                "status": status,
                "config_file": config_file,
                "test_cases_count": len(test_cases),
                "validation_issues": issues
            }

            if not valid:
                self.preparation_result["errors"].extend(issues)

        except Exception as e:
            status = "failed"
            self.checklist["configuration_validation"]["status"] = status
            self.preparation_result["errors"].append(f"配置验证失败: {e}")

        print(f"  配置文件验证: {status}")

    def _needs_cleaning(self) -> bool:
        """检查是否需要清理"""
        print("\n检查是否需要清理...")

        if not self.test_results_dir.exists():
            print("  测试结果目录不存在，无需清理")
            return False

        # 检查测试结果目录内容
        company_dirs = [d for d in self.test_results_dir.iterdir() if d.is_dir()]
        total_files = 0

        for company_dir in company_dirs:
            files = [f for f in company_dir.iterdir() if f.is_file()]
            total_files += len(files)

        print(f"  测试结果目录中有 {len(company_dirs)} 个公司目录")
        print(f"  总文件数: {total_files}")

        # 如果有文件，建议清理
        needs_cleaning = total_files > 0
        print(f"  需要清理: {'是' if needs_cleaning else '否'}")

        return needs_cleaning

    def _prepare_clean_state(self, config_file: str):
        """准备清洁状态"""
        print("\n准备清洁状态...")

        try:
            # 使用智能清理工具
            result = self.cleaner.smart_cleanup(config_file, dry_run=False)

            print(f"  清理结果:")
            print(f"    清理文件: {result.cleaned_files} 个")
            print(f"    清理目录: {result.cleaned_dirs} 个")
            print(f"    保留文件: {result.preserved_files} 个")
            print(f"    保留目录: {result.preserved_dirs} 个")

            if result.errors:
                print(f"    错误: {len(result.errors)} 个")
                for error in result.errors:
                    print(f"      - {error}")

            # 从预期结果恢复文档
            print("  恢复预期文档...")
            restored_files, restore_errors = self.cleaner.restore_expected_documents(dry_run=False)

            print(f"  恢复结果:")
            print(f"    恢复文件: {restored_files} 个")
            if restore_errors:
                print(f"    错误: {len(restore_errors)} 个")
                for error in restore_errors:
                    print(f"      - {error}")

            status = "passed" if not result.errors and not restore_errors else "completed_with_warnings"
            self.checklist["clean_state"]["status"] = status

            self.preparation_result["checklist_results"]["clean_state"] = {
                "status": status,
                "cleanup_result": {
                    "cleaned_files": result.cleaned_files,
                    "cleaned_dirs": result.cleaned_dirs,
                    "preserved_files": result.preserved_files,
                    "preserved_dirs": result.preserved_dirs,
                    "errors": result.errors
                },
                "restore_result": {
                    "restored_files": restored_files,
                    "restore_errors": restore_errors
                }
            }

            if result.errors:
                self.preparation_result["errors"].extend(result.errors)

            if restore_errors:
                self.preparation_result["errors"].extend(restore_errors)

            self.preparation_result["actions_taken"].append(f"清理了测试结果目录")

        except Exception as e:
            status = "failed"
            self.checklist["clean_state"]["status"] = status
            self.preparation_result["errors"].append(f"清洁状态准备失败: {e}")

        print(f"  清洁状态准备: {status}")

    def _final_verification(self):
        """最终验证"""
        print("\n进行最终验证...")

        final_issues = []

        # 重新检查所有必需项
        for item_key, item_info in self.checklist.items():
            if item_info["required"] and item_info["status"] != "passed":
                final_issues.append(f"必需项未通过: {item_info['name']}")

        # 验证环境状态
        try:
            # 检查测试结果目录状态
            test_status = self.cleaner.get_directory_status()
            self.preparation_result["environment_state"]["test_results"] = test_status

            # 检查文档管理器状态
            doc_status = {
                "total_documents": len(self.document_manager.scan_existing_documents()),
                "catalog_exists": self.document_manager.document_catalog_file.exists()
            }
            self.preparation_result["environment_state"]["documents"] = doc_status

        except Exception as e:
            final_issues.append(f"环境状态检查失败: {e}")

        status = "passed" if not final_issues else "failed"
        print(f"  最终验证: {status}")

        if final_issues:
            print("  最终问题:")
            for issue in final_issues:
                print(f"    - {issue}")
            self.preparation_result["errors"].extend(final_issues)

    def generate_preparation_report(self) -> str:
        """生成环境准备报告"""
        report_lines = [
            "# 环境准备报告",
            f"准备时间: {self.preparation_result['start_time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"准备状态: {'成功' if self.preparation_result['success'] else '失败'}",
            f"准备耗时: {self.preparation_result['duration'] or 0:.2f}秒",
            "",
            "## 检查清单结果",
            ""
        ]

        for item_name, result in self.preparation_result["checklist_results"].items():
            item_info = self.checklist[item_name]
            status_icon = "✓" if result["status"] == "passed" else "✗"
            required_mark = " (必需)" if item_info["required"] else " (可选)"
            report_lines.append(f"### {status_icon} {item_info['name']}{required_mark}")
            report_lines.append(f"**状态**: {result['status']}")
            report_lines.append(f"**描述**: {item_info['description']}")
            report_lines.append("")

        if self.preparation_result["errors"]:
            report_lines.extend([
                "## 错误信息",
                ""
            ])
            for i, error in enumerate(self.preparation_result["errors"], 1):
                report_lines.append(f"{i}. {error}")
            report_lines.append("")

        if self.preparation_result["warnings"]:
            report_lines.extend([
                "## 警告信息",
                ""
            ])
            for i, warning in enumerate(self.preparation_result["warnings"], 1):
                report_lines.append(f"{i}. {warning}")
            report_lines.append("")

        if self.preparation_result["actions_taken"]:
            report_lines.extend([
                "## 执行的操作",
                ""
            ])
            for i, action in enumerate(self.preparation_result["actions_taken"], 1):
                report_lines.append(f"{i}. {action}")
            report_lines.append("")

        return "\n".join(report_lines)

    def save_preparation_report(self, output_file: str = None):
        """保存环境准备报告"""
        if not output_file:
            output_file = self.base_dir / "environment_preparation_report.md"

        report = self.generate_preparation_report()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"环境准备报告已保存到: {output_file}")
        return str(output_file)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='增强环境准备工具')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--config', default='config_end2end_test.json', help='配置文件路径')
    parser.add_argument('--force-clean', action='store_true', help='强制清理测试结果目录')
    parser.add_argument('--dry-run', action='store_true', help='仅检查，不执行操作')
    parser.add_argument('--report-only', action='store_true', help='仅生成报告')

    args = parser.parse_args()

    preparer = EnhancedEnvironmentPreparer(args.base_dir)

    if args.report_only:
        report = preparer.generate_preparation_report()
        print(report)
        return 0

    if args.dry_run:
        print("=== 环境准备预览模式 ===")
        print("注意: 预览模式下不会执行实际的清理操作")
        # 在预览模式下，只进行检查，不执行清理
        preparer._check_directory_structure()
        preparer._check_permissions()
        preparer._check_expected_documents()
        preparer._check_document_integrity()
        preparer._validate_configuration(args.config)
        print("\n预览完成")
        return 0

    # 执行完整的环境准备
    result = preparer.prepare_environment(args.config, args.force_clean)

    # 保存报告
    preparer.save_preparation_report()

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())