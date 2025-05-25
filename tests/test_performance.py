#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能测试模块

测试各个组件的性能表现，包括响应时间、内存使用等
"""

import unittest
import time
import psutil
import os
import sys
import json
import threading
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cninfo_activity_downloader import CninfoDownloader
from orgid_utils import get_org_id_by_code, load_mapping, save_mapping
from tests.test_config import TestEnvironment, TEST_ORG_IDS, create_test_mapping

class PerformanceTestCase(unittest.TestCase):
    """性能测试基类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.start_time = None
        self.start_memory = None
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def start_performance_monitoring(self):
        """开始性能监控"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
    
    def end_performance_monitoring(self, operation_name="操作"):
        """结束性能监控并记录结果"""
        if self.start_time is None:
            return
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        elapsed_time = end_time - self.start_time
        memory_diff = end_memory - self.start_memory
        
        print(f"\n{operation_name}性能统计:")
        print(f"  执行时间: {elapsed_time:.3f} 秒")
        print(f"  内存变化: {memory_diff:+.2f} MB")
        print(f"  当前内存: {end_memory:.2f} MB")
        
        return {
            "elapsed_time": elapsed_time,
            "memory_diff": memory_diff,
            "current_memory": end_memory
        }

class TestOrgidUtilsPerformance(PerformanceTestCase):
    """orgid_utils 性能测试"""
    
    def test_load_mapping_performance(self):
        """测试加载映射文件的性能"""
        # 创建大量测试数据
        large_mapping = {}
        for i in range(10000):
            stock_code = f"{i:06d}"
            large_mapping[stock_code] = {
                "org_id": f"org_{i}",
                "name": f"股票{i}",
                "market": "测试市场"
            }
        
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(large_mapping, ensure_ascii=False)
        )
        
        self.start_performance_monitoring()
        
        # 执行多次加载测试
        for _ in range(10):
            mapping = load_mapping(mapping_file)
            self.assertEqual(len(mapping), 10000)
        
        stats = self.end_performance_monitoring("加载大型映射文件(10次)")
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 5.0, "加载10000条记录10次应在5秒内完成")
        self.assertLess(stats["memory_diff"], 100, "内存增长应小于100MB")
    
    def test_save_mapping_performance(self):
        """测试保存映射文件的性能"""
        large_mapping = create_test_mapping()
        
        # 扩展到更大的数据集
        for i in range(1000):
            stock_code = f"test_{i:06d}"
            large_mapping[stock_code] = {
                "org_id": f"org_{i}",
                "name": f"测试股票{i}"
            }
        
        mapping_file = self.test_env.create_temp_file(suffix=".json")
        
        self.start_performance_monitoring()
        
        # 执行多次保存测试
        for _ in range(5):
            result = save_mapping(large_mapping, mapping_file)
            self.assertTrue(result)
        
        stats = self.end_performance_monitoring("保存大型映射文件(5次)")
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 3.0, "保存1000+条记录5次应在3秒内完成")
    
    def test_get_org_id_performance(self):
        """测试获取组织ID的性能"""
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False)
        )
        
        self.start_performance_monitoring()
        
        # 执行大量查询
        for _ in range(1000):
            for stock_code in TEST_ORG_IDS.keys():
                org_id = get_org_id_by_code(stock_code, mapping_file=mapping_file)
                self.assertIsNotNone(org_id)
        
        stats = self.end_performance_monitoring("获取组织ID(5000次查询)")
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 2.0, "5000次查询应在2秒内完成")

class TestCninfoDownloaderPerformance(PerformanceTestCase):
    """CninfoDownloader 性能测试"""
    
    def test_downloader_initialization_performance(self):
        """测试下载器初始化性能"""
        save_dir = self.test_env.create_temp_dir()
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False)
        )
        
        self.start_performance_monitoring()
        
        # 创建多个下载器实例
        downloaders = []
        for _ in range(50):
            downloader = CninfoDownloader(save_dir=save_dir, mapping_file=mapping_file)
            downloaders.append(downloader)
        
        stats = self.end_performance_monitoring("创建50个下载器实例")
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 1.0, "创建50个实例应在1秒内完成")
        self.assertLess(stats["memory_diff"], 50, "内存增长应小于50MB")
    
    def test_filename_cleaning_performance(self):
        """测试文件名清理性能"""
        downloader = CninfoDownloader(save_dir=self.test_env.create_temp_dir())
        
        # 准备测试数据
        test_filenames = [
            f"测试文件名{i}/\\:*?\"<>|.pdf" for i in range(10000)
        ]
        
        self.start_performance_monitoring()
        
        # 执行大量文件名清理
        cleaned_names = []
        for filename in test_filenames:
            cleaned = downloader.clean_filename(filename)
            cleaned_names.append(cleaned)
        
        stats = self.end_performance_monitoring("清理10000个文件名")
        
        # 验证结果
        self.assertEqual(len(cleaned_names), 10000)
        for name in cleaned_names:
            self.assertNotIn('/', name)
            self.assertNotIn('\\', name)
            self.assertNotIn(':', name)
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 1.0, "清理10000个文件名应在1秒内完成")
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_webdriver_setup_performance(self, mock_chrome):
        """测试WebDriver设置性能"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        downloader = CninfoDownloader(save_dir=self.test_env.create_temp_dir())
        
        self.start_performance_monitoring()
        
        # 执行多次WebDriver设置
        for _ in range(10):
            result = downloader.setup_driver(headless=True)
            self.assertTrue(result)
            downloader.close_driver()
        
        stats = self.end_performance_monitoring("WebDriver设置和关闭(10次)")
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 2.0, "10次WebDriver设置应在2秒内完成")

