#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
覆盖率监控体系 - 修复版
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import coverage

# 修复导入 - 使用相对导入或绝对导入
try:
    from src.core.logger import get_logger
except ImportError:
    # 测试环境中的回退方案
    import logging

    get_logger = logging.getLogger

logger = get_logger(__name__)


class CoverageStatus(Enum):
    """覆盖率状态枚举"""

    EXCELLENT = "excellent"  # >= 80%
    GOOD = "good"  # 60% - 80%
    NEEDS_IMPROVEMENT = "needs_improvement"  # 40% - 60%
    POOR = "poor"  # < 40%


@dataclass
class CoverageMetrics:
    """覆盖率指标数据类"""

    total_lines: int
    covered_lines: int
    coverage_percentage: float
    missing_lines: int
    excluded_lines: int
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoverageMetrics":
        """从字典创建实例"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class CoverageMonitor:
    """
    覆盖率监控器
    监控代码覆盖率变化趋势，生成覆盖率报告
    """

    def __init__(self, coverage_data_dir: str = "test_reports/coverage"):
        """
        初始化覆盖率监控器

        Args:
            coverage_data_dir: 覆盖率数据存储目录
        """
        self.coverage_data_dir = Path(coverage_data_dir)
        self.coverage_data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history: List[CoverageMetrics] = []
        self._load_history()

        logger.info(f"CoverageMonitor初始化完成，数据目录: {coverage_data_dir}")

    def _load_history(self) -> None:
        """加载历史覆盖率数据"""
        history_file = self.coverage_data_dir / "coverage_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metrics_history = [
                        CoverageMetrics.from_dict(item)
                        for item in data.get("history", [])
                    ]
                logger.info(f"加载了 {len(self.metrics_history)} 条历史覆盖率记录")
            except Exception as e:
                logger.error(f"加载历史覆盖率数据失败: {e}")
                self.metrics_history = []
        else:
            logger.info("未发现历史覆盖率数据")

    def collect_coverage(self, source_dir: str = "src") -> CoverageMetrics:
        """
        收集当前覆盖率数据

        Args:
            source_dir: 源代码目录

        Returns:
            CoverageMetrics: 覆盖率指标
        """
        try:
            cov = coverage.Coverage()
            cov.load()

            # 确保数据已收集
            if not cov.get_data():
                logger.warning("未找到覆盖率数据，尝试重新收集...")
                cov.combine()
                cov.save()

            # 分析覆盖率
            total_lines = 0
            covered_lines = 0
            missing_lines = 0
            excluded_lines = 0

            # 获取所有文件的覆盖率数据
            for filename in cov.get_data().measured_files():
                if source_dir in filename:
                    analysis = cov.analysis2(filename)
                    total_lines += (
                        len(analysis[1]) + len(analysis[2]) + len(analysis[3])
                    )
                    covered_lines += len(analysis[1])
                    missing_lines += len(analysis[2])
                    excluded_lines += len(analysis[3])

            # 计算覆盖率百分比
            coverage_percentage = 0.0
            if total_lines > 0:
                coverage_percentage = (covered_lines / total_lines) * 100

            metrics = CoverageMetrics(
                total_lines=total_lines,
                covered_lines=covered_lines,
                coverage_percentage=coverage_percentage,
                missing_lines=missing_lines,
                excluded_lines=excluded_lines,
                timestamp=datetime.now(),
            )

            logger.info(
                f"覆盖率收集完成: {coverage_percentage:.2f}% ({covered_lines}/{total_lines})"
            )
            return metrics

        except Exception as e:
            logger.error(f"收集覆盖率数据失败: {e}")
            # 返回默认值
            return CoverageMetrics(
                total_lines=0,
                covered_lines=0,
                coverage_percentage=0.0,
                missing_lines=0,
                excluded_lines=0,
                timestamp=datetime.now(),
            )

    def add_metrics(self, metrics: CoverageMetrics) -> None:
        """
        添加覆盖率指标到历史记录

        Args:
            metrics: 覆盖率指标
        """
        self.metrics_history.append(metrics)
        self._save_history()
        logger.info(f"添加覆盖率记录: {metrics.coverage_percentage:.2f}%")

    def _save_history(self) -> None:
        """保存历史覆盖率数据"""
        try:
            history_file = self.coverage_data_dir / "coverage_history.json"
            data = {
                "history": [item.to_dict() for item in self.metrics_history],
                "last_update": datetime.now().isoformat(),
            }

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存历史覆盖率数据失败: {e}")

    def get_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取覆盖率趋势数据

        Args:
            days: 天数

        Returns:
            List[Dict]: 趋势数据列表
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        trend_data = []
        for metrics in self.metrics_history:
            if metrics.timestamp >= cutoff_date:
                trend_data.append(
                    {
                        "date": metrics.timestamp.strftime("%Y-%m-%d"),
                        "coverage": round(metrics.coverage_percentage, 2),
                        "total_lines": metrics.total_lines,
                        "covered_lines": metrics.covered_lines,
                    }
                )

        logger.info(f"获取覆盖率趋势数据: {len(trend_data)} 条记录")
        return trend_data

    def get_status(self, target_coverage: float = 80.0) -> CoverageStatus:
        """
        获取当前覆盖率状态

        Args:
            target_coverage: 目标覆盖率

        Returns:
            CoverageStatus: 覆盖率状态
        """
        if not self.metrics_history:
            return CoverageStatus.NEEDS_IMPROVEMENT

        current_coverage = self.metrics_history[-1].coverage_percentage

        if current_coverage >= 80.0:
            return CoverageStatus.EXCELLENT
        elif current_coverage >= 60.0:
            return CoverageStatus.GOOD
        elif current_coverage >= 40.0:
            return CoverageStatus.NEEDS_IMPROVEMENT
        else:
            return CoverageStatus.POOR

    def generate_report(self) -> Dict[str, Any]:
        """
        生成覆盖率报告

        Returns:
            Dict: 覆盖率报告
        """
        if not self.metrics_history:
            return {"status": "no_data", "message": "No coverage data available"}

        current = self.metrics_history[-1]
        status = self.get_status()
        trend = self.get_trend()

        # 计算变化
        previous_coverage = current.coverage_percentage
        if len(self.metrics_history) > 1:
            previous = self.metrics_history[-2]
            previous_coverage = previous.coverage_percentage

        coverage_change = current.coverage_percentage - previous_coverage

        report = {
            "current_coverage": round(current.coverage_percentage, 2),
            "total_lines": current.total_lines,
            "covered_lines": current.covered_lines,
            "missing_lines": current.missing_lines,
            "status": status.value,
            "status_description": self._get_status_description(status),
            "trend": trend,
            "coverage_change": round(coverage_change, 2),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"生成覆盖率报告: {current.coverage_percentage:.2f}%")
        return report

    def _get_status_description(self, status: CoverageStatus) -> str:
        """获取状态描述"""
        descriptions = {
            CoverageStatus.EXCELLENT: "覆盖率优秀，继续保持",
            CoverageStatus.GOOD: "覆盖率良好，还有提升空间",
            CoverageStatus.NEEDS_IMPROVEMENT: "覆盖率需要改进",
            CoverageStatus.POOR: "覆盖率较差，需要立即改进",
        }
        return descriptions.get(status, "未知状态")

    def export_report(self, output_file: str = None) -> str:
        """
        导出覆盖率报告到文件

        Args:
            output_file: 输出文件路径

        Returns:
            str: 输出文件路径
        """
        if output_file is None:
            output_file = (
                self.coverage_data_dir
                / f"coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        try:
            report = self.generate_report()

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"覆盖率报告已导出到: {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"导出覆盖率报告失败: {e}")
            return ""

    def check_regression(self, threshold: float = 5.0) -> Tuple[bool, str]:
        """
        检查覆盖率是否下降

        Args:
            threshold: 下降阈值（百分比）

        Returns:
            Tuple[bool, str]: (是否下降, 消息)
        """
        if len(self.metrics_history) < 2:
            return False, "没有足够的历史数据"

        current = self.metrics_history[-1].coverage_percentage
        previous = self.metrics_history[-2].coverage_percentage

        drop = previous - current

        if drop >= threshold:
            message = f"覆盖率下降 {drop:.2f}% (从 {previous:.2f}% 降到 {current:.2f}%)"
            logger.warning(message)
            return True, message
        else:
            return False, f"覆盖率稳定 ({current:.2f}%)"


# 全局监控器实例
_global_coverage_monitor: Optional[CoverageMonitor] = None


def get_global_coverage_monitor() -> CoverageMonitor:
    """
    获取全局覆盖率监控器实例

    Returns:
        CoverageMonitor: 覆盖率监控器
    """
    global _global_coverage_monitor
    if _global_coverage_monitor is None:
        _global_coverage_monitor = CoverageMonitor()
    return _global_coverage_monitor


if __name__ == "__main__":
    # 测试覆盖率监控器
    monitor = CoverageMonitor()

    # 收集当前覆盖率
    try:
        metrics = monitor.collect_coverage()
        monitor.add_metrics(metrics)

        # 生成报告
        report = monitor.generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))

        # 导出报告
        output_file = monitor.export_report()
        print(f"\n报告已导出到: {output_file}")

    except Exception as e:
        print(f"Error: {e}")
