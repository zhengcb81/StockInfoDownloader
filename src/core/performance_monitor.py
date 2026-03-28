"""
Performance monitoring module
Provides performance monitoring, statistics, and reporting functionality
"""

import functools
import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data class"""

    operation: str
    duration: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Performance monitor"""

    def __init__(self) -> None:
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

    def record_metric(self, operation: str, duration: float, **metadata: Any) -> None:
        """Record a performance metric"""
        metric = PerformanceMetric(operation, duration, **metadata)
        self.metrics.append(metric)

        # Update statistics
        stats = self.operation_stats[operation]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        stats["avg_time"] = stats["total_time"] / stats["count"]

        logger.debug(f"Performance metric: {operation} took {duration:.3f}s")

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if operation:
            return dict(self.operation_stats[operation])
        return {op: dict(stats) for op, stats in self.operation_stats.items()}

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
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

    def clear(self) -> None:
        """Clear all metrics"""
        self.metrics.clear()
        self.operation_stats.clear()

    def log_report(self) -> None:
        """Output performance report"""
        summary = self.get_summary()
        logger.info("=== Performance Report ===")
        logger.info(f"Total operations: {summary['total_operations']}")
        logger.info(f"Total time: {summary['total_time']:.3f}s")
        logger.info(
            f"Average time: {summary['total_time'] / max(summary['total_operations'], 1):.3f}s"
        )
        logger.info(f"Slowest operation: {summary['slowest_operation']}")
        logger.info(f"Fastest operation: {summary['fastest_operation']}")

        logger.info("\n=== Operation Details ===")
        for operation, stats in sorted(
            self.operation_stats.items(), key=lambda x: x[1]["avg_time"], reverse=True
        ):
            logger.info(
                f"{operation}: avg {stats['avg_time']:.3f}s "
                f"(min {stats['min_time']:.3f}s, "
                f"max {stats['max_time']:.3f}s, "
                f"count {stats['count']})"
            )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: Optional[str] = None) -> Callable[[F], F]:
    """Performance monitoring decorator"""

    def decorator(func: F) -> F:
        name = operation_name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                performance_monitor.record_metric(name, duration)

        return wrapper  # type: ignore

    return decorator


@contextmanager
def monitor_operation(operation: str, **metadata: Any) -> Iterator[None]:
    """Performance monitoring as a context manager"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        performance_monitor.record_metric(operation, duration, **metadata)


def log_performance_stats() -> None:
    """Convenience function to log performance statistics"""
    performance_monitor.log_report()


def get_performance_stats() -> Dict[str, Any]:
    """Convenience function to get performance statistics"""
    return performance_monitor.get_stats()


def clear_performance_stats() -> None:
    """Convenience function to clear performance statistics"""
    performance_monitor.clear()