class TestConcurrencyPerformance(PerformanceTestCase):
    """并发性能测试"""
    
    def test_concurrent_mapping_access(self):
        """测试并发访问映射文件的性能"""
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False)
        )
        
        results = []
        errors = []
        
        def worker():
            """工作线程函数"""
            try:
                for _ in range(100):
                    for stock_code in TEST_ORG_IDS.keys():
                        org_id = get_org_id_by_code(stock_code, mapping_file=mapping_file)
                        if org_id:
                            results.append(org_id)
            except Exception as e:
                errors.append(e)
        
        self.start_performance_monitoring()
        
        # 创建多个线程并发访问
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        stats = self.end_performance_monitoring("5线程并发访问映射文件")
        
        # 验证结果
        self.assertEqual(len(errors), 0, "不应该有错误发生")
        self.assertGreater(len(results), 0, "应该有结果返回")
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 5.0, "并发访问应在5秒内完成")
    
    def test_concurrent_downloader_creation(self):
        """测试并发创建下载器的性能"""
        save_dir = self.test_env.create_temp_dir()
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False)
        )
        
        downloaders = []
        errors = []
        
        def create_downloader():
            """创建下载器的工作函数"""
            try:
                downloader = CninfoDownloader(save_dir=save_dir, mapping_file=mapping_file)
                downloaders.append(downloader)
            except Exception as e:
                errors.append(e)
        
        self.start_performance_monitoring()
        
        # 创建多个线程并发创建下载器
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_downloader)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        stats = self.end_performance_monitoring("10线程并发创建下载器")
        
        # 验证结果
        self.assertEqual(len(errors), 0, "不应该有错误发生")
        self.assertEqual(len(downloaders), 10, "应该创建10个下载器")
        
        # 性能断言
        self.assertLess(stats["elapsed_time"], 3.0, "并发创建应在3秒内完成")

class TestMemoryLeakage(PerformanceTestCase):
    """内存泄漏测试"""
    
    def test_repeated_operations_memory_stability(self):
        """测试重复操作的内存稳定性"""
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False)
        )
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # 执行大量重复操作
        for cycle in range(10):
            # 每个周期执行1000次操作
            for _ in range(1000):
                mapping = load_mapping(mapping_file)
                for stock_code in TEST_ORG_IDS.keys():
                    org_id = get_org_id_by_code(stock_code, mapping_file=mapping_file)
            
            # 检查内存使用
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_growth = current_memory - initial_memory
            
            print(f"周期 {cycle + 1}: 内存使用 {current_memory:.2f} MB (+{memory_growth:.2f} MB)")
            
            # 内存增长不应该过大
            self.assertLess(memory_growth, 100, f"第{cycle + 1}周期内存增长过大")
    
    def test_downloader_cleanup_effectiveness(self):
        """测试下载器清理的有效性"""
        save_dir = self.test_env.create_temp_dir()
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False)
        )
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # 创建和销毁多个下载器
        for i in range(20):
            downloader = CninfoDownloader(save_dir=save_dir, mapping_file=mapping_file)
            
            # 模拟一些操作
            for stock_code in list(TEST_ORG_IDS.keys())[:3]:
                org_id = downloader.get_org_id(stock_code)
                cleaned_name = downloader.clean_filename(f"测试文件{i}.pdf")
            
            # 显式删除引用
            del downloader
            
            # 每5次检查一次内存
            if (i + 1) % 5 == 0:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                print(f"创建{i + 1}个下载器后: 内存使用 {current_memory:.2f} MB (+{memory_growth:.2f} MB)")
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        # 总内存增长应该在合理范围内
        self.assertLess(total_growth, 50, "创建20个下载器后内存增长应小于50MB")

if __name__ == "__main__":
    # 运行性能测试
    unittest.main(verbosity=2) 