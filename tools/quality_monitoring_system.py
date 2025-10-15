#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
质量监控与报告系统
提供完整的测试质量监控、分析和报告功能
"""

import os
import sys
import json
import time
import sqlite3
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
# import matplotlib.pyplot as plt
# import pandas as pd
# 简化版本，不依赖外部库

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager
from smart_directory_cleaner import SmartDirectoryCleaner
from data_validation_framework import DataValidationFramework


@dataclass
class QualityMetric:
    """质量指标"""
    name: str
    value: float
    unit: str
    threshold: float
    status: str  # 'pass', 'warning', 'fail'
    timestamp: datetime
    description: str


@dataclass
class TestExecutionRecord:
    """测试执行记录"""
    execution_id: str
    timestamp: datetime
    test_name: str
    config_file: str
    total_test_cases: int
    successful_tests: int
    failed_tests: int
    validation_rate: float
    execution_time: float
    error_count: int
    status: str
    details: Dict[str, Any]


@dataclass
class QualityTrend:
    """质量趋势数据"""
    metric_name: str
    time_series: List[Tuple[datetime, float]]
    trend: str  # 'improving', 'declining', 'stable'
    change_rate: float


class QualityMonitoringSystem:
    """质量监控系统"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化质量监控系统

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.quality_dir = self.base_dir / "quality_monitoring"
        self.quality_dir.mkdir(parents=True, exist_ok=True)

        # 数据库文件
        self.db_file = self.quality_dir / "quality_metrics.db"

        # 报告目录
        self.reports_dir = self.quality_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

        # 图表目录
        self.charts_dir = self.quality_dir / "charts"
        self.charts_dir.mkdir(exist_ok=True)

        # 初始化数据库
        self._init_database()

        # 质量阈值配置
        self.quality_thresholds = {
            "validation_rate": {
                "excellent": 95.0,
                "good": 80.0,
                "acceptable": 60.0,
                "poor": 40.0
            },
            "execution_success_rate": {
                "excellent": 95.0,
                "good": 85.0,
                "acceptable": 70.0,
                "poor": 50.0
            },
            "test_coverage": {
                "excellent": 90.0,
                "good": 75.0,
                "acceptable": 60.0,
                "poor": 40.0
            },
            "performance": {
                "excellent": 300.0,  # 秒
                "good": 600.0,
                "acceptable": 900.0,
                "poor": 1800.0
            }
        }

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(str(self.db_file)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_executions (
                    execution_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    test_name TEXT,
                    config_file TEXT,
                    total_test_cases INTEGER,
                    successful_tests INTEGER,
                    failed_tests INTEGER,
                    validation_rate REAL,
                    execution_time REAL,
                    error_count INTEGER,
                    status TEXT,
                    details TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT,
                    metric_name TEXT,
                    value REAL,
                    unit TEXT,
                    threshold REAL,
                    status TEXT,
                    timestamp TEXT,
                    description TEXT,
                    FOREIGN KEY (execution_id) REFERENCES test_executions (execution_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    network_status TEXT,
                    environment_status TEXT
                )
            """)

    def record_test_execution(self, execution_data: Dict[str, Any]) -> str:
        """
        记录测试执行结果

        Args:
            execution_data: 执行数据

        Returns:
            执行ID
        """
        execution_id = execution_data.get("execution_id", f"exec_{int(time.time())}")

        record = TestExecutionRecord(
            execution_id=execution_id,
            timestamp=datetime.now(),
            test_name=execution_data.get("test_name", "unknown"),
            config_file=execution_data.get("config_file", ""),
            total_test_cases=execution_data.get("total_test_cases", 0),
            successful_tests=execution_data.get("successful_tests", 0),
            failed_tests=execution_data.get("failed_tests", 0),
            validation_rate=execution_data.get("validation_rate", 0.0),
            execution_time=execution_data.get("execution_time", 0.0),
            error_count=execution_data.get("error_count", 0),
            status=execution_data.get("status", "unknown"),
            details=execution_data.get("details", {})
        )

        with sqlite3.connect(str(self.db_file)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO test_executions
                (execution_id, timestamp, test_name, config_file, total_test_cases,
                 successful_tests, failed_tests, validation_rate, execution_time,
                 error_count, status, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.execution_id,
                record.timestamp.isoformat(),
                record.test_name,
                record.config_file,
                record.total_test_cases,
                record.successful_tests,
                record.failed_tests,
                record.validation_rate,
                record.execution_time,
                record.error_count,
                record.status,
                json.dumps(record.details)
            ))

        # 计算质量指标
        self._calculate_and_store_metrics(execution_id, record)

        return execution_id

    def _calculate_and_store_metrics(self, execution_id: str, record: TestExecutionRecord):
        """计算并存储质量指标"""
        metrics = []

        # 1. 验证率指标
        validation_rate = record.validation_rate
        validation_status = self._get_quality_status(validation_rate, "validation_rate")
        metrics.append(QualityMetric(
            name="validation_rate",
            value=validation_rate,
            unit="%",
            threshold=self.quality_thresholds["validation_rate"]["good"],
            status=validation_status,
            timestamp=datetime.now(),
            description="文档验证通过率"
        ))

        # 2. 执行成功率指标
        if record.total_test_cases > 0:
            success_rate = (record.successful_tests / record.total_test_cases) * 100
            success_status = self._get_quality_status(success_rate, "execution_success_rate")
            metrics.append(QualityMetric(
                name="execution_success_rate",
                value=success_rate,
                unit="%",
                threshold=self.quality_thresholds["execution_success_rate"]["good"],
                status=success_status,
                timestamp=datetime.now(),
                description="测试执行成功率"
            ))

        # 3. 性能指标
        performance_status = self._get_performance_status(record.execution_time)
        metrics.append(QualityMetric(
            name="execution_performance",
            value=record.execution_time,
            unit="seconds",
            threshold=self.quality_thresholds["performance"]["good"],
            status=performance_status,
            timestamp=datetime.now(),
            description="测试执行时间"
        ))

        # 4. 稳定性指标
        stability_score = max(0, 100 - (record.error_count * 10))
        stability_status = self._get_quality_status(stability_score, "execution_success_rate")
        metrics.append(QualityMetric(
            name="stability_score",
            value=stability_score,
            unit="score",
            threshold=self.quality_thresholds["execution_success_rate"]["good"],
            status=stability_status,
            timestamp=datetime.now(),
            description="系统稳定性评分"
        ))

        # 存储指标
        with sqlite3.connect(str(self.db_file)) as conn:
            for metric in metrics:
                conn.execute("""
                    INSERT INTO quality_metrics
                    (execution_id, metric_name, value, unit, threshold, status, timestamp, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    metric.name,
                    metric.value,
                    metric.unit,
                    metric.threshold,
                    metric.status,
                    metric.timestamp.isoformat(),
                    metric.description
                ))

    def _get_quality_status(self, value: float, metric_type: str) -> str:
        """获取质量状态"""
        thresholds = self.quality_thresholds.get(metric_type, {})

        if metric_type == "performance":
            # 性能指标：值越小越好
            if value <= thresholds.get("excellent", 300):
                return "excellent"
            elif value <= thresholds.get("good", 600):
                return "good"
            elif value <= thresholds.get("acceptable", 900):
                return "warning"
            else:
                return "fail"
        else:
            # 其他指标：值越大越好
            if value >= thresholds.get("excellent", 95):
                return "excellent"
            elif value >= thresholds.get("good", 80):
                return "good"
            elif value >= thresholds.get("acceptable", 60):
                return "warning"
            else:
                return "fail"

    def _get_performance_status(self, execution_time: float) -> str:
        """获取性能状态"""
        thresholds = self.quality_thresholds["performance"]

        if execution_time <= thresholds["excellent"]:
            return "excellent"
        elif execution_time <= thresholds["good"]:
            return "good"
        elif execution_time <= thresholds["acceptable"]:
            return "warning"
        else:
            return "fail"

    def get_quality_dashboard(self, days: int = 7) -> Dict[str, Any]:
        """
        获取质量仪表板数据

        Args:
            days: 分析天数

        Returns:
            仪表板数据
        """
        start_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(str(self.db_file)) as conn:
            # 获取最近的执行记录
            cursor = conn.execute("""
                SELECT * FROM test_executions
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (start_date.isoformat(),))

            executions = []
            for row in cursor.fetchall():
                executions.append({
                    "execution_id": row[0],
                    "timestamp": row[1],
                    "test_name": row[2],
                    "config_file": row[3],
                    "total_test_cases": row[4],
                    "successful_tests": row[5],
                    "failed_tests": row[6],
                    "validation_rate": row[7],
                    "execution_time": row[8],
                    "error_count": row[9],
                    "status": row[10],
                    "details": json.loads(row[11]) if row[11] else {}
                })

            # 获取质量指标
            cursor = conn.execute("""
                SELECT metric_name, AVG(value) as avg_value,
                       MIN(value) as min_value, MAX(value) as max_value,
                       COUNT(*) as count
                FROM quality_metrics
                WHERE timestamp >= ?
                GROUP BY metric_name
            """, (start_date.isoformat(),))

            metrics_summary = {}
            for row in cursor.fetchall():
                metrics_summary[row[0]] = {
                    "average": row[1],
                    "minimum": row[2],
                    "maximum": row[3],
                    "sample_count": row[4]
                }

        # 计算趋势
        trends = self._calculate_quality_trends(days)

        # 计算总体质量评分
        overall_score = self._calculate_overall_quality_score(executions)

        return {
            "period": f"Last {days} days",
            "total_executions": len(executions),
            "successful_executions": len([e for e in executions if e["status"] == "success"]),
            "metrics_summary": metrics_summary,
            "trends": trends,
            "overall_quality_score": overall_score,
            "recent_executions": executions[:10]  # 最近10次执行
        }

    def _calculate_quality_trends(self, days: int) -> Dict[str, QualityTrend]:
        """计算质量趋势"""
        start_date = datetime.now() - timedelta(days=days)
        trends = {}

        with sqlite3.connect(str(self.db_file)) as conn:
            cursor = conn.execute("""
                SELECT metric_name, timestamp, value
                FROM quality_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp
            """, (start_date.isoformat(),))

            data = {}
            for row in cursor.fetchall():
                metric_name = row[0]
                timestamp = datetime.fromisoformat(row[1])
                value = row[2]

                if metric_name not in data:
                    data[metric_name] = []
                data[metric_name].append((timestamp, value))

        for metric_name, time_series in data.items():
            if len(time_series) < 2:
                continue

            # 计算趋势
            values = [point[1] for point in time_series]
            if len(values) >= 3:
                # 简单线性趋势计算
                x = list(range(len(values)))
                slope = self._calculate_slope(x, values)

                if slope > 0.1:
                    trend = "improving"
                elif slope < -0.1:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
                slope = 0

            trends[metric_name] = QualityTrend(
                metric_name=metric_name,
                time_series=time_series,
                trend=trend,
                change_rate=slope
            )

        return trends

    def _calculate_slope(self, x: List[float], y: List[float]) -> float:
        """计算线性回归斜率"""
        if len(x) != len(y) or len(x) == 0:
            return 0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def _calculate_overall_quality_score(self, executions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算总体质量评分"""
        if not executions:
            return {"score": 0, "grade": "N/A", "components": {}}

        # 计算各组件评分
        validation_scores = [e["validation_rate"] for e in executions]
        success_rates = [(e["successful_tests"] / max(e["total_test_cases"], 1)) * 100 for e in executions]
        performance_scores = [max(0, 100 - (e["execution_time"] / 10)) for e in executions]  # 性能评分

        # 计算平均值
        avg_validation = statistics.mean(validation_scores) if validation_scores else 0
        avg_success = statistics.mean(success_rates) if success_rates else 0
        avg_performance = statistics.mean(performance_scores) if performance_scores else 0

        # 权重配置
        weights = {
            "validation": 0.4,
            "success": 0.4,
            "performance": 0.2
        }

        # 计算加权总分
        overall_score = (
            avg_validation * weights["validation"] +
            avg_success * weights["success"] +
            avg_performance * weights["performance"]
        )

        # 确定等级
        if overall_score >= 90:
            grade = "A+"
        elif overall_score >= 80:
            grade = "A"
        elif overall_score >= 70:
            grade = "B"
        elif overall_score >= 60:
            grade = "C"
        else:
            grade = "D"

        return {
            "score": round(overall_score, 1),
            "grade": grade,
            "components": {
                "validation": round(avg_validation, 1),
                "success": round(avg_success, 1),
                "performance": round(avg_performance, 1)
            },
            "weights": weights
        }

    def generate_quality_report(self, days: int = 7, format_type: str = "html") -> str:
        """
        生成质量报告

        Args:
            days: 分析天数
            format_type: 报告格式 ('html', 'markdown', 'json')

        Returns:
            报告文件路径
        """
        dashboard_data = self.get_quality_dashboard(days)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == "html":
            report_file = self.reports_dir / f"quality_report_{timestamp}.html"
            self._generate_html_report(dashboard_data, report_file)
        elif format_type == "markdown":
            report_file = self.reports_dir / f"quality_report_{timestamp}.md"
            self._generate_markdown_report(dashboard_data, report_file)
        else:
            report_file = self.reports_dir / f"quality_report_{timestamp}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)

        return str(report_file)

    def _generate_html_report(self, data: Dict[str, Any], output_file: Path):
        """生成HTML格式报告"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试质量报告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metric {{ margin: 10px 0; padding: 10px; border-left: 4px solid #007cba; background-color: #f9f9f9; }}
                .excellent {{ border-left-color: #28a745; }}
                .good {{ border-left-color: #17a2b8; }}
                .warning {{ border-left-color: #ffc107; }}
                .fail {{ border-left-color: #dc3545; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>测试质量报告</h1>
                <p>报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>分析周期: {data['period']}</p>
            </div>

            <h2>总体质量评分</h2>
            <div class="metric">
                <h3>总分: {data['overall_quality_score']['score']} ({data['overall_quality_score']['grade']})</h3>
                <ul>
                    <li>验证率: {data['overall_quality_score']['components']['validation']}%</li>
                    <li>成功率: {data['overall_quality_score']['components']['success']}%</li>
                    <li>性能: {data['overall_quality_score']['components']['performance']}</li>
                </ul>
            </div>

            <h2>执行统计</h2>
            <div class="metric">
                <p>总执行次数: {data['total_executions']}</p>
                <p>成功执行: {data['successful_executions']}</p>
                <p>成功率: {(data['successful_executions'] / max(data['total_executions'], 1) * 100):.1f}%</p>
            </div>

            <h2>质量指标</h2>
        """

        for metric_name, summary in data['metrics_summary'].items():
            html_content += f"""
            <div class="metric">
                <h3>{metric_name}</h3>
                <p>平均值: {summary['average']:.2f}</p>
                <p>最小值: {summary['minimum']:.2f}</p>
                <p>最大值: {summary['maximum']:.2f}</p>
                <p>样本数: {summary['sample_count']}</p>
            </div>
            """

        html_content += """
        </body>
        </html>
        """

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _generate_markdown_report(self, data: Dict[str, Any], output_file: Path):
        """生成Markdown格式报告"""
        md_content = f"""
# 测试质量报告

**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析周期**: {data['period']}

## 总体质量评分

**总分**: {data['overall_quality_score']['score']} ({data['overall_quality_score']['grade']})

- **验证率**: {data['overall_quality_score']['components']['validation']}%
- **成功率**: {data['overall_quality_score']['components']['success']}%
- **性能**: {data['overall_quality_score']['components']['performance']}

## 执行统计

- **总执行次数**: {data['total_executions']}
- **成功执行**: {data['successful_executions']}
- **成功率**: {(data['successful_executions'] / max(data['total_executions'], 1) * 100):.1f}%

## 质量指标

"""

        for metric_name, summary in data['metrics_summary'].items():
            md_content += f"""
### {metric_name}

- **平均值**: {summary['average']:.2f}
- **最小值**: {summary['minimum']:.2f}
- **最大值**: {summary['maximum']:.2f}
- **样本数**: {summary['sample_count']}

"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

    def cleanup_old_records(self, days_to_keep: int = 30):
        """清理旧记录"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with sqlite3.connect(str(self.db_file)) as conn:
            # 删除旧的执行记录
            cursor = conn.execute("""
                DELETE FROM test_executions
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))

            deleted_executions = cursor.rowcount

            # 删除旧的质量指标
            cursor = conn.execute("""
                DELETE FROM quality_metrics
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))

            deleted_metrics = cursor.rowcount

            # 删除旧的健康记录
            cursor = conn.execute("""
                DELETE FROM system_health
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))

            deleted_health = cursor.rowcount

        print(f"清理完成: 删除 {deleted_executions} 条执行记录, {deleted_metrics} 条质量指标, {deleted_health} 条健康记录")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='质量监控与报告系统')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--days', type=int, default=7, help='分析天数')
    parser.add_argument('--report-format', choices=['html', 'markdown', 'json'], default='html', help='报告格式')
    parser.add_argument('--dashboard', action='store_true', help='显示质量仪表板')
    parser.add_argument('--cleanup', type=int, help='清理多少天前的记录')
    parser.add_argument('--record-execution', help='记录测试执行结果（JSON文件路径）')

    args = parser.parse_args()

    # 创建质量监控系统
    qms = QualityMonitoringSystem(args.base_dir)

    if args.record_execution:
        # 记录测试执行结果
        with open(args.record_execution, 'r', encoding='utf-8') as f:
            execution_data = json.load(f)

        execution_id = qms.record_test_execution(execution_data)
        print(f"已记录测试执行结果: {execution_id}")

    elif args.cleanup:
        # 清理旧记录
        qms.cleanup_old_records(args.cleanup)

    elif args.dashboard:
        # 显示质量仪表板
        dashboard = qms.get_quality_dashboard(args.days)
        print(f"质量仪表板 ({dashboard['period']}):")
        print(f"总体评分: {dashboard['overall_quality_score']['score']} ({dashboard['overall_quality_score']['grade']})")
        print(f"总执行次数: {dashboard['total_executions']}")
        print(f"成功执行: {dashboard['successful_executions']}")

        print(f"\n质量指标:")
        for metric_name, summary in dashboard['metrics_summary'].items():
            print(f"  {metric_name}: 平均 {summary['average']:.2f}")

    else:
        # 生成质量报告
        report_file = qms.generate_quality_report(args.days, args.report_format)
        print(f"质量报告已生成: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())