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
# 删除不存在的导入，改用现有的服务
from tests.test_config import EnvironmentManager, TEST_ORG_IDS, create_test_mapping

class PerformanceTestCase(unittest.TestCase):
    """性能测试基类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = EnvironmentManager()
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

# 注释掉依赖不存在函数的测试类
# class TestOrgidUtilsPerformance(PerformanceTestCase):
#     """orgid_utils 性能测试"""

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
            downloader = CninfoDownloader(save_dir=save_dir, mapping_file=mapping_file, skip_browser_init=True)
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
    
    @patch('src.web.browser_strategy.BrowserStrategyFactory.create_strategy')
    def test_webdriver_setup_performance(self, mock_create):
        """测试WebDriver设置性能"""
        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy

        downloader = CninfoDownloader(save_dir=self.test_env.create_temp_dir(), skip_browser_init=True)
        
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
    
    # 注释掉依赖不存在函数的测试方法
    # def test_concurrent_mapping_access(self):
    #     """测试并发访问映射文件的性能"""
    #     pass
    
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
    
    # 注释掉依赖不存在函数的测试方法
    # def test_repeated_operations_memory_stability(self):
    #     """测试重复操作的内存稳定性"""
    #     pass
    
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