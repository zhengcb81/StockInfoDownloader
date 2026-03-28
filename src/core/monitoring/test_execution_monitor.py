#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Execution Monitoring System
Monitors test execution time, resource usage, and performance metrics
"""

import json
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import psutil

from src.core.logger import get_logger

logger = get_logger(__name__)


class TestStatus(Enum):
    """Test status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestExecutionRecord:
    """Test execution record"""

    test_id: str
    test_name: str
    file_path: str
    start_time: float
    end_time: Optional[float] = None
    status: TestStatus = TestStatus.PENDING
    execution_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None

    @property
    def is_completed(self) -> bool:
        """Check if test is completed"""
        return self.status in [
            TestStatus.PASSED,
            TestStatus.FAILED,
            TestStatus.SKIPPED,
            TestStatus.ERROR,
        ]

    def mark_started(self) -> None:
        """Mark test as started"""
        self.start_time = time.time()
        self.status = TestStatus.RUNNING

    def mark_completed(self, status: TestStatus, error_message: Optional[str] = None) -> None:
        """Mark test as completed"""
        self.end_time = time.time()
        self.status = status
        self.execution_time = self.end_time - self.start_time
        self.error_message = error_message

        # Record resource usage
        self._record_resource_usage()

    def _record_resource_usage(self) -> None:
        """Record resource usage"""
        try:
            process = psutil.Process()
            self.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            self.cpu_usage = process.cpu_percent()
        except Exception as e:
            logger.warning(f"Failed to record resource usage: {e}")


