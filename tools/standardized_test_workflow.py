#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
标准化测试工作流程
整合所有测试工具，提供完整的端到端测试流程
"""

import os
import sys
import json
import time
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager
from smart_directory_cleaner import SmartDirectoryCleaner
from data_validation_framework import DataValidationFramework


@dataclass
class WorkflowStep:
    """工作流程步骤"""
    name: str
    description: str
    required: bool = True
    timeout_seconds: int = 300


@dataclass
class WorkflowResult:
    """工作流程结果"""
    workflow_name: str
    total_steps: int
    completed_steps: int
    success: bool
    start_time: datetime
    end_time: datetime
    duration: float
    step_results: Dict[str, Any]
    errors: List[str]
    summary: Dict[str, Any]


class StandardizedTestWorkflow:
    """标准化测试工作流程"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化工作流程

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.workflow_log_dir = self.base_dir / "workflow_logs"
        self.workflow_log_dir.mkdir(parents=True, exist_ok=True)

        # 初始化工具
        self.document_manager = RealDocumentManager(base_dir)
        self.cleaner = SmartDirectoryCleaner(base_dir)
        self.validator = DataValidationFramework(base_dir)

        # 定义标准工作流程步骤
        self.standard_steps = [
            WorkflowStep(
                name="environment_check",
                description="检查测试环境",
                required=True,
                timeout_seconds=30
            ),
            WorkflowStep(
                name="document_scan",
                description="扫描预期文档",
                required=True,
                timeout_seconds=60
            ),
            WorkflowStep(
                name="configuration_validation",
                description="验证测试配置",
                required=True,
                timeout_seconds=30
            ),
            WorkflowStep(
                name="environment_preparation",
                description="准备测试环境",
                required=True,
                timeout_seconds=120
            ),
            WorkflowStep(
                name="test_execution",
                description="执行测试",
                required=True,
                timeout_seconds=1800
            ),
            WorkflowStep(
                name="data_validation",
                description="验证测试结果",
                required=True,
                timeout_seconds=300
            ),
            WorkflowStep(
                name="cleanup",
                description="清理环境",
                required=False,
                timeout_seconds=60
            ),
            WorkflowStep(
                name="report_generation",
                description="生成报告",
                required=True,
                timeout_seconds=60
            )
        ]

    def log_message(self, message: str, step: str = None):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if step:
            log_entry = f"[{timestamp}] [{step}] {message}"
        else:
            log_entry = f"[{timestamp}] {message}"

        print(log_entry)

        # 写入日志文件
        log_file = self.workflow_log_dir / f"workflow_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")

    def execute_step(self, step: WorkflowStep, config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        执行工作流程步骤

        Args:
            step: 工作流程步骤
            config: 配置信息

        Returns:
            (成功状态, 结果数据, 错误列表)
        """
        self.log_message(f"开始执行步骤: {step.description}", step.name)
        start_time = time.time()
        errors = []
        result_data = {}

        try:
            if step.name == "environment_check":
                # 检查测试环境
                result_data = self._check_environment()

            elif step.name == "document_scan":
                # 扫描预期文档
                result_data = self._scan_documents()

            elif step.name == "configuration_validation":
                # 验证测试配置
                success, config_data = self._validate_configuration(config)
                if not success:
                    errors.extend(config_data.get("errors", []))
                result_data = config_data

            elif step.name == "environment_preparation":
                # 准备测试环境
                result_data = self._prepare_environment(config)

            elif step.name == "test_execution":
                # 执行测试
                result_data = self._execute_tests(config)

            elif step.name == "data_validation":
                # 验证测试结果
                result_data = self._validate_data(config)

            elif step.name == "cleanup":
                # 清理环境
                result_data = self._cleanup_environment(config)

            elif step.name == "report_generation":
                # 生成报告
                result_data = self._generate_reports(config)

            else:
                errors.append(f"未知的工作流程步骤: {step.name}")

            duration = time.time() - start_time
            result_data["duration"] = duration
            result_data["success"] = len(errors) == 0

            self.log_message(f"步骤完成: {step.description} (耗时: {duration:.1f}s)", step.name)

            return len(errors) == 0, result_data, errors

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"步骤执行异常: {str(e)}"
            errors.append(error_msg)
            result_data = {"duration": duration, "success": False, "error": error_msg}

            self.log_message(f"步骤失败: {step.description} - {error_msg}", step.name)
            return False, result_data, errors

    def _check_environment(self) -> Dict[str, Any]:
        """检查测试环境"""
        env_status = {
            "base_dir_exists": self.base_dir.exists(),
            "test_results_dir_exists": (self.base_dir / "test_results").exists(),
            "expected_results_dir_exists": (self.base_dir / "expected_results").exists(),
            "tools_available": True
        }

        # 检查工具可用性
        try:
            self.document_manager.scan_existing_documents()
            self.cleaner.get_directory_status()
            self.validator.validation_rules
        except Exception as e:
            env_status["tools_available"] = False
            env_status["tools_error"] = str(e)

        # 创建必要目录
        if not env_status["test_results_dir_exists"]:
            (self.base_dir / "test_results").mkdir(parents=True, exist_ok=True)
            env_status["test_results_dir_exists"] = True
            self.log_message("创建测试结果目录")

        return env_status

    def _scan_documents(self) -> Dict[str, Any]:
        """扫描预期文档"""
        docs = self.document_manager.scan_existing_documents()

        return {
            "total_documents": len(docs),
            "documents": [
                {
                    "doc_id": self.document_manager.generate_doc_id(doc),
                    "stock_code": doc.stock_code,
                    "stock_name": doc.stock_name,
                    "document_type": doc.document_type,
                    "document_name": doc.document_name,
                    "file_size": doc.file_size
                }
                for doc in docs
            ]
        }

    def _validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """验证测试配置"""
        try:
            config_file = config.get("config_file", "config_end2end_test_extended.json")
            if not os.path.exists(config_file):
                return False, {"errors": [f"配置文件不存在: {config_file}"]}

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            test_cases = config_data.get("test_cases", [])

            # 使用文档管理器验证配置
            valid, issues = self.document_manager.validate_test_configuration(config_file)

            return valid, {
                "config_file": config_file,
                "total_test_cases": len(test_cases),
                "validation_passed": valid,
                "issues": issues
            }

        except Exception as e:
            return False, {"errors": [f"配置验证异常: {str(e)}"]}

    def _prepare_environment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """准备测试环境"""
        config_file = config.get("config_file", "config_end2end_test_extended.json")

        # 使用智能清理工具准备环境
        result = self.cleaner.smart_cleanup(config_file, dry_run=False)

        # 恢复预期文档
        restored_files, restore_errors = self.cleaner.restore_expected_documents(dry_run=False)

        return {
            "cleanup_result": {
                "cleaned_files": result.cleaned_files,
                "cleaned_dirs": result.cleaned_dirs,
                "preserved_files": result.preserved_files,
                "preserved_dirs": result.preserved_dirs
            },
            "restore_result": {
                "restored_files": restored_files,
                "restore_errors": restore_errors
            }
        }

    def _execute_tests(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行测试"""
        config_file = config.get("config_file", "config_end2end_test_extended.json")

        # 检查是否有测试脚本
        test_script = config.get("test_script", "e2e_test_extended.py")

        if not os.path.exists(test_script):
            return {
                "execution_skipped": True,
                "reason": f"测试脚本不存在: {test_script}"
            }

        self.log_message(f"执行测试脚本: {test_script}")

        # 执行测试脚本
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, test_script, "--config", config_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=config.get("test_timeout", 3600)
            )

            return {
                "execution_completed": True,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "execution_completed": False,
                "timeout": True,
                "reason": "测试执行超时"
            }
        except Exception as e:
            return {
                "execution_completed": False,
                "error": str(e)
            }

    def _validate_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证测试结果"""
        config_file = config.get("config_file", "config_end2end_test_extended.json")

        # 使用数据验证框架
        summary, all_results = self.validator.validate_all_test_cases(config_file)

        return {
            "validation_summary": {
                "total_files": summary.total_files,
                "valid_files": summary.valid_files,
                "invalid_files": summary.invalid_files,
                "missing_files": summary.missing_files,
                "validation_rate": summary.validation_rate,
                "total_size": summary.total_size,
                "validation_time": summary.validation_time
            },
            "detailed_results": {
                case_key: {
                    "summary": {
                        "total_files": case_data["summary"].total_files,
                        "valid_files": case_data["summary"].valid_files,
                        "invalid_files": case_data["summary"].invalid_files,
                        "missing_files": case_data["summary"].missing_files,
                        "validation_rate": case_data["summary"].validation_rate
                    }
                }
                for case_key, case_data in all_results.items()
            }
        }

    def _cleanup_environment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """清理环境"""
        config_file = config.get("config_file", "config_end2end_test_extended.json")

        # 执行清理
        result = self.cleaner.smart_cleanup(config_file, dry_run=False)

        return {
            "cleanup_completed": True,
            "cleaned_files": result.cleaned_files,
            "cleaned_dirs": result.cleaned_dirs,
            "preserved_files": result.preserved_files,
            "preserved_dirs": result.preserved_dirs,
            "errors": result.errors
        }

    def _generate_reports(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        reports = {}

        # 生成工作流程报告
        workflow_report_file = self.workflow_log_dir / f"workflow_report_{timestamp}.json"
        reports["workflow_report"] = str(workflow_report_file)

        # 生成验证报告
        validation_report_file = self.workflow_log_dir / f"validation_report_{timestamp}.md"
        reports["validation_report"] = str(validation_report_file)

        # 运行数据验证并生成报告
        try:
            config_file = config.get("config_file", "config_end2end_test_extended.json")
            summary, all_results = self.validator.validate_all_test_cases(config_file)
            self.validator.generate_validation_report(summary, all_results, str(validation_report_file))
        except Exception as e:
            self.log_message(f"生成验证报告失败: {e}")

        return {
            "reports_generated": True,
            "report_files": reports,
            "timestamp": timestamp
        }

    def run_workflow(self, config: Dict[str, Any]) -> WorkflowResult:
        """
        运行完整的工作流程

        Args:
            config: 配置信息

        Returns:
            工作流程结果
        """
        workflow_name = config.get("workflow_name", "standard_test_workflow")
        self.log_message(f"开始执行工作流程: {workflow_name}")

        start_time = datetime.now()
        step_results = {}
        errors = []
        completed_steps = 0
        total_steps = len(self.standard_steps)

        for step in self.standard_steps:
            try:
                success, result_data, step_errors = self.execute_step(step, config)

                step_results[step.name] = {
                    "success": success,
                    "data": result_data,
                    "errors": step_errors,
                    "duration": result_data.get("duration", 0)
                }

                if success:
                    completed_steps += 1
                else:
                    errors.extend(step_errors)

                    # 如果是必需步骤失败，停止工作流程
                    if step.required:
                        self.log_message(f"必需步骤失败，停止工作流程: {step.description}")
                        break

            except Exception as e:
                error_msg = f"步骤执行异常: {str(e)}"
                errors.append(error_msg)
                step_results[step.name] = {
                    "success": False,
                    "data": {},
                    "errors": [error_msg],
                    "duration": 0
                }

                if step.required:
                    self.log_message(f"必需步骤异常，停止工作流程: {step.description}")
                    break

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 计算总体成功状态
        success = completed_steps > 0 and len(errors) == 0

        # 生成工作流程汇总
        summary = {
            "workflow_name": workflow_name,
            "success_rate": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "total_duration": duration,
            "steps_completed": completed_steps,
            "steps_failed": total_steps - completed_steps
        }

        result = WorkflowResult(
            workflow_name=workflow_name,
            total_steps=total_steps,
            completed_steps=completed_steps,
            success=success,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            step_results=step_results,
            errors=errors,
            summary=summary
        )

        # 保存工作流程结果
        self._save_workflow_result(result)

        self.log_message(f"工作流程完成: {workflow_name} (成功: {success}, 耗时: {duration:.1f}s)")

        return result

    def _save_workflow_result(self, result: WorkflowResult):
        """保存工作流程结果"""
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        result_file = self.workflow_log_dir / f"workflow_result_{timestamp}.json"

        # 转换为可序列化的格式
        result_data = {
            "workflow_name": result.workflow_name,
            "total_steps": result.total_steps,
            "completed_steps": result.completed_steps,
            "success": result.success,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "duration": result.duration,
            "step_results": result.step_results,
            "errors": result.errors,
            "summary": result.summary
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        self.log_message(f"工作流程结果已保存: {result_file}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='标准化测试工作流程')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--config', default='config_end2end_test_extended.json', help='测试配置文件')
    parser.add_argument('--test-script', default='e2e_test_extended.py', help='测试脚本文件')
    parser.add_argument('--workflow-name', default='standard_test_workflow', help='工作流程名称')
    parser.add_argument('--skip-test', action='store_true', help='跳过测试执行')
    parser.add_argument('--cleanup-only', action='store_true', help='只执行清理')
    parser.add_argument('--validate-only', action='store_true', help='只执行验证')

    args = parser.parse_args()

    # 创建工作流程配置
    config = {
        "config_file": args.config,
        "test_script": args.test_script,
        "workflow_name": args.workflow_name,
        "base_dir": args.base_dir
    }

    # 根据参数调整工作流程
    if args.cleanup_only:
        # 只执行清理
        cleaner = SmartDirectoryCleaner(args.base_dir)
        result = cleaner.smart_cleanup(args.config, dry_run=False)
        print(f"清理完成: 删除 {result.cleaned_files} 个文件, {result.cleaned_dirs} 个目录")
        return 0

    elif args.validate_only:
        # 只执行验证
        validator = DataValidationFramework(args.base_dir)
        summary, all_results = validator.validate_all_test_cases(args.config)

        print(f"验证结果:")
        print(f"  总文件数: {summary.total_files}")
        print(f"  有效文件: {summary.valid_files}")
        print(f"  无效文件: {summary.invalid_files}")
        print(f"  缺失文件: {summary.missing_files}")
        print(f"  验证率: {summary.validation_rate:.1f}%")

        return 0 if summary.validation_rate >= 50.0 else 1

    else:
        # 执行完整工作流程
        workflow = StandardizedTestWorkflow(args.base_dir)
        result = workflow.run_workflow(config)

        # 输出结果摘要
        print(f"\n{'='*80}")
        print(f"工作流程结果摘要")
        print(f"{'='*80}")
        print(f"工作流程名称: {result.workflow_name}")
        print(f"总步骤数: {result.total_steps}")
        print(f"完成步骤数: {result.completed_steps}")
        print(f"成功率: {result.summary['success_rate']:.1f}%")
        print(f"总耗时: {result.duration:.1f}s")
        print(f"执行状态: {'成功' if result.success else '失败'}")

        if result.errors:
            print(f"\n错误信息:")
            for error in result.errors:
                print(f"  - {error}")

        print(f"\n步骤详情:")
        for step_name, step_result in result.step_results.items():
            status = "✓" if step_result["success"] else "✗"
            duration = step_result.get("duration", 0)
            print(f"  {status} {step_name}: {duration:.1f}s")

        return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())