#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能测试运行器
用于CI/CD流程中的性能测试
"""

import time
import sys
import json
import psutil
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.downloader import DownloadService
from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig
from tests.performance.assertion_utils import PerformanceAssertions


class PerformanceTestRunner:
    """性能测试运行器"""
    
    def __init__(self, report_dir: str = "performance_reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
        
    def run_performance_tests(self) -> str:
        """运行所有性能测试"""
        print("开始运行性能测试...")
        
        results = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "performance",
                "description": "性能测试套件"
            },
            "environment": self._get_environment_info(),
            "tests": []
        }
        
        # 运行各项性能测试
        test_methods = [
            self.test_memory_usage,
            self.test_cpu_usage,
            self.test_keyword_matching_performance,
            self.test_file_operations_performance,
            self.test_mapping_operations_performance,
            self.test_concurrent_operations_performance
        ]
        
        for test_method in test_methods:
            try:
                test_result = test_method()
                results["tests"].append(test_result)
                print(f"✅ {test_method.__name__} 完成")
            except Exception as e:
                print(f"❌ {test_method.__name__} 失败: {e}")
                results["tests"].append({
                    "test_name": test_method.__name__,
                    "success": False,
                    "error": str(e),
                    "execution_time": 0
                })
        
        # 生成性能测试报告
        report_file = self._generate_performance_report(results)
        print(f"性能测试报告已生成: {report_file}")
        
        return report_file
    
    def test_memory_usage(self) -> Dict[str, Any]:
        """测试内存使用情况"""
        test_name = "内存使用测试"
        start_time = time.time()
        
        try:
            import gc
            gc.collect()  # 强制垃圾回收
            
            # 获取初始内存使用
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # 创建大量对象测试内存使用
            objects = []
            for i in range(10000):
                obj = {
                    "id": i,
                    "data": f"test_data_{i}" * 100,
                    "timestamp": datetime.now().isoformat()
                }
                objects.append(obj)
            
            # 获取峰值内存使用
            peak_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # 清理对象
            del objects
            gc.collect()
            
            # 获取最终内存使用
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            memory_growth = peak_memory - initial_memory
            memory_leak = final_memory - initial_memory
            
            execution_time = time.time() - start_time
            
            # 性能断言
            PerformanceAssertions.assert_memory_growth(
                initial_memory,
                peak_memory,
                50.0,  # 最大内存增长50MB
                f"{test_name}内存增长过大"
            )
            PerformanceAssertions.assert_memory_leak(
                initial_memory,
                final_memory,
                5.0,   # 最大内存泄漏5MB
                f"{test_name}内存泄漏"
            )

            return {
                "test_name": test_name,
                "success": True,
                "execution_time": execution_time,
                "metrics": {
                    "initial_memory_mb": round(initial_memory, 2),
                    "peak_memory_mb": round(peak_memory, 2),
                    "final_memory_mb": round(final_memory, 2),
                    "memory_growth_mb": round(memory_growth, 2),
                    "memory_leak_mb": round(memory_leak, 2),
                    "objects_created": 10000
                },
                "performance_criteria": {
                    "memory_growth_threshold_mb": 50,
                    "memory_leak_threshold_mb": 5,
                    "memory_growth_pass": memory_growth < 50,
                    "memory_leak_pass": memory_leak < 5
                }
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def test_cpu_usage(self) -> Dict[str, Any]:
        """测试CPU使用情况"""
        test_name = "CPU使用测试"
        start_time = time.time()
        
        try:
            # 获取初始CPU使用率
            initial_cpu = psutil.cpu_percent(interval=1)
            
            # 执行CPU密集型任务
            start_cpu_time = time.time()
            
            # 计算密集型操作
            result = 0
            for i in range(1000000):
                result += i * i
            
            # 计算执行时间
            cpu_execution_time = time.time() - start_cpu_time
            
            # 获取CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            execution_time = time.time() - start_time

            # 性能断言
            PerformanceAssertions.assert_cpu_usage(
                cpu_usage,
                80.0,  # 最大CPU使用率80%
                f"{test_name}CPU使用率过高"
            )
            PerformanceAssertions.assert_response_time(
                cpu_execution_time,
                5.0,  # 最大执行时间5秒
                f"{test_name}执行时间过长"
            )

            return {
                "test_name": test_name,
                "success": True,
                "execution_time": execution_time,
                "metrics": {
                    "initial_cpu_percent": initial_cpu,
                    "peak_cpu_percent": cpu_usage,
                    "cpu_execution_time": round(cpu_execution_time, 3),
                    "calculation_iterations": 1000000,
                    "calculation_result": result
                },
                "performance_criteria": {
                    "cpu_usage_threshold_percent": 80,
                    "execution_time_threshold_seconds": 5,
                    "cpu_usage_pass": cpu_usage < 80,
                    "execution_time_pass": cpu_execution_time < 5
                }
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def test_keyword_matching_performance(self) -> Dict[str, Any]:
        """测试关键词匹配性能"""
        test_name = "关键词匹配性能测试"
        start_time = time.time()
        
        try:
            # 创建测试数据
            test_texts = [
                "投资者关系活动记录表",
                "机构调研报告",
                "年度财务报告",
                "季度业绩公告",
                "重大事项公告"
            ] * 1000  # 5000个测试文本
            
            keywords = ["投资者关系", "调研", "财务", "业绩", "重大事项"]
            
            # 测试关键词匹配器性能
            config = KeywordConfig(
                allowed_keywords=keywords,
                mode="any"
            )
            matcher = KeywordMatcher(config)
            
            # 执行匹配测试
            start_match_time = time.time()
            matches = 0
            
            for text in test_texts:
                if matcher.matches(text):
                    matches += 1
            
            matching_time = time.time() - start_match_time
            execution_time = time.time() - start_time

            # 性能断言
            PerformanceAssertions.assert_response_time(
                matching_time,
                1.0,  # 最大匹配时间1秒
                f"{test_name}匹配时间过长"
            )
            PerformanceAssertions.assert_response_time(
                matching_time / len(test_texts) * 1000,
                1.0,  # 最大平均时间每文本1毫秒
                f"{test_name}平均匹配时间过长"
            )

            return {
                "test_name": test_name,
                "success": True,
                "execution_time": execution_time,
                "metrics": {
                    "total_texts": len(test_texts),
                    "matches_found": matches,
                    "matching_time_seconds": round(matching_time, 3),
                    "average_time_per_text_ms": round(matching_time / len(test_texts) * 1000, 3),
                    "keywords_count": len(keywords)
                },
                "performance_criteria": {
                    "matching_time_threshold_seconds": 1,
                    "average_time_per_text_threshold_ms": 1,
                    "matching_time_pass": matching_time < 1,
                    "average_time_pass": matching_time / len(test_texts) * 1000 < 1
                }
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def test_file_operations_performance(self) -> Dict[str, Any]:
        """测试文件操作性能"""
        test_name = "文件操作性能测试"
        start_time = time.time()
        
        try:
            import tempfile
            import shutil
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            
            # 测试文件写入性能
            start_write_time = time.time()
            
            files_created = 0
            for i in range(100):
                file_path = os.path.join(temp_dir, f"test_file_{i}.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"测试内容 {i}\n" * 100)
                files_created += 1
            
            write_time = time.time() - start_write_time
            
            # 测试文件读取性能
            start_read_time = time.time()
            
            files_read = 0
            total_content = 0
            for i in range(100):
                file_path = os.path.join(temp_dir, f"test_file_{i}.txt")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_content += len(content)
                files_read += 1
            
            read_time = time.time() - start_read_time
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            execution_time = time.time() - start_time

            # 性能断言
            PerformanceAssertions.assert_response_time(
                write_time,
                5.0,  # 最大写入时间5秒
                f"{test_name}文件写入时间过长"
            )
            PerformanceAssertions.assert_response_time(
                read_time,
                2.0,  # 最大读取时间2秒
                f"{test_name}文件读取时间过长"
            )

            return {
                "test_name": test_name,
                "success": True,
                "execution_time": execution_time,
                "metrics": {
                    "files_created": files_created,
                    "files_read": files_read,
                    "write_time_seconds": round(write_time, 3),
                    "read_time_seconds": round(read_time, 3),
                    "total_content_bytes": total_content,
                    "average_write_time_per_file_ms": round(write_time / files_created * 1000, 3),
                    "average_read_time_per_file_ms": round(read_time / files_read * 1000, 3)
                },
                "performance_criteria": {
                    "write_time_threshold_seconds": 5,
                    "read_time_threshold_seconds": 2,
                    "write_time_pass": write_time < 5,
                    "read_time_pass": read_time < 2
                }
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def test_mapping_operations_performance(self) -> Dict[str, Any]:
        """测试映射操作性能"""
        test_name = "映射操作性能测试"
        start_time = time.time()
        
        try:
            from src.data.mapping import MappingManager
            import tempfile
            import json
            
            # 创建临时映射文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            temp_file.close()
            
            # 生成大量映射数据
            mapping_data = {}
            for i in range(10000):
                stock_code = f"300{i:04d}"
                mapping_data[stock_code] = {
                    "org_id": f"99000{i:08d}",
                    "name": f"测试公司{i}"
                }
            
            with open(temp_file.name, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
            
            # 测试映射加载性能
            start_load_time = time.time()
            manager = MappingManager(temp_file.name)
            load_time = time.time() - start_load_time
            
            # 测试映射查询性能
            start_query_time = time.time()
            queries = 0
            successful_queries = 0
            
            for i in range(1000):
                stock_code = f"300{i:04d}"
                org_id = manager.get_org_id(stock_code)
                queries += 1
                if org_id:
                    successful_queries += 1
            
            query_time = time.time() - start_query_time
            
            # 清理临时文件
            os.unlink(temp_file.name)
            
            execution_time = time.time() - start_time

            # 性能断言
            PerformanceAssertions.assert_response_time(
                load_time,
                2.0,  # 最大加载时间2秒
                f"{test_name}映射加载时间过长"
            )
            PerformanceAssertions.assert_response_time(
                query_time,
                1.0,  # 最大查询时间1秒
                f"{test_name}映射查询时间过长"
            )
            PerformanceAssertions.assert_response_time(
                query_time / queries * 1000,
                1.0,  # 最大平均查询时间1毫秒
                f"{test_name}平均查询时间过长"
            )

            return {
                "test_name": test_name,
                "success": True,
                "execution_time": execution_time,
                "metrics": {
                    "mapping_entries": len(mapping_data),
                    "load_time_seconds": round(load_time, 3),
                    "queries_performed": queries,
                    "successful_queries": successful_queries,
                    "query_time_seconds": round(query_time, 3),
                    "average_query_time_ms": round(query_time / queries * 1000, 3)
                },
                "performance_criteria": {
                    "load_time_threshold_seconds": 2,
                    "query_time_threshold_seconds": 1,
                    "average_query_time_threshold_ms": 1,
                    "load_time_pass": load_time < 2,
                    "query_time_pass": query_time < 1,
                    "average_query_pass": query_time / queries * 1000 < 1
                }
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def test_concurrent_operations_performance(self) -> Dict[str, Any]:
        """测试并发操作性能"""
        test_name = "并发操作性能测试"
        start_time = time.time()
        
        try:
            import threading
            import queue
            import time
            
            # 创建任务队列
            task_queue = queue.Queue()
            result_queue = queue.Queue()
            
            # 添加任务
            num_tasks = 100
            for i in range(num_tasks):
                task_queue.put(i)
            
            # 定义工作线程
            def worker(worker_id):
                while not task_queue.empty():
                    try:
                        task_id = task_queue.get_nowait()
                        
                        # 模拟一些工作
                        start_task = time.time()
                        result = 0
                        for j in range(10000):
                            result += j * j
                        
                        task_time = time.time() - start_task
                        
                        result_queue.put({
                            "worker_id": worker_id,
                            "task_id": task_id,
                            "result": result,
                            "execution_time": task_time
                        })
                        
                    except queue.Empty:
                        break
            
            # 创建工作线程
            num_workers = 4
            workers = []
            
            start_concurrent_time = time.time()
            
            for i in range(num_workers):
                worker_thread = threading.Thread(target=worker, args=(i,))
                workers.append(worker_thread)
                worker_thread.start()
            
            # 等待所有工作线程完成
            for worker in workers:
                worker.join()
            
            concurrent_time = time.time() - start_concurrent_time
            
            # 收集结果
            results = []
            while not result_queue.empty():
                results.append(result_queue.get())
            
            execution_time = time.time() - start_time

            # 性能断言
            PerformanceAssertions.assert_concurrent_time(
                concurrent_time,
                10.0,  # 最大并发时间10秒
                f"{test_name}并发执行时间过长"
            )
            PerformanceAssertions.assert_throughput(
                len(results),
                concurrent_time,
                10.0,  # 最小吞吐量10任务/秒
                f"{test_name}吞吐量不足"
            )

            return {
                "test_name": test_name,
                "success": True,
                "execution_time": execution_time,
                "metrics": {
                    "num_workers": num_workers,
                    "num_tasks": num_tasks,
                    "completed_tasks": len(results),
                    "concurrent_time_seconds": round(concurrent_time, 3),
                    "average_task_time_seconds": round(sum(r["execution_time"] for r in results) / len(results), 3) if results else 0,
                    "throughput_tasks_per_second": round(len(results) / concurrent_time, 2)
                },
                "performance_criteria": {
                    "concurrent_time_threshold_seconds": 10,
                    "throughput_threshold_tasks_per_second": 10,
                    "concurrent_time_pass": concurrent_time < 10,
                    "throughput_pass": len(results) / concurrent_time >= 10
                }
            }
            
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": f"{os.name} {platform.system()} {platform.release()}",
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
            "disk_total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2)
        }
    
    def _generate_performance_report(self, results: Dict[str, Any]) -> str:
        """生成性能测试报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_dir / f"performance_report_{timestamp}.json"
        
        # 计算总体统计
        total_tests = len(results["tests"])
        passed_tests = sum(1 for test in results["tests"] if test["success"])
        failed_tests = total_tests - passed_tests
        
        # 添加汇总信息
        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": round(passed_tests / total_tests * 100, 1) if total_tests > 0 else 0,
            "total_execution_time": round(sum(test.get("execution_time", 0) for test in results["tests"]), 2)
        }
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        return str(report_file)


def main():
    """主函数"""
    print("性能测试运行器")
    print("=" * 50)
    
    runner = PerformanceTestRunner()
    report_file = runner.run_performance_tests()
    
    print(f"\n性能测试完成！")
    print(f"报告文件: {report_file}")


if __name__ == "__main__":
    main()