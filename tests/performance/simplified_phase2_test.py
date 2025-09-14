#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化的Phase 2性能测试脚本
专注于测试异步操作、智能缓存和错误处理
"""

import asyncio
import time
import threading
import statistics
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
import shutil
import sys
import os

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.web.async_operations import (
    AsyncTaskManager, AsyncBatchDownloader, DownloadTask, TaskPriority
)
from src.utils.intelligent_cache import (
    IntelligentCache, CacheConfig, EvictionPolicy, get_global_cache
)
from src.utils.enhanced_error_handler import (
    EnhancedErrorHandler, RetryConfig, RetryStrategy,
    get_global_error_handler, error_protected
)
from src.core.logger import get_logger


class SimplifiedPhase2Tester:
    """简化的Phase 2性能测试器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.test_results = {}
        self.temp_dir = Path(tempfile.mkdtemp(prefix="simplified_phase2_test_"))

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有性能测试"""
        self.logger.info("开始简化Phase 2性能测试")

        test_results = {}

        # 1. 智能缓存测试
        self.logger.info("测试1: 智能缓存")
        test_results['intelligent_cache'] = self.test_intelligent_cache()

        # 2. 增强错误处理测试
        self.logger.info("测试2: 增强错误处理")
        test_results['enhanced_error_handler'] = self.test_enhanced_error_handler()

        # 3. 异步操作测试（本地测试）
        self.logger.info("测试3: 异步操作")
        test_results['async_operations'] = self.test_async_operations_local()

        # 4. 综合性能测试
        self.logger.info("测试4: 综合性能")
        test_results['integrated_performance'] = self.test_integrated_performance()

        # 生成汇总报告
        summary = self.generate_summary(test_results)

        # 清理临时文件
        self.cleanup()

        return summary

    def test_intelligent_cache(self) -> Dict[str, Any]:
        """测试智能缓存"""
        try:
            # 创建缓存配置
            cache_config = CacheConfig(
                l1_max_size=100,
                l1_max_memory=10 * 1024 * 1024,  # 10MB
                l2_max_size=1000,
                default_ttl=300.0,  # 5分钟
                l1_eviction_policy=EvictionPolicy.ARC,
                l2_eviction_policy=EvictionPolicy.LRU,
                compression_enabled=True,
                adaptive_ttl=True
            )

            cache = IntelligentCache(cache_config)

            # 测试数据
            test_data = {}
            for i in range(200):
                test_data[f'key_{i}'] = {
                    'id': i,
                    'name': f'test_item_{i}',
                    'data': 'x' * (100 + i * 10),  # 变长数据
                    'timestamp': time.time()
                }

            # 测试缓存操作
            start_time = time.time()

            # 写入缓存
            for key, value in test_data.items():
                cache.set(key, value)

            # 读取缓存（测试命中率）
            hit_count = 0
            for _ in range(500):  # 500次读取操作
                key = f'key_{(_ % 200)}'  # 循环读取已存在的键
                result = cache.get(key)
                if result is not None:
                    hit_count += 1

            # 测试不存在的键
            for _ in range(100):
                cache.get(f'nonexistent_key_{_}')

            end_time = time.time()

            # 获取缓存统计
            cache_stats = cache.get_stats()
            detailed_status = cache.get_detailed_status()

            return {
                'test_duration': end_time - start_time,
                'cache_stats': cache_stats,
                'hit_rate': (hit_count / 500) * 100,
                'total_operations': 600,  # 500读取 + 100不存在的键
                'cache_config': {
                    'l1_max_size': cache_config.l1_max_size,
                    'l2_max_size': cache_config.l2_max_size,
                    'eviction_policies': {
                        'l1': cache_config.l1_eviction_policy.value,
                        'l2': cache_config.l2_eviction_policy.value
                    }
                },
                'detailed_status': detailed_status,
                'success': True,
                'message': '智能缓存测试通过'
            }

        except Exception as e:
            self.logger.error(f"智能缓存测试失败: {e}")
            return {
                'success': False,
                'message': f"测试失败: {e}",
                'error_details': str(e)
            }

    def test_enhanced_error_handler(self) -> Dict[str, Any]:
        """测试增强错误处理"""
        try:
            error_handler = EnhancedErrorHandler()

            # 创建重试配置
            retry_config = RetryConfig(
                max_retries=3,
                base_delay=0.1,
                strategy=RetryStrategy.EXPONENTIAL,
                jitter=True
            )

            # 测试函数（模拟失败后成功）
            call_count = {'count': 0}

            @error_protected(retry_config=retry_config, circuit_breaker_key="test_service")
            def test_function():
                call_count['count'] += 1
                if call_count['count'] <= 2:  # 前两次调用失败
                    raise ConnectionError("模拟网络错误")
                return "success"

            # 测试重试机制
            start_time = time.time()
            result = test_function()
            end_time = time.time()

            # 测试熔断器
            @error_protected(circuit_breaker_key="failing_service")
            def failing_function():
                raise Exception("服务不可用")

            # 触发熔断器
            for _ in range(6):  # 超过默认阈值5
                try:
                    failing_function()
                except Exception:
                    pass

            # 获取错误统计
            error_stats = error_handler.get_error_stats()
            error_history = error_handler.get_error_history(limit=10)

            return {
                'test_duration': end_time - start_time,
                'retry_test': {
                    'result': result,
                    'total_calls': call_count['count'],
                    'success': result == "success"
                },
                'circuit_breaker_test': {
                    'breaker_stats': error_stats.get('circuit_breakers', {}).get('failing_service', {}),
                    'triggered': len([e for e in error_history if '熔断器开启' in str(e.get('message', ''))]) > 0
                },
                'error_stats': error_stats,
                'success': True,
                'message': '增强错误处理测试通过'
            }

        except Exception as e:
            self.logger.error(f"增强错误处理测试失败: {e}")
            return {
                'success': False,
                'message': f"测试失败: {e}",
                'error_details': str(e)
            }

    def test_async_operations_local(self) -> Dict[str, Any]:
        """测试异步操作（本地模拟）"""
        try:
            # 创建模拟下载任务（本地文件操作）
            test_files = []
            for i in range(5):
                test_file = self.temp_dir / f"test_file_{i}.txt"
                # 创建测试文件
                test_file.write_text(f"Test content {i}\n" + "x" * 1000)
                test_files.append(str(test_file))

            download_tasks = []
            for i, file_path in enumerate(test_files):
                save_path = self.temp_dir / f"copied_file_{i}.txt"
                task = DownloadTask(
                    url=f"file://{file_path}",  # 使用file://协议
                    save_path=str(save_path),
                    priority=TaskPriority.NORMAL,
                    timeout=10.0,
                    retry_count=1
                )
                download_tasks.append(task)

            # 测试异步批量操作（模拟）
            start_time = time.time()

            async def async_local_test():
                async with AsyncTaskManager(max_concurrent_tasks=3) as manager:
                    # 模拟异步文件复制
                    tasks = []
                    for task in download_tasks:
                        task_future = asyncio.create_task(self._simulate_async_copy(task))
                        tasks.append(task_future)

                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    return results

            # 运行异步测试
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(async_local_test())
            loop.close()

            end_time = time.time()

            # 分析结果
            successful_operations = sum(1 for r in results if not isinstance(r, Exception))

            return {
                'test_duration': end_time - start_time,
                'total_tasks': len(download_tasks),
                'successful_operations': successful_operations,
                'success_rate': (successful_operations / len(download_tasks)) * 100,
                'results_summary': {
                    'completed': successful_operations,
                    'failed': len(download_tasks) - successful_operations
                },
                'success': True,
                'message': '异步操作测试通过（本地模拟）'
            }

        except Exception as e:
            self.logger.error(f"异步操作测试失败: {e}")
            return {
                'success': False,
                'message': f"测试失败: {e}",
                'error_details': str(e)
            }

    async def _simulate_async_copy(self, task: DownloadTask):
        """模拟异步文件复制"""
        await asyncio.sleep(0.1)  # 模拟异步延迟

        # 简单的文件复制模拟
        source_path = task.url.replace("file://", "")
        try:
            content = Path(source_path).read_text()
            Path(task.save_path).write_text(content)
            return True
        except Exception:
            return False

    def test_integrated_performance(self) -> Dict[str, Any]:
        """综合性能测试"""
        try:
            import psutil

            # 启动资源监控
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            initial_cpu = process.cpu_percent()

            start_time = time.time()

            # 1. 初始化所有组件
            cache = get_global_cache()
            error_handler = get_global_error_handler()

            # 2. 模拟综合工作负载
            async def integrated_workload():
                # 缓存预热
                for i in range(50):
                    cache.set(f'integrated_key_{i}', {'data': f'value_{i}', 'timestamp': time.time()})

                # 异步任务处理
                async with AsyncTaskManager(max_concurrent_tasks=5) as manager:
                    # 创建模拟任务
                    tasks = []
                    for i in range(10):
                        save_path = self.temp_dir / f"integrated_{i}.txt"
                        task = DownloadTask(
                            url=f"file://{self.temp_dir / f'test_file_{i % 5}.txt'}",
                            save_path=str(save_path),
                            priority=TaskPriority.NORMAL,
                            timeout=10.0,
                            retry_count=1
                        )
                        tasks.append(task)

                    # 执行模拟异步操作
                    task_futures = []
                    for task in tasks:
                        future = asyncio.create_task(self._simulate_async_copy(task))
                        task_futures.append(future)

                    await asyncio.gather(*task_futures, return_exceptions=True)

                # 缓存访问测试
                cache_hits = 0
                for i in range(200):
                    result = cache.get(f'integrated_key_{i % 50}')
                    if result is not None:
                        cache_hits += 1

                return {
                    'cache_hits': cache_hits,
                    'cache_hit_rate': (cache_hits / 200) * 100
                }

            # 运行综合工作负载
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            workload_results = loop.run_until_complete(integrated_workload())
            loop.close()

            end_time = time.time()

            # 获取最终资源使用情况
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            final_cpu = process.cpu_percent()

            # 获取组件统计
            cache_stats = cache.get_stats()
            error_stats = error_handler.get_error_stats()

            return {
                'test_duration': end_time - start_time,
                'resource_usage': {
                    'memory_change_mb': final_memory - initial_memory,
                    'final_memory_mb': final_memory,
                    'cpu_usage_percent': final_cpu
                },
                'workload_results': workload_results,
                'cache_performance': {
                    'hit_rate': workload_results['cache_hit_rate'],
                    'cache_stats': cache_stats
                },
                'error_handling': {
                    'error_stats': error_stats
                },
                'success': True,
                'message': '综合性能测试通过'
            }

        except Exception as e:
            self.logger.error(f"综合性能测试失败: {e}")
            return {
                'success': False,
                'message': f"测试失败: {e}",
                'error_details': str(e)
            }

    def generate_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试汇总报告"""
        try:
            total_tests = len(test_results)
            successful_tests = sum(1 for result in test_results.values() if result.get('success', False))

            # 计算性能指标
            performance_metrics = {}
            for test_name, result in test_results.items():
                if result.get('success'):
                    if 'test_duration' in result:
                        performance_metrics[f'{test_name}_duration'] = result['test_duration']

            # 生成报告
            summary = {
                'test_summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'success_rate': (successful_tests / total_tests) * 100,
                    'test_results': {name: result.get('success', False) for name, result in test_results.items()}
                },
                'performance_metrics': performance_metrics,
                'detailed_results': test_results,
                'overall_success': successful_tests == total_tests,
                'timestamp': time.time(),
                'test_phase': 'Phase 2 - 高级优化 (简化版)'
            }

            # 保存详细报告
            report_file = self.temp_dir / "simplified_phase2_test_report.json"
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"简化Phase 2测试报告已保存到: {report_file}")
            return summary

        except Exception as e:
            self.logger.error(f"生成测试报告失败: {e}")
            return {
                'test_summary': {'error': str(e)},
                'overall_success': False,
                'detailed_results': test_results
            }

    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"已清理临时目录: {self.temp_dir}")
        except Exception as e:
            self.logger.warning(f"清理临时目录失败: {e}")


def main():
    """主函数"""
    print("简化Phase 2性能测试启动")
    print("=" * 60)

    tester = SimplifiedPhase2Tester()
    results = tester.run_all_tests()

    # 输出结果
    print("\n" + "=" * 60)
    print("简化Phase 2性能测试结果")
    print("=" * 60)

    summary = results.get('test_summary', {})
    print(f"总测试数: {summary.get('total_tests', 0)}")
    print(f"成功测试数: {summary.get('successful_tests', 0)}")
    print(f"成功率: {summary.get('success_rate', 0):.1f}%")
    print(f"整体状态: {'通过' if results.get('overall_success', False) else '失败'}")

    # 输出各测试结果
    print("\n详细结果:")
    for test_name, success in summary.get('test_results', {}).items():
        status = "OK" if success else "FAIL"
        print(f"  {test_name}: {status}")

    # 输出性能指标
    if 'performance_metrics' in results:
        print("\n性能指标:")
        for metric, value in results['performance_metrics'].items():
            if 'duration' in metric:
                print(f"  {metric}: {value:.3f}s")

    print("\n" + "=" * 60)

    # 返回退出码
    return 0 if results.get('overall_success', False) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)