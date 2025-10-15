#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试编排器
整合环境准备、一致性保证、测试执行等所有组件
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入各个工具组件
try:
    from tools.enhanced_environment_preparer import EnhancedEnvironmentPreparer
    from tools.environment_consistency_manager import EnvironmentConsistencyManager
    from tools.document_classification_system import DocumentClassificationSystem
    from tools.real_scenario_test_generator import RealScenarioTestGenerator
    from tools.standardized_test_workflow_v2 import StandardizedTestWorkflowV2

    # 创建正确的工具实例
    def create_workflow_instance(config_file):
        return StandardizedTestWorkflowV2()  # 使用默认基础目录

except ImportError as e:
    logger.warning(f"导入工具模块失败: {e}")
    # 创建基本的工具类接口
    class MockTool:
        def __init__(self, config_file=None):
            self.config_file = config_file
        def run(self):
            return {"success": False, "error": str(e)}

    EnhancedEnvironmentPreparer = MockTool
    EnvironmentConsistencyManager = MockTool
    DocumentClassificationSystem = MockTool
    RealScenarioTestGenerator = MockTool

    def create_workflow_instance(config_file):
        return MockTool(config_file)


class IntegratedTestOrchestrator:
    """集成测试编排器"""

    def __init__(self, config_file: str = "config_end2end_test.json"):
        self.config_file = config_file
        self.config = self._load_config()

        # 初始化各个组件
        self.env_preparer = EnhancedEnvironmentPreparer()  # 使用默认基础目录
        self.consistency_manager = EnvironmentConsistencyManager()
        self.classification_system = DocumentClassificationSystem()
        self.test_generator = RealScenarioTestGenerator()
        self.workflow_manager = create_workflow_instance(config_file)

        # 测试状态
        self.test_session_id = f"SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_snapshot_id: Optional[str] = None
        self.test_results: List[Dict[str, Any]] = []

        logger.info(f"集成测试编排器初始化完成 - 会话ID: {self.test_session_id}")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def execute_full_test_workflow(self) -> Dict[str, Any]:
        """执行完整的测试工作流"""
        logger.info("=" * 60)
        logger.info("开始执行集成测试工作流")
        logger.info(f"会话ID: {self.test_session_id}")
        logger.info("=" * 60)

        workflow_report = {
            "session_id": self.test_session_id,
            "start_time": datetime.now().isoformat(),
            "stages": [],
            "overall_success": False,
            "errors": [],
            "recommendations": []
        }

        try:
            # 阶段1: 环境一致性保证
            stage1_result = self._execute_environment_consistency_stage()
            workflow_report["stages"].append(stage1_result)

            if not stage1_result["success"]:
                workflow_report["overall_success"] = False
                workflow_report["errors"].extend(stage1_result.get("errors", []))
                return self._finalize_workflow_report(workflow_report)

            # 阶段2: 增强环境准备
            stage2_result = self._execute_environment_preparation_stage()
            workflow_report["stages"].append(stage2_result)

            if not stage2_result["success"]:
                workflow_report["overall_success"] = False
                workflow_report["errors"].extend(stage2_result.get("errors", []))
                return self._finalize_workflow_report(workflow_report)

            # 阶段3: 文档分类更新
            stage3_result = self._execute_document_classification_stage()
            workflow_report["stages"].append(stage3_result)

            # 阶段4: 测试用例验证
            stage4_result = self._execute_test_case_validation_stage()
            workflow_report["stages"].append(stage4_result)

            # 阶段5: 真实场景测试执行
            stage5_result = self._execute_real_scenario_testing_stage()
            workflow_report["stages"].append(stage5_result)

            # 阶段6: 环境一致性验证
            stage6_result = self._execute_post_test_consistency_check()
            workflow_report["stages"].append(stage6_result)

            # 计算整体成功状态
            workflow_report["overall_success"] = all(
                stage.get("success", False) for stage in workflow_report["stages"]
            )

            # 生成建议
            self._generate_workflow_recommendations(workflow_report)

        except Exception as e:
            logger.error(f"工作流执行异常: {e}")
            workflow_report["overall_success"] = False
            workflow_report["errors"].append(f"工作流执行异常: {str(e)}")

        return self._finalize_workflow_report(workflow_report)

    def _execute_environment_consistency_stage(self) -> Dict[str, Any]:
        """阶段1: 环境一致性保证"""
        logger.info("\n" + "="*40)
        logger.info("阶段1: 环境一致性保证")
        logger.info("="*40)

        stage_result = {
            "stage_name": "环境一致性保证",
            "stage_id": "consistency_check",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {},
            "errors": []
        }

        try:
            # 创建环境快照
            logger.info("创建测试前环境快照...")
            snapshot = self.consistency_manager.create_snapshot(
                f"测试会话 {self.test_session_id} - 测试前快照"
            )
            self.current_snapshot_id = snapshot.snapshot_id
            stage_result["details"]["snapshot_id"] = snapshot.snapshot_id

            # 执行环境监控
            logger.info("执行环境状态监控...")
            monitoring_results = self.consistency_manager.monitor_environment()
            stage_result["details"]["monitoring_results"] = monitoring_results

            # 检查是否有严重的环境问题
            if monitoring_results["failed_checks"] > 0:
                logger.warning(f"发现 {monitoring_results['failed_checks']} 个环境检查失败")
                stage_result["errors"].append(
                    f"环境检查失败: {monitoring_results['failed_checks']} 项检查未通过"
                )

                # 对于严重问题，尝试恢复
                if self.current_snapshot_id:
                    logger.info("尝试恢复到最后一个良好状态...")
                    if self.consistency_manager.restore_environment(self.current_snapshot_id):
                        stage_result["details"]["recovery_attempted"] = True
                        stage_result["details"]["recovery_success"] = True
                    else:
                        stage_result["details"]["recovery_success"] = False
                        stage_result["errors"].append("环境恢复失败")

            stage_result["success"] = True
            logger.info("环境一致性保证阶段完成")

        except Exception as e:
            logger.error(f"环境一致性保证阶段失败: {e}")
            stage_result["errors"].append(f"阶段执行异常: {str(e)}")

        stage_result["end_time"] = datetime.now().isoformat()
        return stage_result

    def _execute_environment_preparation_stage(self) -> Dict[str, Any]:
        """阶段2: 增强环境准备"""
        logger.info("\n" + "="*40)
        logger.info("阶段2: 增强环境准备")
        logger.info("="*40)

        stage_result = {
            "stage_name": "增强环境准备",
            "stage_id": "environment_preparation",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {},
            "errors": []
        }

        try:
            # 执行增强环境准备
            preparation_result = self.env_preparer.prepare_environment(self.config_file)
            stage_result["details"]["preparation_result"] = preparation_result

            if preparation_result.get("success", False):
                stage_result["success"] = True
                logger.info("环境准备阶段完成")
            else:
                stage_result["errors"].append(
                    preparation_result.get("error", "环境准备失败")
                )
                logger.error("环境准备阶段失败")

        except Exception as e:
            logger.error(f"环境准备阶段异常: {e}")
            stage_result["errors"].append(f"阶段执行异常: {str(e)}")

        stage_result["end_time"] = datetime.now().isoformat()
        return stage_result

    def _execute_document_classification_stage(self) -> Dict[str, Any]:
        """阶段3: 文档分类更新"""
        logger.info("\n" + "="*40)
        logger.info("阶段3: 文档分类更新")
        logger.info("="*40)

        stage_result = {
            "stage_name": "文档分类更新",
            "stage_id": "document_classification",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {},
            "errors": []
        }

        try:
            # 更新文档分类
            classification_result = self.classification_system.classify_documents()
            stage_result["details"]["classification_result"] = classification_result

            # 生成统计报告
            statistics = self.classification_system.generate_statistics()
            stage_result["details"]["statistics"] = statistics

            stage_result["success"] = True
            logger.info("文档分类更新阶段完成")

        except Exception as e:
            logger.error(f"文档分类更新阶段异常: {e}")
            stage_result["errors"].append(f"阶段执行异常: {str(e)}")

        stage_result["end_time"] = datetime.now().isoformat()
        return stage_result

    def _execute_test_case_validation_stage(self) -> Dict[str, Any]:
        """阶段4: 测试用例验证"""
        logger.info("\n" + "="*40)
        logger.info("阶段4: 测试用例验证")
        logger.info("="*40)

        stage_result = {
            "stage_name": "测试用例验证",
            "stage_id": "test_case_validation",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {},
            "errors": []
        }

        try:
            # 生成真实场景测试用例
            test_cases = self.test_generator.generate_real_scenario_test_cases()
            stage_result["details"]["generated_test_cases"] = len(test_cases)

            # 验证测试用例
            validated_cases = 0
            for case in test_cases:
                if self._validate_test_case(case):
                    validated_cases += 1

            stage_result["details"]["validated_test_cases"] = validated_cases
            stage_result["details"]["test_cases"] = [
                {
                    "test_id": case.test_id,
                    "scenario_name": case.scenario_name,
                    "stock_code": case.stock_code,
                    "priority": case.test_priority
                }
                for case in test_cases
            ]

            stage_result["success"] = True
            logger.info(f"测试用例验证完成 - 生成了 {len(test_cases)} 个用例，验证了 {validated_cases} 个")

        except Exception as e:
            logger.error(f"测试用例验证阶段异常: {e}")
            stage_result["errors"].append(f"阶段执行异常: {str(e)}")

        stage_result["end_time"] = datetime.now().isoformat()
        return stage_result

    def _execute_real_scenario_testing_stage(self) -> Dict[str, Any]:
        """阶段5: 真实场景测试执行"""
        logger.info("\n" + "="*40)
        logger.info("阶段5: 真实场景测试执行")
        logger.info("="*40)

        stage_result = {
            "stage_name": "真实场景测试执行",
            "stage_id": "real_scenario_testing",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {},
            "errors": []
        }

        try:
            # 执行标准化测试工作流
            workflow_result = self.workflow_manager.execute_workflow(self.config_file)
            stage_result["details"]["workflow_result"] = workflow_result

            if workflow_result.get("success", False):
                stage_result["success"] = True
                logger.info("真实场景测试执行阶段完成")
            else:
                stage_result["errors"].append(
                    workflow_result.get("error", "测试执行失败")
                )
                logger.error("真实场景测试执行阶段失败")

        except Exception as e:
            logger.error(f"真实场景测试执行阶段异常: {e}")
            stage_result["errors"].append(f"阶段执行异常: {str(e)}")

        stage_result["end_time"] = datetime.now().isoformat()
        return stage_result

    def _execute_post_test_consistency_check(self) -> Dict[str, Any]:
        """阶段6: 测试后环境一致性验证"""
        logger.info("\n" + "="*40)
        logger.info("阶段6: 测试后环境一致性验证")
        logger.info("="*40)

        stage_result = {
            "stage_name": "测试后环境一致性验证",
            "stage_id": "post_test_consistency",
            "start_time": datetime.now().isoformat(),
            "success": False,
            "details": {},
            "errors": []
        }

        try:
            # 创建测试后快照
            post_test_snapshot = self.consistency_manager.create_snapshot(
                f"测试会话 {self.test_session_id} - 测试后快照"
            )
            stage_result["details"]["post_test_snapshot_id"] = post_test_snapshot.snapshot_id

            # 执行环境监控
            post_monitoring_results = self.consistency_manager.monitor_environment()
            stage_result["details"]["post_monitoring_results"] = post_monitoring_results

            # 比较测试前后的环境状态
            comparison = self._compare_environment_states(
                self.current_snapshot_id, post_test_snapshot.snapshot_id
            )
            stage_result["details"]["environment_comparison"] = comparison

            # 生成一致性报告
            consistency_report = self.consistency_manager.generate_consistency_report()
            stage_result["details"]["consistency_report"] = consistency_report

            stage_result["success"] = True
            logger.info("测试后环境一致性验证完成")

        except Exception as e:
            logger.error(f"测试后环境一致性验证异常: {e}")
            stage_result["errors"].append(f"阶段执行异常: {str(e)}")

        stage_result["end_time"] = datetime.now().isoformat()
        return stage_result

    def _validate_test_case(self, test_case: Any) -> bool:
        """验证单个测试用例"""
        try:
            # 基本字段验证
            required_fields = ['test_id', 'stock_code', 'stock_name', 'document_type']
            for field in required_fields:
                if not hasattr(test_case, field) or not getattr(test_case, field):
                    logger.warning(f"测试用例缺少必需字段 {field}: {test_case}")
                    return False

            # 路径验证
            expected_dir = self.config.get("expected_result_dir", "end2end_test/expected_results")
            if not os.path.exists(expected_dir):
                logger.warning(f"预期结果目录不存在: {expected_dir}")
                return False

            return True

        except Exception as e:
            logger.error(f"验证测试用例异常: {e}")
            return False

    def _compare_environment_states(self, before_snapshot_id: str, after_snapshot_id: str) -> Dict[str, Any]:
        """比较测试前后的环境状态"""
        comparison = {
            "snapshot_comparison": {
                "before": before_snapshot_id,
                "after": after_snapshot_id
            },
            "differences": {},
            "summary": {}
        }

        try:
            # 加载两个快照
            before_snapshot = self.consistency_manager.load_snapshot(before_snapshot_id)
            after_snapshot = self.consistency_manager.load_snapshot(after_snapshot_id)

            if before_snapshot and after_snapshot:
                # 比较文件数量变化
                before_files = len(before_snapshot.files)
                after_files = len(after_snapshot.files)
                comparison["differences"]["file_count_change"] = after_files - before_files

                # 比较目录结构变化
                before_dirs = len(before_snapshot.directories)
                after_dirs = len(after_snapshot.directories)
                comparison["differences"]["directory_count_change"] = after_dirs - before_dirs

                # 比较配置文件变化
                before_configs = len(before_snapshot.config_files)
                after_configs = len(after_snapshot.config_files)
                comparison["differences"]["config_file_change"] = after_configs - before_configs

                comparison["summary"] = {
                    "total_changes": sum(1 for v in comparison["differences"].values() if v != 0),
                    "significant_changes": any(abs(v) > 5 for v in comparison["differences"].values())
                }

        except Exception as e:
            logger.error(f"比较环境状态异常: {e}")
            comparison["error"] = str(e)

        return comparison

    def _generate_workflow_recommendations(self, workflow_report: Dict[str, Any]) -> None:
        """生成工作流建议"""
        recommendations = []

        # 分析各阶段的执行情况
        failed_stages = [stage for stage in workflow_report["stages"] if not stage.get("success", False)]

        if failed_stages:
            recommendations.append({
                "type": "failed_stages",
                "priority": "high",
                "message": f"以下阶段执行失败: {', '.join([stage['stage_name'] for stage in failed_stages])}",
                "action": "review_failed_stages"
            })

        # 分析环境一致性
        consistency_stages = [stage for stage in workflow_report["stages"]
                            if "consistency" in stage.get("stage_id", "")]
        if consistency_stages:
            for stage in consistency_stages:
                monitoring_results = stage.get("details", {}).get("monitoring_results", {})
                if monitoring_results.get("failed_checks", 0) > 0:
                    recommendations.append({
                        "type": "environment_issues",
                        "priority": "medium",
                        "message": f"阶段 {stage['stage_name']} 发现环境问题",
                        "action": "review_monitoring_rules"
                    })

        # 分析测试执行情况
        testing_stages = [stage for stage in workflow_report["stages"]
                         if "testing" in stage.get("stage_id", "")]
        if testing_stages:
            for stage in testing_stages:
                details = stage.get("details", {})
                if "validated_test_cases" in details:
                    case_count = details["validated_test_cases"]
                    if case_count < 5:
                        recommendations.append({
                            "type": "test_coverage",
                            "priority": "medium",
                            "message": f"验证的测试用例数量较少: {case_count}",
                            "action": "expand_test_cases"
                        })

        workflow_report["recommendations"] = recommendations

    def _finalize_workflow_report(self, workflow_report: Dict[str, Any]) -> Dict[str, Any]:
        """完成工作流报告"""
        workflow_report["end_time"] = datetime.now().isoformat()

        # 计算执行时长
        try:
            start_time = datetime.fromisoformat(workflow_report["start_time"])
            end_time = datetime.fromisoformat(workflow_report["end_time"])
            duration = end_time - start_time
            workflow_report["execution_duration_seconds"] = int(duration.total_seconds())
        except Exception:
            workflow_report["execution_duration_seconds"] = 0

        # 保存报告
        self._save_workflow_report(workflow_report)

        return workflow_report

    def _save_workflow_report(self, report: Dict[str, Any]) -> None:
        """保存工作流报告"""
        try:
            reports_dir = Path("test_environment/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)

            report_file = reports_dir / f"integrated_test_report_{self.test_session_id}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"集成测试报告已保存到: {report_file}")

        except Exception as e:
            logger.error(f"保存工作流报告失败: {e}")

    def generate_summary_report(self) -> Dict[str, Any]:
        """生成汇总报告"""
        logger.info("生成集成测试汇总报告")

        # 获取最新的工作流报告
        reports_dir = Path("test_environment/reports")
        if not reports_dir.exists():
            return {"error": "没有找到测试报告目录"}

        # 查找最新的报告文件
        report_files = list(reports_dir.glob("integrated_test_report_*.json"))
        if not report_files:
            return {"error": "没有找到测试报告文件"}

        latest_report_file = max(report_files, key=lambda x: x.stat().st_mtime)

        try:
            with open(latest_report_file, 'r', encoding='utf-8') as f:
                workflow_report = json.load(f)

            # 生成汇总
            summary = {
                "summary_timestamp": datetime.now().isoformat(),
                "session_id": workflow_report.get("session_id"),
                "execution_duration": workflow_report.get("execution_duration_seconds", 0),
                "overall_success": workflow_report.get("overall_success", False),
                "stages_executed": len(workflow_report.get("stages", [])),
                "successful_stages": len([s for s in workflow_report.get("stages", []) if s.get("success", False)]),
                "total_errors": len(workflow_report.get("errors", [])),
                "recommendations_count": len(workflow_report.get("recommendations", [])),
                "environment_snapshots": len(self.consistency_manager.list_snapshots()),
                "key_metrics": self._extract_key_metrics(workflow_report)
            }

            return summary

        except Exception as e:
            return {"error": f"读取报告文件失败: {str(e)}"}

    def _extract_key_metrics(self, workflow_report: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键指标"""
        metrics = {}

        # 从各阶段提取指标
        for stage in workflow_report.get("stages", []):
            stage_id = stage.get("stage_id", "")
            details = stage.get("details", {})

            if stage_id == "consistency_check":
                monitoring = details.get("monitoring_results", {})
                metrics["environment_checks"] = {
                    "total": monitoring.get("total_rules", 0),
                    "passed": monitoring.get("passed_checks", 0),
                    "failed": monitoring.get("failed_checks", 0)
                }

            elif stage_id == "test_case_validation":
                metrics["test_cases"] = {
                    "generated": details.get("generated_test_cases", 0),
                    "validated": details.get("validated_test_cases", 0)
                }

            elif stage_id == "document_classification":
                statistics = details.get("statistics", {})
                if statistics:
                    metrics["document_classification"] = {
                        "total_documents": statistics.get("total_documents", 0),
                        "companies_covered": len(statistics.get("by_company", {})),
                        "document_types": len(statistics.get("by_type", {}))
                    }

        return metrics


def main():
    """主函数 - 执行完整的集成测试工作流"""
    print("=" * 60)
    print("集成测试编排器")
    print("=" * 60)

    # 初始化编排器
    orchestrator = IntegratedTestOrchestrator()

    # 执行完整工作流
    print("\n开始执行完整集成测试工作流...")
    workflow_report = orchestrator.execute_full_test_workflow()

    # 显示执行结果
    print("\n" + "="*40)
    print("工作流执行结果")
    print("="*40)

    print(f"会话ID: {workflow_report['session_id']}")
    print(f"执行时长: {workflow_report.get('execution_duration_seconds', 0)} 秒")
    print(f"整体成功: {'是' if workflow_report.get('overall_success', False) else '否'}")
    print(f"执行阶段数: {len(workflow_report.get('stages', []))}")

    print("\n各阶段执行情况:")
    for stage in workflow_report.get('stages', []):
        status = "[PASS]" if stage.get('success', False) else "[FAIL]"
        print(f"  {status} {stage.get('stage_name', 'Unknown Stage')}")

    if workflow_report.get('errors'):
        print(f"\n错误信息 ({len(workflow_report['errors'])} 项):")
        for error in workflow_report['errors'][:3]:  # 只显示前3个错误
            print(f"  - {error}")

    if workflow_report.get('recommendations'):
        print(f"\n建议 ({len(workflow_report['recommendations'])} 项):")
        for rec in workflow_report['recommendations']:
            print(f"  - [{rec.get('priority', 'N/A')}] {rec.get('message', '')}")

    # 生成汇总报告
    print("\n生成汇总报告...")
    summary = orchestrator.generate_summary_report()

    if "error" not in summary:
        print("\n关键指标:")
        metrics = summary.get("key_metrics", {})

        if "environment_checks" in metrics:
            env = metrics["environment_checks"]
            print(f"  环境检查: {env['passed']}/{env['total']} 通过")

        if "test_cases" in metrics:
            tc = metrics["test_cases"]
            print(f"  测试用例: {tc['validated']}/{tc['generated']} 验证通过")

        if "document_classification" in metrics:
            dc = metrics["document_classification"]
            print(f"  文档分类: {dc['total_documents']} 个文档，{dc['companies_covered']} 家公司")

    print("\n集成测试工作流执行完成!")


if __name__ == "__main__":
    main()