class TestExecutionMonitor:
    """Test execution monitor"""

    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.logger = get_logger("TestExecutionMonitor")
        self._records: Dict[str, TestExecutionRecord] = {}
        self._lock = threading.RLock()

        # Monitoring configuration
        self.config: Dict[str, Any] = {
            "max_execution_time": 60.0,  # Maximum execution time (seconds)
            "max_memory_usage": 500.0,  # Maximum memory usage (MB)
            "max_cpu_usage": 80.0,  # Maximum CPU usage (%)
            "enable_resource_monitoring": True,
        }

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "error_tests": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "slow_tests": [],
            "resource_intensive_tests": [],
        }

        self.logger.info("Test execution monitor initialized")

    def start_test(self, test_id: str, test_name: str, file_path: str) -> str:
        """Start monitoring a test"""
        with self._lock:
            record = TestExecutionRecord(
                test_id=test_id,
                test_name=test_name,
                file_path=file_path,
                start_time=time.time(),
            )
            record.mark_started()
            self._records[test_id] = record

            self.stats["total_tests"] += 1

            self.logger.debug(f"Started monitoring test: {test_name}")
            return test_id

    def end_test(
        self, test_id: str, status: TestStatus, error_message: Optional[str] = None
    ) -> None:
        """End monitoring a test"""
        with self._lock:
            if test_id not in self._records:
                self.logger.warning(f"Test record not found: {test_id}")
                return

            record = self._records[test_id]
            record.mark_completed(status, error_message)

            # Update statistics
            self._update_stats(record)

            # Check for performance issues
            self._check_performance_issues(record)

            self.logger.debug(f"Test completed: {record.test_name} - {status.value}")

    def _update_stats(self, record: TestExecutionRecord) -> None:
        """Update statistics"""
        if record.status == TestStatus.PASSED:
            self.stats["passed_tests"] += 1
        elif record.status == TestStatus.FAILED:
            self.stats["failed_tests"] += 1
        elif record.status == TestStatus.SKIPPED:
            self.stats["skipped_tests"] += 1
        elif record.status == TestStatus.ERROR:
            self.stats["error_tests"] += 1

        self.stats["total_execution_time"] += record.execution_time

        # Calculate average execution time
        completed_tests = (
            self.stats["passed_tests"]
            + self.stats["failed_tests"]
            + self.stats["error_tests"]
        )
        if completed_tests > 0:
            self.stats["average_execution_time"] = (
                self.stats["total_execution_time"] / completed_tests
            )

    def _check_performance_issues(self, record: TestExecutionRecord) -> None:
        """Check for performance issues"""
        # Check for long execution time
        max_execution_time = cast(float, self.config.get("max_execution_time", 60.0))
        if record.execution_time > max_execution_time:
            slow_tests = cast(List[Dict[str, Any]], self.stats.get("slow_tests"))
            slow_tests.append(
                {
                    "test_name": record.test_name,
                    "execution_time": record.execution_time,
                    "file_path": record.file_path,
                }
            )

        # Check for high resource usage
        enable_resource_monitoring = cast(bool, self.config.get("enable_resource_monitoring", True))
        if enable_resource_monitoring:
            max_memory_usage = cast(float, self.config.get("max_memory_usage", 500.0))
            if record.memory_usage > max_memory_usage:
                resource_tests = cast(List[Dict[str, Any]], self.stats.get("resource_intensive_tests"))
                resource_tests.append(
                    {
                        "test_name": record.test_name,
                        "memory_usage": record.memory_usage,
                        "file_path": record.file_path,
                    }
                )

            max_cpu_usage = cast(float, self.config.get("max_cpu_usage", 80.0))
            if record.cpu_usage > max_cpu_usage:
                resource_tests = cast(List[Dict[str, Any]], self.stats.get("resource_intensive_tests"))
                resource_tests.append(
                    {
                        "test_name": record.test_name,
                        "cpu_usage": record.cpu_usage,
                        "file_path": record.file_path,
                    }
                )

    def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get test status"""
        with self._lock:
            record = self._records.get(test_id)
            if record is None:
                return None

            return {
                "test_id": record.test_id,
                "test_name": record.test_name,
                "file_path": record.file_path,
                "status": record.status.value,
                "execution_time": record.execution_time,
                "memory_usage": record.memory_usage,
                "cpu_usage": record.cpu_usage,
                "start_time": record.start_time,
                "end_time": record.end_time,
                "error_message": record.error_message,
            }

    def get_all_test_status(self) -> List[Dict[str, Any]]:
        """Get all test statuses"""
        with self._lock:
            result = [self.get_test_status(test_id) for test_id in self._records.keys()]
            # Filter out None values
            return [r for r in result if r is not None]  # type: ignore[list-item]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        with self._lock:
            stats_copy = self.stats.copy()

            # Calculate success rate
            total_completed = (
                stats_copy["passed_tests"]
                + stats_copy["failed_tests"]
                + stats_copy["error_tests"]
            )
            if total_completed > 0:
                stats_copy["success_rate"] = (
                    stats_copy["passed_tests"] / total_completed
                )
            else:
                stats_copy["success_rate"] = 0.0

            return stats_copy

    def generate_report(self) -> Dict[str, Any]:
        """Generate monitoring report"""
        with self._lock:
            report = {
                "timestamp": datetime.now().isoformat(),
                "monitor_config": self.config,
                "test_statistics": self.get_stats(),
                "test_records": [asdict(record) for record in self._records.values()],
                "performance_issues": {
                    "slow_tests": self.stats["slow_tests"],
                    "resource_intensive_tests": self.stats["resource_intensive_tests"],
                },
                "summary": {
                    "total_tests_monitored": len(self._records),
                    "monitoring_duration": self._calculate_monitoring_duration(),
                    "overall_status": self._calculate_overall_status(),
                },
            }

            return report

    def _calculate_monitoring_duration(self) -> float:
        """Calculate monitoring duration"""
        if not self._records:
            return 0.0

        start_times = [record.start_time for record in self._records.values()]
        end_times = [
            record.end_time for record in self._records.values() if record.end_time
        ]

        if not end_times:
            return time.time() - min(start_times)

        return max(end_times) - min(start_times)

    def _calculate_overall_status(self) -> str:
        """Calculate overall status"""
        stats = self.get_stats()

        if stats["failed_tests"] > 0 or stats["error_tests"] > 0:
            return "FAILED"
        elif stats["passed_tests"] == stats["total_tests"]:
            return "PASSED"
        else:
            return "PARTIAL"

    def save_report(self, filename: Optional[str] = None) -> Optional[str]:
        """Save monitoring report"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_execution_report_{timestamp}.json"

        report_path = self.output_dir / filename

        try:
            report = self.generate_report()

            # Ensure all enum values are converted to strings
            def convert_enums(obj: Any) -> Any:
                if isinstance(obj, dict):
                    return {k: convert_enums(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_enums(item) for item in obj]
                elif isinstance(obj, Enum):
                    return obj.value
                else:
                    return obj

            report = convert_enums(report)

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Test execution report saved to: {report_path}")
            return str(report_path)

        except Exception as e:
            self.logger.error(f"Failed to save test execution report: {e}")
            return None

    def clear_records(self) -> None:
        """Clear all records"""
        with self._lock:
            self._records.clear()
            self.stats = {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "error_tests": 0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0,
                "slow_tests": [],
                "resource_intensive_tests": [],
            }


# Global monitor instance
_global_monitor: Optional[TestExecutionMonitor] = None


def get_global_monitor() -> TestExecutionMonitor:
    """Get the global monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = TestExecutionMonitor()
    return _global_monitor


def start_monitoring_test(test_name: str, file_path: str, test_id: Optional[str] = None) -> str:
    """Start monitoring a test (convenience function)"""
    monitor = get_global_monitor()
    test_id = f"{file_path}::{test_name}"
    return monitor.start_test(test_id, test_name, file_path)


def end_monitoring_test(
    test_id: str, status: TestStatus, error_message: Optional[str] = None
) -> None:
    """End monitoring a test (convenience function)"""
    monitor = get_global_monitor()
    monitor.end_test(test_id, status, error_message)


def save_monitoring_report() -> Optional[str]:
    """Save monitoring report (convenience function)"""
    monitor = get_global_monitor()
    return monitor.save_report()


def get_monitoring_stats() -> Dict[str, Any]:
    """Get monitoring statistics (convenience function)"""
    monitor = get_global_monitor()
    return monitor.get_stats()


# Pytest integration hooks
import pytest


@pytest.fixture(scope="function")
def test_monitor() -> Dict[str, Any]:
    """Pytest test monitoring fixture"""
    test_id = None

    def _start_monitoring(request: Any) -> None:
        nonlocal test_id
        test_name = request.node.name
        file_path = request.node.fspath.strpath
        test_id = start_monitoring_test(test_name, file_path)

    def _end_monitoring(
        request: Any, status: TestStatus, error_message: Optional[str] = None
    ) -> None:
        nonlocal test_id
        if test_id:
            end_monitoring_test(test_id, status, error_message)

    return {"start": _start_monitoring, "end": _end_monitoring}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: Any, nextitem: Any) -> Any:
    """Pytest test protocol hook"""
    # Get monitoring fixture
    monitor_fixture = None
    try:
        monitor_fixture = item.funcargs.get("test_monitor")
    except Exception:
        pass

    # Start monitoring
    if monitor_fixture:
        monitor_fixture["start"](item)

    # Execute test
    result = yield

    # End monitoring
    if monitor_fixture:
        # Determine status based on test result
        if hasattr(item, "_test_outcome") and item._test_outcome:
            outcome = item._test_outcome.outcome
            if outcome == "passed":
                status = TestStatus.PASSED
            elif outcome == "failed":
                status = TestStatus.FAILED
            elif outcome == "skipped":
                status = TestStatus.SKIPPED
            else:
                status = TestStatus.ERROR
        else:
            status = TestStatus.ERROR

        monitor_fixture["end"](item, status)


if __name__ == "__main__":
    # Example usage
    monitor = TestExecutionMonitor()

    # Simulate test execution
    test_id1 = monitor.start_test("test1", "test_example_1", "test_example.py")
    time.sleep(1)
    monitor.end_test(test_id1, TestStatus.PASSED)

    test_id2 = monitor.start_test("test2", "test_example_2", "test_example.py")
    time.sleep(2)
    monitor.end_test(test_id2, TestStatus.FAILED, "Assertion error")

    # Generate report
    report_path = monitor.save_report()
    print(f"Report saved to: {report_path}")

    # Print statistics
    stats = monitor.get_stats()
    print(f"Statistics: {json.dumps(stats, indent=2)}")
