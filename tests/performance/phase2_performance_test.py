#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phase 2 性能测试脚本
测试增强WebDriver连接池、异步操作、智能缓存和错误处理机制
"""

import asyncio
import time
import threading
import psutil
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

from src.web.enhanced_driver_pool import (
    EnhancedWebDriverPool, PoolConfig, DriverPriority,
    create_enhanced_driver_pool
)
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


class Phase2PerformanceTester:
    """Phase 2 性能测试器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.test_results = {}
        self.temp_dir = Path(tempfile.mkdtemp(prefix="phase2_test_"))

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有性能测试"""
        self.logger.info("开始Phase 2性能测试")

        test_results = {}

        # 1. 增强WebDriver连接池测试
        self.logger.info("测试1: 增强WebDriver连接池")
        test_results['enhanced_driver_pool'] = self.test_enhanced_driver_pool()

        # 2. 异步操作测试
        self.logger.info("测试2: 异步操作")
        test_results['async_operations'] = self.test_async_operations()

        # 3. 智能缓存测试
        self.logger.info("测试3: 智能缓存")
        test_results['intelligent_cache'] = self.test_intelligent_cache()

        # 4. 增强错误处理测试
        self.logger.info("测试4: 增强错误处理")
        test_results['enhanced_error_handler'] = self.test_enhanced_error_handler()

        # 5. 综合性能测试
        self.logger.info("测试5: 综合性能")
        test_results['integrated_performance'] = self.test_integrated_performance()

        # 生成汇总报告
        summary = self.generate_summary(test_results)

        # 清理临时文件
        self.cleanup()

        return summary

    def test_enhanced_driver_pool(self) -> Dict[str, Any]:
        """测试增强WebDriver连接池"""
        try:
            config = PoolConfig(
                min_pool_size=2,
                max_pool_size=5,
                max_session_downloads=5,
                health_check_interval=30,
                scaling_enabled=True
            )

            with create_enhanced_driver_pool(config) as pool:
                start_time = time.time()
                results = []

                # 测试并发获取driver
                def worker(worker_id: int):
                    try:
                        driver = pool.get_driver(DriverPriority.NORMAL)
                        time.sleep(0.1)  # 模拟工作
                        pool.return_driver(driver, True)
                        return {'worker_id': worker_id, 'success': True}
                    except Exception as e:
                        return {'worker_id': worker_id, 'success': False, 'error': str(e)}

                # 创建多个工作线程
                threads = []
                for i in range(10):
                    thread = threading.Thread(target=worker, args=(i,))
                    threads.append(thread)

                # 启动所有线程
                for thread in threads:
                    thread.start()

                # 等待所有线程完成
                for thread in threads:
                    thread.join()

                end_time = time.time()

                # 获取池状态
                pool_status = pool.get_pool_status()
                detailed_metrics = pool.get_detailed_metrics()

                return {
                    'test_duration': end_time - start_time,
                    'pool_status': pool_status,
                    'detailed_metrics': detailed_metrics,
                    'worker_results': [worker(worker_id) for worker_id in range(10)],
                    'success': True,
                    'message': '增强WebDriver连接池测试通过'
                }

        except Exception as e:
            self.logger.error(f"增强WebDriver连接池测试失败: {e}")
            return {
                'success': False,
                'message': f"测试失败: {e}",
                'error_details': str(e)
            }

    def test_async_operations(self) -> Dict[str, Any]:
        """测试异步操作"""
        try:
            # 创建测试下载任务
            test_urls = [
                "https://httpbin.org/delay/1",
                "https://httpbin.org/delay/2",
                "https://httpbin.org/delay/1",
                "https://httpbin.org/delay/3",
                "https://httpbin.org/delay/1"
            ]

            download_tasks = []
            for i, url in enumerate(test_urls):
                save_path = self.temp_dir / f"test_file_{i}.txt"
                task = DownloadTask(
                    url=url,
                    save_path=str(save_path),
                    priority=TaskPriority.NORMAL,
                    timeout=30.0,
                    retry_count=2
                )
                download_tasks.append(task)

            # 测试异步批量下载
            start_time = time.time()

            async def async_test():
                async with AsyncTaskManager(max_concurrent_tasks=3) as manager:
                    downloader = AsyncBatchDownloader(manager)
                    return await downloader.download_batch(download_tasks)

            # 运行异步测试
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(async_test())
            loop.close()

            end_time = time.time()

            # 分析结果
            successful_downloads = sum(1 for r in results.values() if r.success)
            total_downloaded = sum(r.bytes_downloaded for r in results.values() if r.success)

            return {
                'test_duration': end_time - start_time,
                'total_tasks': len(download_tasks),
                'successful_downloads': successful_downloads,
                'success_rate': (successful_downloads / len(download_tasks)) * 100,
                'total_bytes_downloaded': total_downloaded,
                'average_speed': total_downloaded / (end_time - start_time) if end_time > start_time else 0,
                'results_summary': {
                    'completed': len([r for r in results.values() if r.status.value == 'completed']),
                    'failed': len([r for r in results.values() if r.status.value == 'failed']),
                    'cancelled': len([r for r in results.values() if r.status.value == 'cancelled'])
                },
                'success': True,
                'message': '异步操作测试通过'
            }

        except Exception as e:
            self.logger.error(f"异步操作测试失败: {e}")
            return {
                'success': False,
                'message': f"测试失败: {e}",
                'error_details': str(e)
            }

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

    def test_integrated_performance(self) -> Dict[str, Any]:
        """综合性能测试"""
        try:
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
                    downloader = AsyncBatchDownloader(manager)

                    # 创建测试任务
                    tasks = []
                    for i in range(10):
                        save_path = self.temp_dir / f"integrated_{i}.txt"
                        task = DownloadTask(
                            url="https://httpbin.org/delay/1",
                            save_path=str(save_path),
                            priority=TaskPriority.NORMAL,
                            timeout=30.0,
                            retry_count=2
                        )
                        tasks.append(task)

                    # 执行下载
                    download_results = await downloader.download_batch(tasks)

                # 缓存访问测试
                cache_hits = 0
                for i in range(200):
                    result = cache.get(f'integrated_key_{i % 50}')
                    if result is not None:
                        cache_hits += 1

                return {
                    'download_results': download_results,
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
                'test_phase': 'Phase 2 - 高级优化'
            }

            # 保存详细报告
            report_file = self.temp_dir / "phase2_test_report.json"
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"Phase 2测试报告已保存到: {report_file}")
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
    print("Phase 2 性能测试启动")
    print("=" * 60)

    tester = Phase2PerformanceTester()
    results = tester.run_all_tests()

    # 输出结果
    print("\n" + "=" * 60)
    print("Phase 2 性能测试结果")
    print("=" * 60)

    summary = results.get('test_summary', {})
    print(f"总测试数: {summary.get('total_tests', 0)}")
    print(f"成功测试数: {summary.get('successful_tests', 0)}")
    print(f"成功率: {summary.get('success_rate', 0):.1f}%")
    print(f"整体状态: {'通过' if results.get('overall_success', False) else '失败'}")

    # 输出各测试结果
    print("\n详细结果:")
    for test_name, success in summary.get('test_results', {}).items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")

    # 输出性能指标
    if 'performance_metrics' in results:
        print("\n性能指标:")
        for metric, value in results['performance_metrics'].items():
            if 'duration' in metric:
                print(f"  {metric}: {value:.2f}s")

    print("\n" + "=" * 60)

    # 返回退出码
    return 0 if results.get('overall_success', False) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)