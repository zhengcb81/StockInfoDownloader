#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续改进机制系统
提供文档更新、用例调整、质量监控等功能
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ImprovementAction:
    """改进动作"""
    action_id: str
    action_type: str  # 'document_update', 'testcase_adjust', 'quality_monitor', 'performance_optimize'
    title: str
    description: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    target_component: str
    current_state: Dict[str, Any]
    desired_state: Dict[str, Any]
    implementation_steps: List[str]
    verification_criteria: List[str]
    estimated_effort: str
    created_time: datetime
    due_date: Optional[datetime] = None
    status: str = "pending"  # 'pending', 'in_progress', 'completed', 'cancelled'
    assignee: str = ""
    progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['created_time'] = self.created_time.isoformat()
        if self.due_date:
            data['due_date'] = self.due_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImprovementAction':
        """从字典创建实例"""
        if data.get('created_time'):
            data['created_time'] = datetime.fromisoformat(data['created_time'])
        if data.get('due_date'):
            data['due_date'] = datetime.fromisoformat(data['due_date'])
        return cls(**data)


@dataclass
class QualityMetric:
    """质量指标"""
    metric_id: str
    metric_name: str
    metric_type: str  # 'performance', 'reliability', 'coverage', 'efficiency'
    current_value: float
    target_value: float
    unit: str
    measurement_frequency: str  # 'daily', 'weekly', 'monthly'
    trend_direction: str  # 'improving', 'stable', 'declining'
    last_measured: datetime
    historical_values: List[Tuple[datetime, float]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['last_measured'] = self.last_measured.isoformat()
        data['historical_values'] = [
            (t.isoformat(), v) for t, v in self.historical_values
        ]
        return data


@dataclass
class ImprovementCycle:
    """改进周期"""
    cycle_id: str
    cycle_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "active"  # 'active', 'completed', 'paused'
    actions: List[str] = None  # action_id列表
    metrics_monitored: List[str] = None  # metric_id列表
    outcomes: Dict[str, Any] = None
    lessons_learned: List[str] = None

    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.metrics_monitored is None:
            self.metrics_monitored = []
        if self.outcomes is None:
            self.outcomes = {}
        if self.lessons_learned is None:
            self.lessons_learned = []


class ContinuousImprovementSystem:
    """持续改进系统"""

    def __init__(self, config_file: str = "config_end2end_test.json"):
        self.config_file = config_file
        self.config = self._load_config()

        # 系统会话ID
        self.system_session_id = f"IMPROVEMENT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 数据存储
        self.improvement_actions: List[ImprovementAction] = []
        self.quality_metrics: List[QualityMetric] = []
        self.improvement_cycles: List[ImprovementCycle] = []

        # 配置文件路径
        self.data_dir = Path("test_environment/improvement_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 历史数据文件
        self.actions_file = self.data_dir / "improvement_actions.json"
        self.metrics_file = self.data_dir / "quality_metrics.json"
        self.cycles_file = self.data_dir / "improvement_cycles.json"

        # 加载历史数据
        self._load_historical_data()

        # 改进规则
        self.improvement_rules = self._initialize_improvement_rules()

        logger.info(f"持续改进系统初始化完成 - 会话ID: {self.system_session_id}")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def _load_historical_data(self):
        """加载历史数据"""
        try:
            # 加载改进动作
            if self.actions_file.exists():
                with open(self.actions_file, 'r', encoding='utf-8') as f:
                    actions_data = json.load(f)
                    self.improvement_actions = [
                        ImprovementAction.from_dict(action) for action in actions_data
                    ]

            # 加载质量指标
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)
                    for metric_data in metrics_data:
                        metric_data['last_measured'] = datetime.fromisoformat(metric_data['last_measured'])
                        metric_data['historical_values'] = [
                            (datetime.fromisoformat(t), v) for t, v in metric_data['historical_values']
                        ]
                        self.quality_metrics.append(QualityMetric(**metric_data))

            # 加载改进周期
            if self.cycles_file.exists():
                with open(self.cycles_file, 'r', encoding='utf-8') as f:
                    cycles_data = json.load(f)
                    for cycle_data in cycles_data:
                        cycle_data['start_time'] = datetime.fromisoformat(cycle_data['start_time'])
                        if cycle_data.get('end_time'):
                            cycle_data['end_time'] = datetime.fromisoformat(cycle_data['end_time'])
                        self.improvement_cycles.append(ImprovementCycle(**cycle_data))

            logger.info(f"加载历史数据: {len(self.improvement_actions)} 个动作, {len(self.quality_metrics)} 个指标, {len(self.improvement_cycles)} 个周期")

        except Exception as e:
            logger.error(f"加载历史数据失败: {e}")

    def _save_historical_data(self):
        """保存历史数据"""
        try:
            # 保存改进动作
            with open(self.actions_file, 'w', encoding='utf-8') as f:
                actions_data = [action.to_dict() for action in self.improvement_actions]
                json.dump(actions_data, f, ensure_ascii=False, indent=2)

            # 保存质量指标
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                metrics_data = [metric.to_dict() for metric in self.quality_metrics]
                json.dump(metrics_data, f, ensure_ascii=False, indent=2)

            # 保存改进周期
            with open(self.cycles_file, 'w', encoding='utf-8') as f:
                cycles_data = [asdict(cycle) for cycle in self.improvement_cycles]
                for cycle_data in cycles_data:
                    cycle_data['start_time'] = cycle_data['start_time'].isoformat()
                    if cycle_data.get('end_time'):
                        cycle_data['end_time'] = cycle_data['end_time'].isoformat()
                json.dump(cycles_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")

    def _initialize_improvement_rules(self) -> Dict[str, Any]:
        """初始化改进规则"""
        return {
            "performance_rules": {
                "slow_test_threshold": 120,  # 秒
                "low_success_rate_threshold": 0.8,
                "high_failure_rate_threshold": 0.2
            },
            "coverage_rules": {
                "min_test_coverage": 0.7,
                "min_dimension_coverage": 0.6,
                "critical_path_coverage": 0.9
            },
            "quality_rules": {
                "min_confidence_score": 0.7,
                "max_error_rate": 0.1,
                "min_recovery_rate": 0.8
            },
            "frequency_rules": {
                "daily_metrics": ["test_success_rate", "execution_time"],
                "weekly_metrics": ["coverage_score", "quality_index"],
                "monthly_metrics": ["performance_trend", "improvement_rate"]
            }
        }

    def analyze_test_results_and_suggest_improvements(self, test_reports_dir: str = "test_environment") -> List[ImprovementAction]:
        """分析测试结果并提出改进建议"""
        logger.info("开始分析测试结果并提出改进建议...")

        suggestions = []

        try:
            # 收集测试报告数据
            test_data = self._collect_test_data(test_reports_dir)

            # 分析性能问题
            performance_suggestions = self._analyze_performance_issues(test_data)
            suggestions.extend(performance_suggestions)

            # 分析覆盖度问题
            coverage_suggestions = self._analyze_coverage_issues(test_data)
            suggestions.extend(coverage_suggestions)

            # 分析质量问题
            quality_suggestions = self._analyze_quality_issues(test_data)
            suggestions.extend(quality_suggestions)

            # 分析异常模式
            anomaly_suggestions = self._analyze_anomaly_patterns(test_data)
            suggestions.extend(anomaly_suggestions)

            # 过滤和优先级排序
            filtered_suggestions = self._filter_and_prioritize_suggestions(suggestions)

            # 保存改进建议
            for suggestion in filtered_suggestions:
                self.improvement_actions.append(suggestion)

            self._save_historical_data()

            logger.info(f"分析完成，生成 {len(filtered_suggestions)} 个改进建议")
            return filtered_suggestions

        except Exception as e:
            logger.error(f"分析测试结果失败: {e}")
            return []

    def _collect_test_data(self, test_reports_dir: str) -> Dict[str, Any]:
        """收集测试数据"""
        test_data = {
            "integration_reports": [],
            "multidimensional_reports": [],
            "validation_reports": [],
            "boundary_reports": [],
            "exception_reports": [],
            "summary_metrics": {}
        }

        reports_path = Path(test_reports_dir)
        if not reports_path.exists():
            return test_data

        # 收集各类测试报告
        report_patterns = [
            ("integration", "reports/integrated_test_report_*.json"),
            ("multidimensional", "multidimensional_reports/*.json"),
            ("validation", "validation_reports/*.json"),
            ("boundary", "boundary_test_reports/*.json"),
            ("exception", "exception_test_reports/*.json")
        ]

        for report_type, pattern in report_patterns:
            for report_file in reports_path.rglob(pattern):
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                        test_data[f"{report_type}_reports"].append(report_data)
                except Exception as e:
                    logger.warning(f"读取报告文件失败 {report_file}: {e}")

        # 计算汇总指标
        test_data["summary_metrics"] = self._calculate_summary_metrics(test_data)

        return test_data

    def _calculate_summary_metrics(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算汇总指标"""
        metrics = {
            "total_success_rate": 0.0,
            "average_execution_time": 0.0,
            "coverage_score": 0.0,
            "quality_score": 0.0,
            "recovery_rate": 0.0,
            "total_tests": 0,
            "successful_tests": 0,
            "failed_tests": 0
        }

        # 从集成测试报告中提取数据
        integration_reports = test_data.get("integration_reports", [])
        if integration_reports:
            total_success = sum(1 for report in integration_reports if report.get("overall_success", False))
            metrics["integration_success_rate"] = total_success / len(integration_reports)

        # 从多维度测试报告中提取数据
        multidimensional_reports = test_data.get("multidimensional_reports", [])
        if multidimensional_reports:
            success_rates = [report.get("summary", {}).get("success_rate", 0) for report in multidimensional_reports]
            if success_rates:
                metrics["multidimensional_success_rate"] = sum(success_rates) / len(success_rates)

        # 从验证报告中提取数据
        validation_reports = test_data.get("validation_reports", [])
        if validation_reports:
            confidence_scores = [report.get("summary", {}).get("average_confidence_score", 0) for report in validation_reports]
            if confidence_scores:
                metrics["average_confidence_score"] = sum(confidence_scores) / len(confidence_scores)

        # 从边界测试报告中提取数据
        boundary_reports = test_data.get("boundary_reports", [])
        if boundary_reports:
            recovery_rates = [report.get("summary", {}).get("recovery_success_rate", 0) for report in boundary_reports]
            if recovery_rates:
                metrics["boundary_recovery_rate"] = sum(recovery_rates) / len(recovery_rates)

        return metrics

    def _analyze_performance_issues(self, test_data: Dict[str, Any]) -> List[ImprovementAction]:
        """分析性能问题"""
        suggestions = []
        metrics = test_data["summary_metrics"]

        # 检查执行时间
        avg_time = metrics.get("average_execution_time", 0)
        if avg_time > self.improvement_rules["performance_rules"]["slow_test_threshold"]:
            suggestion = ImprovementAction(
                action_id=f"PERF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action_type="performance_optimize",
                title="优化测试执行性能",
                description=f"平均执行时间 {avg_time:.1f}s 超过阈值 {self.improvement_rules['performance_rules']['slow_test_threshold']}s",
                priority="high",
                target_component="test_execution",
                current_state={"average_time": avg_time},
                desired_state={"average_time": self.improvement_rules["performance_rules"]["slow_test_threshold"]},
                implementation_steps=[
                    "分析性能瓶颈",
                    "优化测试并发策略",
                    "改进资源管理",
                    "优化网络请求处理"
                ],
                verification_criteria=[
                    "平均执行时间 < 120s",
                    "性能提升 > 20%"
                ],
                estimated_effort="2-3天",
                created_time=datetime.now()
            )
            suggestions.append(suggestion)

        # 检查成功率
        success_rate = metrics.get("total_success_rate", 0)
        if success_rate < self.improvement_rules["performance_rules"]["low_success_rate_threshold"]:
            suggestion = ImprovementAction(
                action_id=f"SUCCESS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action_type="quality_monitor",
                title="提升测试成功率",
                description=f"测试成功率 {success_rate:.1%} 低于阈值 {self.improvement_rules['performance_rules']['low_success_rate_threshold']:.1%}",
                priority="critical",
                target_component="test_reliability",
                current_state={"success_rate": success_rate},
                desired_state={"success_rate": self.improvement_rules["performance_rules"]["low_success_rate_threshold"]},
                implementation_steps=[
                    "分析失败原因",
                    "改进错误处理机制",
                    "增强测试稳定性",
                    "优化网络连接策略"
                ],
                verification_criteria=[
                    "成功率 > 85%",
                    "失败率 < 15%"
                ],
                estimated_effort="3-5天",
                created_time=datetime.now()
            )
            suggestions.append(suggestion)

        return suggestions

    def _analyze_coverage_issues(self, test_data: Dict[str, Any]) -> List[ImprovementAction]:
        """分析覆盖度问题"""
        suggestions = []

        # 检查测试覆盖度
        coverage_score = test_data["summary_metrics"].get("coverage_score", 0)
        if coverage_score < self.improvement_rules["coverage_rules"]["min_test_coverage"]:
            suggestion = ImprovementAction(
                action_id=f"COVERAGE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action_type="testcase_adjust",
                title="提升测试覆盖度",
                description=f"测试覆盖度 {coverage_score:.1%} 低于最小要求 {self.improvement_rules['coverage_rules']['min_test_coverage']:.1%}",
                priority="medium",
                target_component="test_coverage",
                current_state={"coverage_score": coverage_score},
                desired_state={"coverage_score": self.improvement_rules["coverage_rules"]["min_test_coverage"]},
                implementation_steps=[
                    "分析未覆盖的功能模块",
                    "设计新的测试用例",
                    "增加边界条件测试",
                    "扩展异常场景测试"
                ],
                verification_criteria=[
                    "覆盖度 > 70%",
                    "关键路径覆盖 > 90%"
                ],
                estimated_effort="1-2周",
                created_time=datetime.now()
            )
            suggestions.append(suggestion)

        return suggestions

    def _analyze_quality_issues(self, test_data: Dict[str, Any]) -> List[ImprovementAction]:
        """分析质量问题"""
        suggestions = []

        # 检查质量评分
        quality_score = test_data["summary_metrics"].get("quality_score", 0)
        if quality_score < self.improvement_rules["quality_rules"]["min_confidence_score"]:
            suggestion = ImprovementAction(
                action_id=f"QUALITY_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action_type="quality_monitor",
                title="提升测试质量",
                description=f"测试质量评分 {quality_score:.1%} 低于最小要求 {self.improvement_rules['quality_rules']['min_confidence_score']:.1%}",
                priority="medium",
                target_component="test_quality",
                current_state={"quality_score": quality_score},
                desired_state={"quality_score": self.improvement_rules["quality_rules"]["min_confidence_score"]},
                implementation_steps=[
                    "分析质量问题根因",
                    "改进测试数据质量",
                    "增强验证机制",
                    "完善错误处理"
                ],
                verification_criteria=[
                    "质量评分 > 70%",
                    "错误率 < 10%"
                ],
                estimated_effort="1-2周",
                created_time=datetime.now()
            )
            suggestions.append(suggestion)

        # 检查恢复率
        recovery_rate = test_data["summary_metrics"].get("recovery_rate", 0)
        if recovery_rate < self.improvement_rules["quality_rules"]["min_recovery_rate"]:
            suggestion = ImprovementAction(
                action_id=f"RECOVERY_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action_type="performance_optimize",
                title="改进异常恢复机制",
                description=f"异常恢复率 {recovery_rate:.1%} 低于最小要求 {self.improvement_rules['quality_rules']['min_recovery_rate']:.1%}",
                priority="high",
                target_component="error_recovery",
                current_state={"recovery_rate": recovery_rate},
                desired_state={"recovery_rate": self.improvement_rules["quality_rules"]["min_recovery_rate"]},
                implementation_steps=[
                    "分析恢复失败原因",
                    "改进重试机制",
                    "增强错误检测",
                    "优化恢复策略"
                ],
                verification_criteria=[
                    "恢复率 > 80%",
                    "自动恢复成功 > 90%"
                ],
                estimated_effort="1周",
                created_time=datetime.now()
            )
            suggestions.append(suggestion)

        return suggestions

    def _analyze_anomaly_patterns(self, test_data: Dict[str, Any]) -> List[ImprovementAction]:
        """分析异常模式"""
        suggestions = []

        # 分析失败的测试模式
        failure_patterns = self._identify_failure_patterns(test_data)
        if failure_patterns:
            suggestion = ImprovementAction(
                action_id=f"ANOMALY_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                action_type="quality_monitor",
                title="解决异常模式问题",
                description=f"发现 {len(failure_patterns)} 个异常模式需要处理",
                priority="medium",
                target_component="anomaly_detection",
                current_state={"patterns": failure_patterns},
                desired_state={"patterns": []},
                implementation_steps=[
                    "深入分析异常模式",
                    "制定针对性解决方案",
                    "实施预防措施",
                    "建立监控机制"
                ],
                verification_criteria=[
                    "异常模式消除",
                    "稳定性提升 > 15%"
                ],
                estimated_effort="1-2周",
                created_time=datetime.now()
            )
            suggestions.append(suggestion)

        return suggestions

    def _identify_failure_patterns(self, test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别失败模式"""
        patterns = []

        # 这里可以实现更复杂的模式识别逻辑
        # 简化版：基于已知的常见问题生成模式

        # 检查是否有网络相关问题
        if any("network" in str(report).lower() for report in test_data.get("integration_reports", [])):
            patterns.append({
                "type": "network_connectivity",
                "frequency": "multiple",
                "impact": "medium",
                "description": "网络连接稳定性问题"
            })

        # 检查是否有超时相关问题
        if any("timeout" in str(report).lower() for report in test_data.get("boundary_reports", [])):
            patterns.append({
                "type": "timeout_handling",
                "frequency": "multiple",
                "impact": "high",
                "description": "超时处理机制问题"
            })

        return patterns

    def _filter_and_prioritize_suggestions(self, suggestions: List[ImprovementAction]) -> List[ImprovementAction]:
        """过滤和优先级排序建议"""
        # 去重
        seen_titles = set()
        filtered = []
        for suggestion in suggestions:
            if suggestion.title not in seen_titles:
                seen_titles.add(suggestion.title)
                filtered.append(suggestion)

        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        filtered.sort(key=lambda x: priority_order.get(x.priority, 4))

        return filtered

    def create_improvement_cycle(self, cycle_name: str, action_ids: List[str] = None, duration_days: int = 30) -> ImprovementCycle:
        """创建改进周期"""
        cycle_id = f"CYCLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if action_ids is None:
            # 选择高优先级的待处理动作
            action_ids = [
                action.action_id for action in self.improvement_actions
                if action.status == "pending" and action.priority in ["critical", "high"]
            ][:5]  # 最多5个动作

        cycle = ImprovementCycle(
            cycle_id=cycle_id,
            cycle_name=cycle_name,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(days=duration_days),
            actions=action_ids,
            metrics_monitored=self._select_relevant_metrics(action_ids)
        )

        self.improvement_cycles.append(cycle)
        self._save_historical_data()

        logger.info(f"创建改进周期: {cycle_name} (ID: {cycle_id})")
        return cycle

    def _select_relevant_metrics(self, action_ids: List[str]) -> List[str]:
        """选择相关指标"""
        # 根据动作类型选择相关指标
        relevant_metrics = []

        for action_id in action_ids:
            action = next((a for a in self.improvement_actions if a.action_id == action_id), None)
            if action:
                if action.action_type in ["performance_optimize"]:
                    relevant_metrics.extend(["execution_time", "success_rate"])
                elif action.action_type in ["quality_monitor"]:
                    relevant_metrics.extend(["quality_score", "error_rate"])
                elif action.action_type in ["testcase_adjust"]:
                    relevant_metrics.extend(["coverage_score", "test_effectiveness"])

        return list(set(relevant_metrics))  # 去重

    def monitor_quality_metrics(self) -> Dict[str, Any]:
        """监控质量指标"""
        logger.info("开始监控质量指标...")

        monitoring_report = {
            "monitoring_session_id": self.system_session_id,
            "monitoring_time": datetime.now().isoformat(),
            "metrics_status": {},
            "trends": {},
            "alerts": [],
            "recommendations": []
        }

        # 更新指标值
        for metric in self.quality_metrics:
            current_value = self._measure_metric(metric)
            if current_value is not None:
                # 更新历史值
                metric.historical_values.append((datetime.now(), current_value))
                metric.current_value = current_value
                metric.last_measured = datetime.now()

                # 分析趋势
                metric.trend_direction = self._analyze_trend(metric.historical_values)

                monitoring_report["metrics_status"][metric.metric_id] = {
                    "current_value": current_value,
                    "target_value": metric.target_value,
                    "trend": metric.trend_direction,
                    "status": "on_track" if current_value >= metric.target_value else "needs_attention"
                }

        # 生成警报
        alerts = self._generate_metric_alerts()
        monitoring_report["alerts"] = alerts

        # 生成趋势分析
        monitoring_report["trends"] = self._generate_trend_analysis()

        # 生成建议
        monitoring_report["recommendations"] = self._generate_monitoring_recommendations(alerts)

        self._save_historical_data()

        logger.info(f"质量指标监控完成 - 监控了 {len(self.quality_metrics)} 个指标，发现 {len(alerts)} 个警报")
        return monitoring_report

    def _measure_metric(self, metric: QualityMetric) -> Optional[float]:
        """测量指标值"""
        # 这里应该实现实际的指标测量逻辑
        # 简化版：返回模拟数据
        if metric.metric_type == "performance":
            return random.uniform(0.7, 1.0)
        elif metric.metric_type == "reliability":
            return random.uniform(0.8, 1.0)
        elif metric.metric_type == "coverage":
            return random.uniform(0.6, 0.9)
        elif metric.metric_type == "efficiency":
            return random.uniform(0.7, 0.95)
        else:
            return random.uniform(0.7, 1.0)

    def _analyze_trend(self, historical_values: List[Tuple[datetime, float]]) -> str:
        """分析趋势"""
        if len(historical_values) < 2:
            return "stable"

        # 取最近的几个值
        recent_values = [value for _, value in historical_values[-5:]]
        if len(recent_values) < 2:
            return "stable"

        # 简单的趋势分析
        recent_avg = sum(recent_values[-3:]) / len(recent_values[-3:])
        earlier_avg = sum(recent_values[:3]) / len(recent_values[:3])

        if recent_avg > earlier_avg * 1.05:
            return "improving"
        elif recent_avg < earlier_avg * 0.95:
            return "declining"
        else:
            return "stable"

    def _generate_metric_alerts(self) -> List[Dict[str, Any]]:
        """生成指标警报"""
        alerts = []

        for metric in self.quality_metrics:
            # 检查是否低于目标值
            if metric.current_value < metric.target_value:
                alert = {
                    "alert_id": f"ALERT_{metric.metric_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "metric_id": metric.metric_id,
                    "metric_name": metric.metric_name,
                    "alert_type": "below_target",
                    "severity": "high" if metric.current_value < metric.target_value * 0.8 else "medium",
                    "message": f"指标 {metric.metric_name} 当前值 {metric.current_value:.2f} 低于目标值 {metric.target_value:.2f}",
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)

            # 检查趋势
            if metric.trend_direction == "declining":
                alert = {
                    "alert_id": f"TREND_{metric.metric_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "metric_id": metric.metric_id,
                    "metric_name": metric.metric_name,
                    "alert_type": "declining_trend",
                    "severity": "medium",
                    "message": f"指标 {metric.metric_name} 呈现下降趋势",
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)

        return alerts

    def _generate_trend_analysis(self) -> Dict[str, Any]:
        """生成趋势分析"""
        trends = {}

        for metric in self.quality_metrics:
            if len(metric.historical_values) >= 3:
                trends[metric.metric_id] = {
                    "metric_name": metric.metric_name,
                    "current_value": metric.current_value,
                    "trend_direction": metric.trend_direction,
                    "recent_change": self._calculate_recent_change(metric),
                    "forecast": self._simple_forecast(metric)
                }

        return trends

    def _calculate_recent_change(self, metric: QualityMetric) -> float:
        """计算近期变化"""
        if len(metric.historical_values) < 2:
            return 0.0

        latest_value = metric.historical_values[-1][1]
        previous_value = metric.historical_values[-2][1]

        if previous_value == 0:
            return 0.0

        return (latest_value - previous_value) / previous_value

    def _simple_forecast(self, metric: QualityMetric) -> float:
        """简单预测"""
        if len(metric.historical_values) < 3:
            return metric.current_value

        # 使用最近3个值的平均趋势进行简单预测
        recent_values = [value for _, value in metric.historical_values[-3:]]
        if len(recent_values) < 2:
            return metric.current_value

        # 计算平均变化率
        changes = []
        for i in range(1, len(recent_values)):
            if recent_values[i-1] != 0:
                changes.append((recent_values[i] - recent_values[i-1]) / recent_values[i-1])

        if not changes:
            return metric.current_value

        avg_change = sum(changes) / len(changes)
        forecast_value = metric.current_value * (1 + avg_change)

        return max(0.0, min(1.0, forecast_value))  # 限制在0-1范围内

    def _generate_monitoring_recommendations(self, alerts: List[Dict[str, Any]]) -> List[str]:
        """生成监控建议"""
        recommendations = []

        if not alerts:
            recommendations.append("所有指标表现良好，继续保持当前策略")
        else:
            high_priority_alerts = [a for a in alerts if a["severity"] == "high"]
            if high_priority_alerts:
                recommendations.append(f"优先处理 {len(high_priority_alerts)} 个高优先级警报")

            declining_metrics = set(a["metric_id"] for a in alerts if a["alert_type"] == "declining_trend")
            if declining_metrics:
                recommendations.append(f"关注 {len(declining_metrics)} 个下降趋势的指标")

        return recommendations

    def update_test_documentation(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """更新测试文档"""
        logger.info("开始更新测试文档...")

        update_report = {
            "update_session_id": self.system_session_id,
            "update_time": datetime.now().isoformat(),
            "updates_performed": [],
            "files_updated": [],
            "summary": {}
        }

        for update in updates:
            try:
                result = self._apply_documentation_update(update)
                update_report["updates_performed"].append(result)
                if result["success"]:
                    update_report["files_updated"].append(result["file_path"])
            except Exception as e:
                logger.error(f"应用文档更新失败: {e}")
                update_report["updates_performed"].append({
                    "update_id": update.get("update_id", "unknown"),
                    "success": False,
                    "error": str(e)
                })

        # 生成摘要
        update_report["summary"] = {
            "total_updates": len(updates),
            "successful_updates": len([u for u in update_report["updates_performed"] if u["success"]]),
            "files_updated_count": len(update_report["files_updated"]),
            "success_rate": len([u for u in update_report["updates_performed"] if u["success"]]) / len(updates) if updates else 0
        }

        logger.info(f"测试文档更新完成 - 成功: {update_report['summary']['successful_updates']}/{update_report['summary']['total_updates']}")
        return update_report

    def _apply_documentation_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """应用文档更新"""
        result = {
            "update_id": update.get("update_id", "unknown"),
            "file_path": "",
            "success": False,
            "changes_made": [],
            "error": ""
        }

        try:
            file_path = update.get("file_path")
            if not file_path or not os.path.exists(file_path):
                result["error"] = f"文件不存在: {file_path}"
                return result

            result["file_path"] = file_path

            # 备份原文件
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(file_path, backup_path)

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 应用更新
            updated_content = content
            changes = []

            if update.get("update_type") == "add_section":
                section_content = update.get("content", "")
                insert_position = update.get("position", "end")

                if insert_position == "end":
                    updated_content += f"\n\n{section_content}"
                else:
                    # 在指定位置插入（简化实现）
                    lines = updated_content.split('\n')
                    if insert_position < len(lines):
                        lines.insert(insert_position, section_content)
                        updated_content = '\n'.join(lines)

                changes.append(f"添加章节: {update.get('section_title', '未命名')}")

            elif update.get("update_type") == "update_config":
                # 更新配置文件
                if file_path.endswith('.json'):
                    try:
                        config_data = json.loads(content)
                        config_updates = update.get("config_updates", {})
                        config_data.update(config_updates)
                        updated_content = json.dumps(config_data, ensure_ascii=False, indent=2)
                        changes.append(f"更新配置: {', '.join(config_updates.keys())}")
                    except json.JSONDecodeError as e:
                        result["error"] = f"JSON解析错误: {e}"
                        return result

            # 写入更新后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            result["success"] = True
            result["changes_made"] = changes

        except Exception as e:
            result["error"] = str(e)

        return result

    def generate_improvement_report(self) -> Dict[str, Any]:
        """生成改进报告"""
        logger.info("生成改进系统报告...")

        report = {
            "report_id": self.system_session_id,
            "generation_time": datetime.now().isoformat(),
            "summary": {},
            "actions_status": {},
            "metrics_summary": {},
            "cycles_overview": {},
            "recommendations": []
        }

        # 生成摘要
        report["summary"] = {
            "total_actions": len(self.improvement_actions),
            "pending_actions": len([a for a in self.improvement_actions if a.status == "pending"]),
            "in_progress_actions": len([a for a in self.improvement_actions if a.status == "in_progress"]),
            "completed_actions": len([a for a in self.improvement_actions if a.status == "completed"]),
            "total_metrics": len(self.quality_metrics),
            "active_cycles": len([c for c in self.improvement_cycles if c.status == "active"]),
            "overall_health_score": self._calculate_overall_health_score()
        }

        # 动作状态
        action_stats = {}
        for action in self.improvement_actions:
            action_type = action.action_type
            if action_type not in action_stats:
                action_stats[action_type] = {"total": 0, "completed": 0}
            action_stats[action_type]["total"] += 1
            if action.status == "completed":
                action_stats[action_type]["completed"] += 1

        report["actions_status"] = action_stats

        # 指标摘要
        metrics_summary = {}
        for metric in self.quality_metrics:
            metric_type = metric.metric_type
            if metric_type not in metrics_summary:
                metrics_summary[metric_type] = {"count": 0, "avg_current": 0, "avg_target": 0}
            metrics_summary[metric_type]["count"] += 1
            metrics_summary[metric_type]["avg_current"] += metric.current_value
            metrics_summary[metric_type]["avg_target"] += metric.target_value

        for metric_type in metrics_summary:
            count = metrics_summary[metric_type]["count"]
            if count > 0:
                metrics_summary[metric_type]["avg_current"] /= count
                metrics_summary[metric_type]["avg_target"] /= count

        report["metrics_summary"] = metrics_summary

        # 周期概览
        cycles_overview = {
            "total_cycles": len(self.improvement_cycles),
            "active_cycles": len([c for c in self.improvement_cycles if c.status == "active"]),
            "completed_cycles": len([c for c in self.improvement_cycles if c.status == "completed"]),
            "avg_duration": 0
        }

        completed_cycles = [c for c in self.improvement_cycles if c.status == "completed" and c.end_time]
        if completed_cycles:
            total_duration = sum((c.end_time - c.start_time).days for c in completed_cycles)
            cycles_overview["avg_duration"] = total_duration / len(completed_cycles)

        report["cycles_overview"] = cycles_overview

        # 生成建议
        report["recommendations"] = self._generate_system_recommendations()

        logger.info("改进系统报告生成完成")
        return report

    def _calculate_overall_health_score(self) -> float:
        """计算整体健康评分"""
        if not self.quality_metrics:
            return 0.5

        # 基于指标完成度计算健康评分
        total_score = 0
        for metric in self.quality_metrics:
            if metric.target_value > 0:
                score = min(1.0, metric.current_value / metric.target_value)
                total_score += score

        return total_score / len(self.quality_metrics)

    def _generate_system_recommendations(self) -> List[str]:
        """生成系统建议"""
        recommendations = []

        # 基于动作状态生成建议
        pending_high_priority = len([
            a for a in self.improvement_actions
            if a.status == "pending" and a.priority in ["critical", "high"]
        ])

        if pending_high_priority > 3:
            recommendations.append(f"有 {pending_high_priority} 个高优先级待处理动作，建议优先处理")

        # 基于指标状态生成建议
        declining_metrics = len([
            m for m in self.quality_metrics if m.trend_direction == "declining"
        ])

        if declining_metrics > 0:
            recommendations.append(f"{declining_metrics} 个指标呈下降趋势，需要关注")

        # 基于周期状态生成建议
        active_cycles = len([
            c for c in self.improvement_cycles if c.status == "active"
        ])

        if active_cycles == 0:
            recommendations.append("当前没有活跃的改进周期，建议创建新的改进计划")

        if not recommendations:
            recommendations.append("系统运行良好，继续保持当前策略")

        return recommendations


# 需要导入random模块
import random

def main():
    """主函数 - 演示持续改进系统"""
    print("=" * 60)
    print("持续改进机制系统")
    print("=" * 60)

    # 初始化改进系统
    improvement_system = ContinuousImprovementSystem()

    # 分析测试结果并提出改进建议
    print("\n1. 分析测试结果并提出改进建议...")
    suggestions = improvement_system.analyze_test_results_and_suggest_improvements()

    print(f"   生成了 {len(suggestions)} 个改进建议")
    for suggestion in suggestions[:3]:  # 只显示前3个
        print(f"   - {suggestion.title} (优先级: {suggestion.priority})")

    # 创建改进周期
    print("\n2. 创建改进周期...")
    if suggestions:
        cycle = improvement_system.create_improvement_cycle(
            cycle_name="测试质量提升周期",
            action_ids=[s.action_id for s in suggestions[:2]]  # 选择前2个建议
        )
        print(f"   创建改进周期: {cycle.cycle_name}")
        print(f"   包含动作: {len(cycle.actions)} 个")

    # 监控质量指标
    print("\n3. 监控质量指标...")
    monitoring_report = improvement_system.monitor_quality_metrics()

    print(f"   监控指标数: {len(monitoring_report['metrics_status'])}")
    print(f"   生成警报: {len(monitoring_report['alerts'])} 个")

    # 生成改进报告
    print("\n4. 生成改进系统报告...")
    system_report = improvement_system.generate_improvement_report()

    summary = system_report["summary"]
    print(f"   总动作数: {summary['total_actions']}")
    print(f"   待处理: {summary['pending_actions']}")
    print(f"   已完成: {summary['completed_actions']}")
    print(f"   整体健康评分: {summary['overall_health_score']:.1%}")

    # 显示建议
    print("\n5. 系统建议:")
    for rec in system_report["recommendations"]:
        print(f"   - {rec}")

    print("\n持续改进机制演示完成!")


if __name__ == "__main__":
    main()