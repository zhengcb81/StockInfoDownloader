"""
性能监控模块
提供性能监控、统计和报告功能
"""

import functools
import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标数据类"""

    operation: str
    duration: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.operation_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
                "avg_time": 0,
            }
        )

    def record_metric(self, operation: str, duration: float, **metadata):
        """记录性能指标"""
        metric = PerformanceMetric(operation, duration, **metadata)
        self.metrics.append(metric)

        # 更新统计信息
        stats = self.operation_stats[operation]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        stats["avg_time"] = stats["total_time"] / stats["count"]

        logger.debug(f"性能指标: {operation} 耗时 {duration:.3f}秒")

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """获取性能统计"""
        if operation:
            return dict(self.operation_stats[operation])
        return {op: dict(stats) for op, stats in self.operation_stats.items()}

    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        total_operations = sum(
            stats["count"] for stats in self.operation_stats.values()
        )
        total_time = sum(stats["total_time"] for stats in self.operation_stats.values())

        return {
            "total_operations": total_operations,
            "total_time": total_time,
            "operations_count": len(self.operation_stats),
            "slowest_operation": max(
                self.operation_stats.items(),
                key=lambda x: x[1]["avg_time"],
                default=("N/A", {"avg_time": 0}),
            )[0],
            "fastest_operation": min(
                self.operation_stats.items(),
                key=lambda x: x[1]["avg_time"],
                default=("N/A", {"avg_time": float("inf")}),
            )[0],
        }

    def clear(self):
        """清除所有指标"""
        self.metrics.clear()
        self.operation_stats.clear()

    def log_report(self):
        """输出性能报告"""
        summary = self.get_summary()
        logger.info("=== 性能报告 ===")
        logger.info(f"总操作数: {summary['total_operations']}")
        logger.info(f"总耗时: {summary['total_time']:.3f}秒")
        logger.info(
            f"平均耗时: {summary['total_time'] / max(summary['total_operations'], 1):.3f}秒"
        )
        logger.info(f"最慢操作: {summary['slowest_operation']}")
        logger.info(f"最快操作: {summary['fastest_operation']}")

        logger.info("\n=== 各操作详情 ===")
        for operation, stats in sorted(
            self.operation_stats.items(), key=lambda x: x[1]["avg_time"], reverse=True
        ):
            logger.info(
                f"{operation}: 平均 {stats['avg_time']:.3f}秒 "
                f"(最小 {stats['min_time']:.3f}秒, "
                f"最大 {stats['max_time']:.3f}秒, "
                f"执行 {stats['count']}次)"
            )


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: Optional[str] = None):
    """性能监控装饰器"""

    def decorator(func):
        name = operation_name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                performance_monitor.record_metric(name, duration)

        return wrapper

    return decorator


@contextmanager
def monitor_operation(operation: str, **metadata):
    """上下文管理器形式的性能监控"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        performance_monitor.record_metric(operation, duration, **metadata)


def log_performance_stats():
    """记录性能统计的便捷函数"""
    performance_monitor.log_report()


def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计的便捷函数"""
    return performance_monitor.get_stats()


def clear_performance_stats():
    """清除性能统计的便捷函数"""
    performance_monitor.clear()
