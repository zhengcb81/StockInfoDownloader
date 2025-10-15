#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能测试环境清理工具
根据测试说明.md的要求，智能清理测试环境，保留必要的文件
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SmartTestEnvironmentCleaner:
    """智能测试环境清理器"""

    def __init__(self, config_file: str = "config_end2end_test.json"):
        self.config_file = config_file
        self.config = self._load_config()

        # 目录路径
        self.test_results_dir = Path("end2end_test/test_results")
        self.expected_results_dir = Path("end2end_test/expected_results")

        # 清理规则
        self.cleanup_rules = {
            "keep_files_with_delete_later_false": True,  # 保留delete_later=false的文件
            "remove_empty_directories": True,              # 删除空目录
            "keep_config_directories": True,               # 保留配置目录结构
            "dry_run": False                               # 实际执行清理
        }

        logger.info("智能测试环境清理器初始化完成")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {"test_cases": []}

    def prepare_test_environment(self, force_clean: bool = False) -> Dict[str, Any]:
        """准备测试环境"""
        logger.info("开始智能准备测试环境...")

        preparation_result = {
            "start_time": datetime.now().isoformat(),
            "success": False,
            "operations": [],
            "errors": [],
            "files_kept": [],
            "files_removed": [],
            "directories_processed": []
        }

        try:
            # 1. 确保目录结构存在
            self._ensure_directory_structure(preparation_result)

            # 2. 智能清理测试结果目录
            self._smart_cleanup_test_results(preparation_result, force_clean)

            # 3. 验证预期文档
            self._verify_expected_documents(preparation_result)

            # 4. 检查配置文件
            self._validate_configuration(preparation_result)

            preparation_result["success"] = True
            preparation_result["end_time"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"环境准备失败: {e}")
            preparation_result["errors"].append(f"环境准备异常: {str(e)}")
            preparation_result["end_time"] = datetime.now().isoformat()

        # 生成报告
        self._generate_preparation_report(preparation_result)

        logger.info(f"测试环境准备完成 - 成功: {preparation_result['success']}")
        return preparation_result

    def _ensure_directory_structure(self, result: Dict[str, Any]):
        """确保目录结构存在"""
        logger.info("检查并创建目录结构...")

        directories = [
            self.test_results_dir,
            self.expected_results_dir
        ]

        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                result["operations"].append(f"创建目录: {directory}")
                logger.info(f"  创建目录: {directory}")
            else:
                result["operations"].append(f"目录已存在: {directory}")
                logger.info(f"  目录已存在: {directory}")

    def _smart_cleanup_test_results(self, result: Dict[str, Any], force_clean: bool):
        """智能清理测试结果目录"""
        logger.info("执行智能清理...")

        if not self.test_results_dir.exists():
            result["operations"].append("测试结果目录不存在，无需清理")
            return

        # 获取测试用例配置
        test_cases = self.config.get("test_cases", [])
        delete_later_false_files = set()

        # 找出需要保留的文件（delete_later=false）
        for case in test_cases:
            if not case.get("delete_later", True):
                for expected_doc in case.get("expected_documents", []):
                    delete_later_false_files.add(expected_doc)

        logger.info(f"  需要保留的文件: {len(delete_later_false_files)} 个")
        logger.info(f"  保留文件列表: {list(delete_later_false_files)}")

        # 遍历测试结果目录
        files_kept = []
        files_removed = []
        directories_processed = []

        for item in self.test_results_dir.iterdir():
            if item.is_file():
                should_keep = self._should_keep_file(item, delete_later_false_files, force_clean)
                if should_keep:
                    files_kept.append(str(item))
                    result["operations"].append(f"保留文件: {item.name}")
                else:
                    try:
                        item.unlink()
                        files_removed.append(str(item))
                        result["operations"].append(f"删除文件: {item.name}")
                    except Exception as e:
                        result["errors"].append(f"删除文件失败 {item.name}: {str(e)}")

            elif item.is_dir():
                # 清理目录内容
                if self._cleanup_directory_content(item, delete_later_false_files, force_clean, result):
                    # 如果目录为空，删除目录
                    if not any(item.iterdir()):
                        try:
                            item.rmdir()
                            result["operations"].append(f"删除空目录: {item.name}")
                        except Exception as e:
                            result["errors"].append(f"删除目录失败 {item.name}: {str(e)}")
                    else:
                        directories_processed.append(str(item))
                        result["operations"].append(f"保留目录: {item.name}")
                else:
                    directories_processed.append(str(item))
                    result["operations"].append(f"保留目录: {item.name}")

        result["files_kept"] = files_kept
        result["files_removed"] = files_removed
        result["directories_processed"] = directories_processed

        logger.info(f"  保留文件: {len(files_kept)} 个")
        logger.info(f"  删除文件: {len(files_removed)} 个")
        logger.info(f"  处理目录: {len(directories_processed)} 个")

    def _should_keep_file(self, file_path: Path, keep_files: set, force_clean: bool) -> bool:
        """判断是否应该保留文件"""
        if force_clean:
            return False

        file_name = file_path.name

        # 检查是否在保留列表中
        for keep_file in keep_files:
            if keep_file in file_name or file_name in keep_file:
                return True

        # 检查文件修改时间，避免删除最近的文件（5分钟内）
        if datetime.fromtimestamp(file_path.stat().st_mtime) > datetime.now() - timedelta(minutes=5):
            return True

        return False

    def _cleanup_directory_content(self, directory: Path, keep_files: set, force_clean: bool, result: Dict[str, Any]) -> bool:
        """清理目录内容"""
        directory_has_content = False

        for item in directory.iterdir():
            if item.is_file():
                should_keep = self._should_keep_file(item, keep_files, force_clean)
                if should_keep:
                    directory_has_content = True
                else:
                    try:
                        item.unlink()
                        result["operations"].append(f"删除目录文件: {directory.name}/{item.name}")
                    except Exception as e:
                        result["errors"].append(f"删除目录文件失败 {directory.name}/{item.name}: {str(e)}")
                        directory_has_content = True

            elif item.is_dir():
                # 递归清理子目录
                if self._cleanup_directory_content(item, keep_files, force_clean, result):
                    directory_has_content = True
                else:
                    # 子目录为空，尝试删除
                    try:
                        item.rmdir()
                        result["operations"].append(f"删除空子目录: {directory.name}/{item.name}")
                    except Exception as e:
                        result["errors"].append(f"删除子目录失败 {directory.name}/{item.name}: {str(e)}")
                        directory_has_content = True

        return directory_has_content

    def _verify_expected_documents(self, result: Dict[str, Any]):
        """验证预期文档"""
        logger.info("验证预期文档...")

        if not self.expected_results_dir.exists():
            result["operations"].append("预期结果目录不存在")
            return

        try:
            # 统计文档数量
            doc_count = len([f for f in self.expected_results_dir.iterdir() if f.is_file()])
            result["operations"].append(f"预期文档数量: {doc_count}")

            if doc_count >= 3:
                result["operations"].append("预期文档数量充足")
            else:
                result["operations"].append(f"预期文档数量较少: {doc_count} 个")

        except Exception as e:
            result["errors"].append(f"验证预期文档失败: {str(e)}")

    def _validate_configuration(self, result: Dict[str, Any]):
        """验证配置文件"""
        logger.info("验证配置文件...")

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            test_cases = config.get("test_cases", [])
            result["operations"].append(f"配置文件包含 {len(test_cases)} 个测试用例")

            # 检查关键配置项
            required_keys = ["save_dir", "test_cases"]
            missing_keys = [key for key in required_keys if key not in config]

            if missing_keys:
                result["errors"].append(f"配置文件缺少必需项: {', '.join(missing_keys)}")
            else:
                result["operations"].append("配置文件验证通过")

        except Exception as e:
            result["errors"].append(f"配置文件验证失败: {str(e)}")

    def _generate_preparation_report(self, result: Dict[str, Any]):
        """生成准备报告"""
        report = {
            "preparation_time": result["start_time"],
            "success": result["success"],
            "operations_count": len(result["operations"]),
            "errors_count": len(result["errors"]),
            "files_kept_count": len(result["files_kept"]),
            "files_removed_count": len(result["files_removed"]),
            "operations": result["operations"],
            "errors": result["errors"],
            "summary": {
                "status": "成功" if result["success"] else "失败",
                "message": "测试环境准备完成" if result["success"] else "测试环境准备失败"
            }
        }

        try:
            report_file = Path("end2end_test/smart_environment_preparation_report.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"环境准备报告已保存: {report_file}")

        except Exception as e:
            logger.error(f"保存准备报告失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("智能测试环境清理工具")
    print("=" * 60)

    # 初始化清理器
    cleaner = SmartTestEnvironmentCleaner()

    # 执行环境准备
    print("\n1. 准备测试环境...")
    result = cleaner.prepare_test_environment()

    # 显示结果
    print("\n2. 环境准备结果:")
    print(f"   状态: {'成功' if result['success'] else '失败'}")
    print(f"   执行操作: {result.get('operations_count', len(result.get('operations', [])))} 个")
    print(f"   错误数量: {result.get('errors_count', len(result.get('errors', [])))} 个")
    print(f"   保留文件: {result.get('files_kept_count', len(result.get('files_kept', [])))} 个")
    print(f"   删除文件: {result.get('files_removed_count', len(result.get('files_removed', [])))} 个")

    # 显示关键操作
    print("\n3. 关键操作:")
    for operation in result["operations"][:5]:  # 只显示前5个
        print(f"   - {operation}")

    if result["errors"]:
        print("\n4. 错误信息:")
        for error in result["errors"]:
            print(f"   - {error}")

    print("\n智能环境清理完成!")


if __name__ == "__main__":
    main()