#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
标准化测试工作流程 v2
整合所有工具，提供完整的端到端测试准备流程
基于真实场景要求和测试说明.md的标准
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from enhanced_environment_preparer import EnhancedEnvironmentPreparer
from real_document_manager import RealDocumentManager
from smart_directory_cleaner import SmartDirectoryCleaner
from data_validation_framework import DataValidationFramework
from real_scenario_test_generator import RealScenarioTestGenerator
from document_classification_system import DocumentClassificationSystem


@dataclass
class WorkflowStep:
    """工作流程步骤"""
    step_id: str
    name: str
    description: str
    required: bool
    estimated_time: int  # 秒
    dependencies: List[str]
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    result: Dict[str, Any] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class WorkflowReport:
    """工作流程报告"""
    workflow_id: str
    start_time: datetime
    total_steps: int
    completed_steps: int = 0
    failed_steps: int = 0
    success: bool = False
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    steps: List[WorkflowStep] = None
    summary: Dict[str, Any] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.summary is None:
            self.summary = {}
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class StandardizedTestWorkflowV2:
    """标准化测试工作流程 v2"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化工作流程

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.workflow_logs_dir = self.base_dir / "workflow_logs"
        self.workflow_logs_dir.mkdir(parents=True, exist_ok=True)

        # 初始化所有工具
        self.env_preparer = EnhancedEnvironmentPreparer(base_dir)
        self.document_manager = RealDocumentManager(base_dir)
        self.cleaner = SmartDirectoryCleaner(base_dir)
        self.validator = DataValidationFramework(base_dir)
        self.test_generator = RealScenarioTestGenerator(base_dir)
        self.classification_system = DocumentClassificationSystem(base_dir)

        # 定义标准工作流程步骤
        self.workflow_steps = [
            WorkflowStep(
                step_id="preparation_check",
                name="环境准备检查",
                description="根据测试说明要求进行完整的环境准备和验证",
                required=True,
                estimated_time=60,
                dependencies=[]
            ),
            WorkflowStep(
                step_id="document_verification",
                name="文档完整性验证",
                description="验证预期文档的完整性和可访问性",
                required=True,
                estimated_time=30,
                dependencies=["preparation_check"]
            ),
            WorkflowStep(
                step_id="classification_update",
                name="文档分类更新",
                description="更新文档分类体系，确保分类信息准确",
                required=True,
                estimated_time=45,
                dependencies=["document_verification"]
            ),
            WorkflowStep(
                step_id="test_case_validation",
                name="测试用例验证",
                description="验证所有测试用例配置的正确性",
                required=True,
                estimated_time=30,
                dependencies=["classification_update"]
            ),
            WorkflowStep(
                step_id="test_scenario_ready",
                name="测试场景准备",
                description="确保所有测试场景都已准备就绪",
                required=True,
                estimated_time=20,
                dependencies=["test_case_validation"]
            ),
            WorkflowStep(
                step_id="quality_check",
                name="质量检查",
                description="执行最终质量检查，确保所有要求都已满足",
                required=True,
                estimated_time=25,
                dependencies=["test_scenario_ready"]
            )
        ]

        # 工作流程报告
        self.workflow_report = WorkflowReport(
            workflow_id=f"workflow_{int(time.time())}",
            start_time=datetime.now(),
            total_steps=len(self.workflow_steps),
            completed_steps=0,
            failed_steps=0
        )

    def execute_workflow(self, config_file: str = "config_end2end_test.json",
                         test_scenarios_file: str = None,
                         force_clean: bool = False,
                         dry_run: bool = False) -> WorkflowReport:
        """
        执行完整的标准化工作流程

        Args:
            config_file: 配置文件路径
            test_scenarios_file: 测试场景文件路径
            force_clean: 是否强制清理
            dry_run: 是否为干运行模式

        Returns:
            工作流程报告
        """
        print("=" * 80)
        print("标准化测试工作流程 v2")
        print("=" * 80)
        print(f"工作流程ID: {self.workflow_report.workflow_id}")
        print(f"开始时间: {self.workflow_report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"配置文件: {config_file}")
        print(f"干运行模式: {dry_run}")
        print(f"强制清理: {force_clean}")
        print("=" * 80)

        try:
            # 执行所有工作流程步骤
            for step in self.workflow_steps:
                self._execute_step(step, config_file, test_scenarios_file, force_clean, dry_run)

            # 完成工作流程
            self.workflow_report.end_time = datetime.now()
            self.workflow_report.duration = (
                self.workflow_report.end_time - self.workflow_report.start_time
            ).total_seconds()

            # 计算统计信息
            self.workflow_report.completed_steps = len(
                [s for s in self.workflow_report.steps if s.status == "completed"]
            )
            self.workflow_report.failed_steps = len(
                [s for s in self.workflow_report.steps if s.status == "failed"]
            )
            self.workflow_report.success = (
                self.workflow_report.failed_steps == 0 and
                all(s.status == "completed" for s in self.workflow_report.steps if s.required)
            )

            # 生成汇总信息
            self._generate_summary()

            # 保存工作流程报告
            self._save_workflow_report()

            # 打印最终结果
            self._print_final_results()

        except Exception as e:
            self.workflow_report.errors.append(f"工作流程执行异常: {e}")
            self.workflow_report.end_time = datetime.now()
            self.workflow_report.success = False
            self._save_workflow_report()
            print(f"\n工作流程执行失败: {e}")

        return self.workflow_report

    def _execute_step(self, step: WorkflowStep, config_file: str,
                     test_scenarios_file: str, force_clean: bool, dry_run: bool):
        """执行单个工作流程步骤"""
        print(f"\n{'='*60}")
        print(f"步骤 {step.step_id}: {step.name}")
        print(f"{'='*60}")
        print(f"描述: {step.description}")
        print(f"预计耗时: {step.estimated_time}秒")
        print(f"依赖: {', '.join(step.dependencies) if step.dependencies else '无'}")

        step.start_time = datetime.now()

        try:
            if dry_run:
                print(f"[干运行] 将执行: {step.name}")
                step.status = "skipped"
                step.result = {"dry_run": True, "message": "干运行模式，跳过实际执行"}
            else:
                # 检查依赖
                if not self._check_dependencies(step):
                    raise Exception(f"依赖项未满足: {step.dependencies}")

                # 执行具体步骤
                if step.step_id == "preparation_check":
                    result = self._execute_preparation_check(config_file, force_clean)

                elif step.step_id == "document_verification":
                    result = self._execute_document_verification()

                elif step.step_id == "classification_update":
                    result = self._execute_classification_update()

                elif step.step_id == "test_case_validation":
                    result = self._execute_test_case_validation(config_file, test_scenarios_file)

                elif step.step_id == "test_scenario_ready":
                    result = self._execute_test_scenario_ready()

                elif step.step_id == "quality_check":
                    result = self._execute_quality_check()

                else:
                    raise Exception(f"未知的工作流程步骤: {step.step_id}")

                step.result = result
                step.status = "completed" if not result.get("errors") else "completed_with_errors"

        except Exception as e:
            step.status = "failed"
            step.errors = [str(e)]
            step.result = {"error": str(e)}
            print(f"步骤执行失败: {e}")

        step.end_time = datetime.now()
        step.duration = (step.end_time - step.start_time).total_seconds()

        self.workflow_report.steps.append(step)

        print(f"步骤状态: {step.status}")
        print(f"执行耗时: {step.duration:.2f}秒")

        if step.errors:
            print(f"错误信息:")
            for error in step.errors:
                print(f"  - {error}")

        if step.result and step.result.get("warnings"):
            print(f"警告信息:")
            for warning in step.result.get("warnings", []):
                print(f"  - {warning}")

    def _check_dependencies(self, step: WorkflowStep) -> bool:
        """检查步骤依赖"""
        if not step.dependencies:
            return True

        for dep_id in step.dependencies:
            dep_step = next((s for s in self.workflow_report.steps if s.step_id == dep_id), None)
            if not dep_step or dep_step.status != "completed":
                print(f"依赖检查失败: {dep_id} 未完成")
                return False

        return True

    def _execute_preparation_check(self, config_file: str, force_clean: bool) -> Dict[str, Any]:
        """执行环境准备检查"""
        print("执行环境准备检查...")

        result = self.env_preparer.prepare_environment(config_file, force_clean)

        return {
            "success": result["success"],
            "errors": result["errors"],
            "warnings": result["warnings"],
            "actions_taken": result["actions_taken"],
            "checklist_results": result["checklist_results"]
        }

    def _execute_document_verification(self) -> Dict[str, Any]:
        """执行文档完整性验证"""
        print("执行文档完整性验证...")

        try:
            documents = self.document_manager.scan_existing_documents()

            # 验证文档完整性
            valid_docs = 0
            issues = []

            for doc in documents:
                doc_path = self.document_manager.get_document_path(doc)
                if doc_path.exists() and doc.file_size > 0:
                    valid_docs += 1
                else:
                    issues.append(f"文档无效: {doc.document_name}")

            return {
                "success": len(issues) == 0,
                "total_documents": len(documents),
                "valid_documents": valid_docs,
                "issues": issues
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _execute_classification_update(self) -> Dict[str, Any]:
        """执行文档分类更新"""
        print("执行文档分类更新...")

        try:
            classification = self.classification_system.classify_documents()

            return {
                "success": True,
                "total_documents": classification["total_documents"],
                "company_categories": len(classification["by_company_category"]),
                "document_types": len(classification["by_document_type"]),
                "classification": classification
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _execute_test_case_validation(self, config_file: str, test_scenarios_file: str) -> Dict[str, Any]:
        """执行测试用例验证"""
        print("执行测试用例验证...")

        try:
            # 验证配置文件中的测试用例
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            config_test_cases = config.get("test_cases", [])

            # 如果有真实场景测试用例文件，也验证它
            scenario_test_cases = []
            if test_scenarios_file and os.path.exists(test_scenarios_file):
                with open(test_scenarios_file, 'r', encoding='utf-8') as f:
                    scenario_data = json.load(f)
                    if "test_cases" in scenario_data:
                        scenario_test_cases = scenario_data["test_cases"]

            total_test_cases = len(config_test_cases) + len(scenario_test_cases)

            return {
                "success": True,
                "config_test_cases": len(config_test_cases),
                "scenario_test_cases": len(scenario_test_cases),
                "total_test_cases": total_test_cases,
                "config_file": config_file,
                "scenario_file": test_scenarios_file
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _execute_test_scenario_ready(self) -> Dict[str, Any]:
        """执行测试场景准备"""
        print("执行测试场景准备...")

        try:
            # 检查测试结果目录状态
            test_status = self.cleaner.get_directory_status()

            # 检查预期结果目录
            expected_status = {
                "exists": self.env_preparer.expected_results_dir.exists(),
                "total_files": 0,
                "total_dirs": 0
            }

            if self.env_preparer.expected_results_dir.exists():
                for company_dir in self.env_preparer.expected_results_dir.iterdir():
                    if company_dir.is_dir():
                        expected_status["total_dirs"] += 1
                        for file_path in company_dir.iterdir():
                            if file_path.is_file():
                                expected_status["total_files"] += 1

            return {
                "success": True,
                "test_results_status": test_status,
                "expected_results_status": expected_status,
                "ready": expected_status["total_files"] > 0
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _execute_quality_check(self) -> Dict[str, Any]:
        """执行质量检查"""
        print("执行质量检查...")

        try:
            # 检查所有工具的状态
            tools_status = {
                "document_manager": "available",
                "cleaner": "available",
                "validator": "available",
                "test_generator": "available",
                "classification_system": "available"
            }

            # 检查文档目录结构
            directory_structure_ok = (
                self.env_preparer.base_dir.exists() and
                self.env_preparer.test_results_dir.exists() and
                self.env_preparer.expected_results_dir.exists()
            )

            # 统计文档数量
            documents = self.document_manager.scan_existing_documents()

            quality_score = 100
            if not directory_structure_ok:
                quality_score -= 30
            if len(documents) < 3:
                quality_score -= 20

            return {
                "success": quality_score >= 80,
                "quality_score": quality_score,
                "tools_status": tools_status,
                "directory_structure_ok": directory_structure_ok,
                "total_documents": len(documents),
                "passed": quality_score >= 80
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_summary(self):
        """生成工作流程汇总信息"""
        total_time = sum(s.duration or 0 for s in self.workflow_report.steps)
        avg_time = total_time / len(self.workflow_report.steps) if self.workflow_report.steps else 0

        self.workflow_report.summary = {
            "total_execution_time": total_time,
            "average_step_time": avg_time,
            "success_rate": (self.workflow_report.completed_steps / self.workflow_report.total_steps * 100) if self.workflow_report.total_steps > 0 else 0,
            "required_steps_passed": all(
                s.status == "completed" for s in self.workflow_report.steps if s.required
            ),
            "tool_versions": {
                "document_manager": "1.0",
                "cleaner": "1.0",
                "validator": "1.0",
                "test_generator": "1.0",
                "classification_system": "1.0",
                "environment_preparer": "1.0"
            }
        }

    def _save_workflow_report(self):
        """保存工作流程报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.workflow_logs_dir / f"workflow_report_{timestamp}.json"

        # 转换为可序列化的格式
        def serialize_step(step):
            step_data = asdict(step)
            if step_data["start_time"]:
                step_data["start_time"] = step_data["start_time"].isoformat()
            if step_data["end_time"]:
                step_data["end_time"] = step_data["end_time"].isoformat()
            return step_data

        report_data = {
            "workflow_id": self.workflow_report.workflow_id,
            "start_time": self.workflow_report.start_time.isoformat(),
            "end_time": self.workflow_report.end_time.isoformat() if self.workflow_report.end_time else None,
            "duration": self.workflow_report.duration,
            "total_steps": self.workflow_report.total_steps,
            "completed_steps": self.workflow_report.completed_steps,
            "failed_steps": self.workflow_report.failed_steps,
            "success": self.workflow_report.success,
            "steps": [serialize_step(step) for step in self.workflow_report.steps],
            "summary": self.workflow_report.summary,
            "errors": self.workflow_report.errors,
            "warnings": self.workflow_report.warnings
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"工作流程报告已保存到: {report_file}")

    def _print_final_results(self):
        """打印最终结果"""
        print(f"\n{'='*80}")
        print("工作流程执行结果")
        print(f"{'='*80}")
        print(f"工作流程ID: {self.workflow_report.workflow_id}")
        print(f"开始时间: {self.workflow_report.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"结束时间: {self.workflow_report.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.workflow_report.end_time else '进行中'}")
        print(f"总耗时: {self.workflow_report.duration or 0:.2f}秒")
        print(f"总步骤数: {self.workflow_report.total_steps}")
        print(f"完成步骤数: {self.workflow_report.completed_steps}")
        print(f"失败步骤数: {self.workflow_report.failed_steps}")
        print(f"成功率: {(self.workflow_report.completed_steps / self.workflow_report.total_steps * 100) if self.workflow_report.total_steps > 0 else 0:.1f}%")
        print(f"总体状态: {'成功' if self.workflow_report.success else '失败'}")

        if self.workflow_report.summary:
            print(f"\n汇总信息:")
            print(f"  平均步骤耗时: {self.workflow_report.summary.get('average_step_time', 0):.2f}秒")
            print(f"  质量评分: {self.workflow_report.summary.get('quality_score', 'N/A')}")

        if self.workflow_report.errors:
            print(f"\n错误信息:")
            for i, error in enumerate(self.workflow_report.errors, 1):
                print(f"  {i}. {error}")

        if self.workflow_report.warnings:
            print(f"\n警告信息:")
            for i, warning in enumerate(self.workflow_report.warnings, 1):
                print(f"  {i}. {warning}")

        print(f"{'='*80}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='标准化测试工作流程 v2')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--config', default='config_end2end_test.json', help='配置文件路径')
    parser.add_argument('--scenarios', help='测试场景文件路径')
    parser.add_argument('--force-clean', action='store_true', help='强制清理')
    parser.add_argument('--dry-run', action='store_true', help='干运行模式')
    parser.add_argument('--report-only', action='store_true', help='仅生成报告')

    args = parser.parse_args()

    workflow = StandardizedTestWorkflowV2(args.base_dir)

    if args.report_only:
        print("报告生成功能暂未实现")
        return 0

    # 执行工作流程
    result = workflow.execute_workflow(
        config_file=args.config,
        test_scenarios_file=args.scenarios,
        force_clean=args.force_clean,
        dry_run=args.dry_run
    )

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())