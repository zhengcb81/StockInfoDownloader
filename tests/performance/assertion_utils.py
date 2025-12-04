#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能测试断言工具
为性能测试提供统一的断言接口
"""

import time
import psutil
import statistics
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class PerformanceThreshold:
    """性能阈值配置"""
    max_response_time: float  # 最大响应时间（秒）
    min_success_rate: float   # 最低成功率（百分比，0-100）
    max_memory_growth_mb: float  # 最大内存增长（MB）
    max_cpu_usage_percent: float  # 最大CPU使用率（百分比）
    max_concurrent_time: Optional[float] = None  # 最大并发执行时间（秒）
    min_throughput: Optional[float] = None  # 最小吞吐量（任务/秒）


class PerformanceAssertions:
    """性能测试断言类"""

    @staticmethod
    def assert_response_time(actual_time: float, max_time: float,
                           message: str = "") -> None:
        """
        断言响应时间不超过阈值

        Args:
            actual_time: 实际响应时间（秒）
            max_time: 最大允许时间（秒）
            message: 自定义错误消息
        """
        assert actual_time <= max_time, (
            f"响应时间超时: {actual_time:.2f}s > {max_time:.2f}s {message}"
        )

    @staticmethod
    def assert_success_rate(success_count: int, total_count: int,
                          min_rate: float, message: str = "") -> None:
        """
        断言成功率不低于阈值

        Args:
            success_count: 成功次数
            total_count: 总次数
            min_rate: 最低成功率（百分比，0-100）
            message: 自定义错误消息
        """
        if total_count == 0:
            raise ValueError("总次数不能为0")

        rate = (success_count / total_count) * 100
        assert rate >= min_rate, (
            f"成功率不足: {rate:.1f}% < {min_rate:.1f}% {message}"
        )

    @staticmethod
    def assert_memory_growth(initial_memory_mb: float, peak_memory_mb: float,
                           max_growth_mb: float, message: str = "") -> None:
        """
        断言内存增长不超过阈值

        Args:
            initial_memory_mb: 初始内存使用（MB）
            peak_memory_mb: 峰值内存使用（MB）
            max_growth_mb: 最大允许增长（MB）
            message: 自定义错误消息
        """
        growth = peak_memory_mb - initial_memory_mb
        assert growth <= max_growth_mb, (
            f"内存增长过大: {growth:.2f}MB > {max_growth_mb:.2f}MB {message}"
        )

    @staticmethod
    def assert_memory_leak(initial_memory_mb: float, final_memory_mb: float,
                         max_leak_mb: float, message: str = "") -> None:
        """
        断言内存泄漏不超过阈值

        Args:
            initial_memory_mb: 初始内存使用（MB）
            final_memory_mb: 最终内存使用（MB）
            max_leak_mb: 最大允许泄漏（MB）
            message: 自定义错误消息
        """
        leak = final_memory_mb - initial_memory_mb
        assert leak <= max_leak_mb, (
            f"内存泄漏: {leak:.2f}MB > {max_leak_mb:.2f}MB {message}"
        )

    @staticmethod
    def assert_cpu_usage(cpu_usage_percent: float, max_usage_percent: float,
                        message: str = "") -> None:
        """
        断言CPU使用率不超过阈值

        Args:
            cpu_usage_percent: 实际CPU使用率（百分比）
            max_usage_percent: 最大允许使用率（百分比）
            message: 自定义错误消息
        """
        assert cpu_usage_percent <= max_usage_percent, (
            f"CPU使用率过高: {cpu_usage_percent:.1f}% > {max_usage_percent:.1f}% {message}"
        )

    @staticmethod
    def assert_concurrent_time(actual_time: float, max_time: float,
                             message: str = "") -> None:
        """
        断言并发执行时间不超过阈值

        Args:
            actual_time: 实际执行时间（秒）
            max_time: 最大允许时间（秒）
            message: 自定义错误消息
        """
        assert actual_time <= max_time, (
            f"并发执行时间超时: {actual_time:.2f}s > {max_time:.2f}s {message}"
        )

    @staticmethod
    def assert_throughput(tasks_completed: int, total_time: float,
                        min_throughput: float, message: str = "") -> None:
        """
        断言吞吐量不低于阈值

        Args:
            tasks_completed: 完成的任务数
            total_time: 总时间（秒）
            min_throughput: 最小吞吐量（任务/秒）
            message: 自定义错误消息
        """
        if total_time == 0:
            raise ValueError("总时间不能为0")

        throughput = tasks_completed / total_time
        assert throughput >= min_throughput, (
            f"吞吐量不足: {throughput:.2f} tasks/s < {min_throughput:.2f} tasks/s {message}"
        )

    @staticmethod
    def assert_latency_percentile(latencies: List[float], percentile: float,
                                max_latency: float, message: str = "") -> None:
        """
        断言延迟百分位数不超过阈值

        Args:
            latencies: 延迟列表（秒）
            percentile: 百分位（0-100）
            max_latency: 最大允许延迟（秒）
            message: 自定义错误消息
        """
        if not latencies:
            raise ValueError("延迟列表不能为空")

        latencies_sorted = sorted(latencies)
        index = int(len(latencies_sorted) * percentile / 100)
        index = min(index, len(latencies_sorted) - 1)
        p_latency = latencies_sorted[index]

        assert p_latency <= max_latency, (
            f"{percentile}%延迟超时: {p_latency:.3f}s > {max_latency:.3f}s {message}"
        )

    @staticmethod
    def assert_cache_hit_rate(hit_count: int, total_requests: int,
                            min_hit_rate: float, message: str = "") -> None:
        """
        断言缓存命中率不低于阈值

        Args:
            hit_count: 命中次数
            total_requests: 总请求数
            min_hit_rate: 最低命中率（百分比，0-100）
            message: 自定义错误消息
        """
        if total_requests == 0:
            raise ValueError("总请求数不能为0")

        hit_rate = (hit_count / total_requests) * 100
        assert hit_rate >= min_hit_rate, (
            f"缓存命中率不足: {hit_rate:.1f}% < {min_hit_rate:.1f}% {message}"
        )

    @staticmethod
    def assert_against_thresholds(results: Dict[str, Any],
                                thresholds: PerformanceThreshold,
                                test_name: str = "") -> None:
        """
        根据阈值配置断言所有性能指标

        Args:
            results: 测试结果字典
            thresholds: 性能阈值配置
            test_name: 测试名称，用于错误消息
        """
        prefix = f"[{test_name}] " if test_name else ""

        # 检查响应时间
        if 'test_duration' in results:
            PerformanceAssertions.assert_response_time(
                results['test_duration'],
                thresholds.max_response_time,
                f"{prefix}总体测试时间"
            )

        # 检查成功率
        if 'successful_tests' in results and 'total_tests' in results:
            PerformanceAssertions.assert_success_rate(
                results['successful_tests'],
                results['total_tests'],
                thresholds.min_success_rate,
                f"{prefix}测试成功率"
            )

        # 检查内存增长
        if ('initial_memory_mb' in results and
            'peak_memory_mb' in results):
            PerformanceAssertions.assert_memory_growth(
                results['initial_memory_mb'],
                results['peak_memory_mb'],
                thresholds.max_memory_growth_mb,
                f"{prefix}内存增长"
            )

        # 检查CPU使用率
        if 'cpu_usage_percent' in results:
            PerformanceAssertions.assert_cpu_usage(
                results['cpu_usage_percent'],
                thresholds.max_cpu_usage_percent,
                f"{prefix}CPU使用率"
            )

        # 检查并发时间
        if ('concurrent_time_seconds' in results and
            thresholds.max_concurrent_time is not None):
            PerformanceAssertions.assert_concurrent_time(
                results['concurrent_time_seconds'],
                thresholds.max_concurrent_time,
                f"{prefix}并发执行时间"
            )

        # 检查吞吐量
        if ('tasks_completed' in results and 'total_time' in results and
            thresholds.min_throughput is not None):
            PerformanceAssertions.assert_throughput(
                results['tasks_completed'],
                results['total_time'],
                thresholds.min_throughput,
                f"{prefix}吞吐量"
            )


def create_default_thresholds() -> PerformanceThreshold:
    """
    创建默认性能阈值配置

    Returns:
        PerformanceThreshold: 默认阈值配置
    """
    return PerformanceThreshold(
        max_response_time=30.0,      # 30秒
        min_success_rate=95.0,       # 95%
        max_memory_growth_mb=100.0,  # 100MB
        max_cpu_usage_percent=80.0,  # 80%
        max_concurrent_time=10.0,    # 10秒
        min_throughput=10.0          # 10 tasks/s
    )


def create_strict_thresholds() -> PerformanceThreshold:
    """
    创建严格性能阈值配置

    Returns:
        PerformanceThreshold: 严格阈值配置
    """
    return PerformanceThreshold(
        max_response_time=10.0,      # 10秒
        min_success_rate=99.0,       # 99%
        max_memory_growth_mb=50.0,   # 50MB
        max_cpu_usage_percent=70.0,  # 70%
        max_concurrent_time=5.0,     # 5秒
        min_throughput=20.0          # 20 tasks/s
    )


def create_lenient_thresholds() -> PerformanceThreshold:
    """
    创建宽松性能阈值配置

    Returns:
        PerformanceThreshold: 宽松阈值配置
    """
    return PerformanceThreshold(
        max_response_time=60.0,      # 60秒
        min_success_rate=90.0,       # 90%
        max_memory_growth_mb=200.0,  # 200MB
        max_cpu_usage_percent=90.0,  # 90%
        max_concurrent_time=20.0,    # 20秒
        min_throughput=5.0           # 5 tasks/s
    )


# 提供全局断言实例
assertions = PerformanceAssertions()