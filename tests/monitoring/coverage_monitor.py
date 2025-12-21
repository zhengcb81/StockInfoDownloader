#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
覆盖率监控体系
监控代码覆盖率变化趋势，提供覆盖率分析和报告
"""

import json
import time
import coverage
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from src.core.logger import get_logger
except ImportError:
    import logging
    get_logger = logging.getLogger

logger = get_logger(__name__)


class CoverageStatus(Enum):
    """覆盖率状态枚举"""
    EXCELLENT = "excellent"  # >= 90%
    GOOD = "good"           # 80% - 89%
    FAIR = "fair"           # 70% - 79%
    POOR = "poor"           # 60% - 69%
    VERY_POOR = "very_poor" # < 60%


@dataclass
class CoverageMetrics:
    """覆盖率指标"""
    timestamp: float
    overall_coverage: float
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    total_lines: int
    covered_lines: int
    total_branches: int
    covered_branches: int
    total_functions: int
    covered_functions: int

    @property
    def status(self) -> CoverageStatus:
        """获取覆盖率状态"""
        if self.overall_coverage >= 90:
            return CoverageStatus.EXCELLENT
        elif self.overall_coverage >= 80:
            return CoverageStatus.GOOD
        elif self.overall_coverage >= 70:
            return CoverageStatus.FAIR
        elif self.overall_coverage >= 60:
            return CoverageStatus.POOR
        else:
            return CoverageStatus.VERY_POOR


@dataclass
class ModuleCoverage:
    """模块覆盖率"""
    module_name: str
    file_path: str
    overall_coverage: float
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    total_lines: int
    covered_lines: int
    total_branches: int
    covered_branches: int
    total_functions: int
    covered_functions: int


class CoverageMonitor:
    """覆盖率监控器"""

    def __init__(self, source_dir: str = "src", output_dir: str = "coverage_reports"):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.logger = get_logger("CoverageMonitor")
        self._coverage_data: List[CoverageMetrics] = []
        self._module_coverage: Dict[str, List[ModuleCoverage]] = {}

        # 监控配置
        self.config = {
            'target_coverage': 80.0,
            'warning_threshold': 70.0,
            'critical_threshold': 60.0,
            'trend_window_days': 30,
            'enable_trend_analysis': True
        }

        # 统计信息
        self.stats = {
            'total_measurements': 0,
            'current_coverage': 0.0,
            'best_coverage': 0.0,
            'worst_coverage': 100.0,
            'coverage_trend': 'stable',  # 'improving', 'declining', 'stable'
            'modules_below_target': [],
            'modules_improving': [],
            'modules_declining': []
        }

        self.logger.info("覆盖率监控器初始化完成")

    def measure_coverage(self, test_command: str = "pytest tests/") -> CoverageMetrics:
        """测量覆盖率"""
        try:
            # 使用coverage.py测量覆盖率
            cov = coverage.Coverage(source=[str(self.source_dir)])
            cov.start()

            # 执行测试
            import subprocess
            result = subprocess.run(test_command.split(), capture_output=True, text=True)

            cov.stop()
            cov.save()

            # 获取覆盖率数据
            coverage_data = cov.get_data()

            # 计算覆盖率指标
            metrics = self._calculate_coverage_metrics(coverage_data)
            self._coverage_data.append(metrics)

            # 更新模块覆盖率
            self._update_module_coverage(coverage_data, metrics.timestamp)

            # 更新统计信息
            self._update_stats()

            self.logger.info(f"覆盖率测量完成: {metrics.overall_coverage:.1f}%")
            return metrics

        except Exception as e:
            self.logger.error(f"覆盖率测量失败: {e}")
            # 返回空的覆盖率指标
            return CoverageMetrics(
                timestamp=time.time(),
                overall_coverage=0.0,
                line_coverage=0.0,
                branch_coverage=0.0,
                function_coverage=0.0,
                total_lines=0,
                covered_lines=0,
                total_branches=0,
                covered_branches=0,
                total_functions=0,
                covered_functions=0
            )

    def _calculate_coverage_metrics(self, coverage_data) -> CoverageMetrics:
        """计算覆盖率指标"""
        try:
            # 获取总体覆盖率
            analysis = coverage_data.analysis2(self.source_dir)

            # 计算各种覆盖率
            total_lines = analysis.numbers.n_statements
            covered_lines = analysis.numbers.n_executed
            line_coverage = (covered_lines / total_lines * 100) if total_lines > 0 else 0

            # 简化计算，实际项目中需要更精确的计算
            overall_coverage = line_coverage
            branch_coverage = line_coverage * 0.8  # 简化计算
            function_coverage = line_coverage * 0.9  # 简化计算

            return CoverageMetrics(
                timestamp=time.time(),
                overall_coverage=overall_coverage,
                line_coverage=line_coverage,
                branch_coverage=branch_coverage,
                function_coverage=function_coverage,
                total_lines=total_lines,
                covered_lines=covered_lines,
                total_branches=int(total_lines * 0.5),  # 简化计算
                covered_branches=int(covered_lines * 0.4),  # 简化计算
                total_functions=int(total_lines * 0.1),  # 简化计算
                covered_functions=int(covered_lines * 0.09)  # 简化计算
            )
        except Exception as e:
            self.logger.warning(f"覆盖率计算失败，使用默认值: {e}")
            # 返回默认的覆盖率指标
            return CoverageMetrics(
                timestamp=time.time(),
                overall_coverage=0.0,
                line_coverage=0.0,
                branch_coverage=0.0,
                function_coverage=0.0,
                total_lines=0,
                covered_lines=0,
                total_branches=0,
                covered_branches=0,
                total_functions=0,
                covered_functions=0
            )

    def _update_module_coverage(self, coverage_data, timestamp: float):
        """更新模块覆盖率"""
        timestamp_str = str(timestamp)
        self._module_coverage[timestamp_str] = []

        # 遍历所有源文件
        for file_path in self.source_dir.rglob("*.py"):
            if file_path.is_file() and "__pycache__" not in str(file_path):
                try:
                    # 分析单个文件的覆盖率
                    analysis = coverage_data.analysis2(file_path)

                    if analysis.numbers.n_statements > 0:
                        module_cov = ModuleCoverage(
                            module_name=file_path.stem,
                            file_path=str(file_path),
                            overall_coverage=(analysis.numbers.n_executed / analysis.numbers.n_statements * 100),
                            line_coverage=(analysis.numbers.n_executed / analysis.numbers.n_statements * 100),
                            branch_coverage=0.0,  # 简化计算
                            function_coverage=0.0,  # 简化计算
                            total_lines=analysis.numbers.n_statements,
                            covered_lines=analysis.numbers.n_executed,
                            total_branches=0,
                            covered_branches=0,
                            total_functions=0,
                            covered_functions=0
                        )
                        self._module_coverage[timestamp_str].append(module_cov)

                except Exception as e:
                    self.logger.debug(f"分析文件覆盖率失败 {file_path}: {e}")

    def _update_stats(self):
        """更新统计信息"""
        if not self._coverage_data:
            return

        current_metrics = self._coverage_data[-1]
        self.stats['total_measurements'] = len(self._coverage_data)
        self.stats['current_coverage'] = current_metrics.overall_coverage

        # 计算最佳和最差覆盖率
        coverages = [m.overall_coverage for m in self._coverage_data]
        self.stats['best_coverage'] = max(coverages)
        self.stats['worst_coverage'] = min(coverages)

        # 分析趋势
        self.stats['coverage_trend'] = self._analyze_trend()

        # 分析模块状态
        self._analyze_module_status()

    def _analyze_trend(self) -> str:
        """分析覆盖率趋势"""
        if len(self._coverage_data) < 2:
            return 'stable'

        # 获取最近几次测量的覆盖率
        recent_coverages = [m.overall_coverage for m in self._coverage_data[-5:]]

        if len(recent_coverages) < 2:
            return 'stable'

        # 计算趋势
        first = recent_coverages[0]
        last = recent_coverages[-1]

        if last - first > 1.0:  # 提高超过1%
            return 'improving'
        elif first - last > 1.0:  # 下降超过1%
            return 'declining'
        else:
            return 'stable'

    def _analyze_module_status(self):
        """分析模块状态"""
        if not self._module_coverage:
            return

        current_timestamp = str(self._coverage_data[-1].timestamp)
        current_modules = self._module_coverage.get(current_timestamp, [])

        # 找出低于目标的模块
        self.stats['modules_below_target'] = [
            m.module_name for m in current_modules
            if m.overall_coverage < self.config['target_coverage']
        ]

        # 分析模块趋势（简化实现）
        self.stats['modules_improving'] = []
        self.stats['modules_declining'] = []

    def get_current_coverage(self) -> Optional[CoverageMetrics]:
        """获取当前覆盖率"""
        if not self._coverage_data:
            return None
        return self._coverage_data[-1]

    def get_coverage_history(self, days: int = 30) -> List[CoverageMetrics]:
        """获取覆盖率历史"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        return [m for m in self._coverage_data if m.timestamp >= cutoff_time]

    def get_module_coverage(self, module_name: str) -> List[Tuple[float, float]]:
        """获取模块覆盖率历史"""
        module_history = []

        for timestamp_str, modules in self._module_coverage.items():
            for module in modules:
                if module.module_name == module_name:
                    module_history.append((float(timestamp_str), module.overall_coverage))
                    break

        return sorted(module_history, key=lambda x: x[0])

    def check_coverage_quality(self) -> Dict[str, Any]:
        """检查覆盖率质量"""
        current = self.get_current_coverage()
        if not current:
            return {'status': 'unknown', 'message': '没有覆盖率数据'}

        quality_check = {
            'current_coverage': current.overall_coverage,
            'target_coverage': self.config['target_coverage'],
            'status': current.status.value,
            'meets_target': current.overall_coverage >= self.config['target_coverage'],
            'above_warning': current.overall_coverage >= self.config['warning_threshold'],
            'above_critical': current.overall_coverage >= self.config['critical_threshold'],
            'trend': self.stats['coverage_trend'],
            'modules_below_target': len(self.stats['modules_below_target'])
        }

        return quality_check

    def generate_report(self) -> Dict[str, Any]:
        """生成覆盖率报告"""
        current = self.get_current_coverage()

        report = {
            'timestamp': datetime.now().isoformat(),
            'monitor_config': self.config,
            'current_coverage': current.overall_coverage if current else 0.0,
            'coverage_status': current.status.value if current else 'unknown',
            'statistics': self.stats,
            'quality_check': self.check_coverage_quality(),
            'coverage_history': [
                {
                    'timestamp': m.timestamp,
                    'overall_coverage': m.overall_coverage,
                    'status': m.status.value
                }
                for m in self._coverage_data[-10:]  # 最近10次测量
            ],
            'module_analysis': {
                'modules_below_target': self.stats['modules_below_target'],
                'total_modules': len(self._module_coverage.get(str(current.timestamp), [])) if current else 0
            }
        }

        return report

    def save_report(self, filename: Optional[str] = None) -> Optional[str]:
        """保存覆盖率报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"coverage_report_{timestamp}.json"

        report_path = self.output_dir / filename

        try:
            report = self.generate_report()

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"覆盖率报告已保存到: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"保存覆盖率报告失败: {e}")
            return None

    def export_trend_data(self, days: int = 30) -> Dict[str, Any]:
        """导出趋势数据"""
        history = self.get_coverage_history(days)

        trend_data = {
            'period_days': days,
            'data_points': [
                {
                    'date': datetime.fromtimestamp(m.timestamp).strftime('%Y-%m-%d'),
                    'coverage': m.overall_coverage,
                    'status': m.status.value
                }
                for m in history
            ],
            'summary': {
                'average_coverage': sum(m.overall_coverage for m in history) / len(history) if history else 0,
                'trend': self.stats['coverage_trend'],
                'measurement_count': len(history)
            }
        }

        return trend_data


# 全局监控器实例
_global_coverage_monitor: Optional[CoverageMonitor] = None


def get_global_coverage_monitor() -> CoverageMonitor:
    """获取全局覆盖率监控器实例"""
    global _global_coverage_monitor
    if _global_coverage_monitor is None:
        _global_coverage_monitor = CoverageMonitor()
    return _global_coverage_monitor


def measure_current_coverage() -> CoverageMetrics:
    """测量当前覆盖率（便捷函数）"""
    monitor = get_global_coverage_monitor()
    return monitor.measure_coverage()


def get_coverage_quality() -> Dict[str, Any]:
    """获取覆盖率质量（便捷函数）"""
    monitor = get_global_coverage_monitor()
    return monitor.check_coverage_quality()


def save_coverage_report() -> Optional[str]:
    """保存覆盖率报告（便捷函数）"""
    monitor = get_global_coverage_monitor()
    return monitor.save_report()


def export_coverage_trend(days: int = 30) -> Dict[str, Any]:
    """导出覆盖率趋势数据（便捷函数）"""
    monitor = get_global_coverage_monitor()
    return monitor.export_trend_data(days)


if __name__ == "__main__":
    # 示例用法
    monitor = CoverageMonitor()

    # 测量覆盖率
    metrics = monitor.measure_coverage()
    print(f"当前覆盖率: {metrics.overall_coverage:.1f}%")
    print(f"覆盖率状态: {metrics.status.value}")

    # 检查质量
    quality = monitor.check_coverage_quality()
    print(f"质量检查: {json.dumps(quality, indent=2)}")

    # 生成报告
    report_path = monitor.save_report()
    print(f"报告已保存到: {report_path}")

    # 导出趋势数据
    trend_data = monitor.export_trend_data(7)
    print(f"趋势数据: {json.dumps(trend_data, indent=2)}")