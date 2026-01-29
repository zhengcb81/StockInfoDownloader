#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能测试模块

测试各个组件的性能表现，包括响应时间、内存使用等
"""

import json
import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import psutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.unified_downloader import UnifiedDownloader
from tests.test_config import TEST_ORG_IDS, EnvironmentManager, create_test_mapping


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
            return {}

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
            "current_memory": end_memory,
        }


class TestUnifiedDownloaderPerformance(PerformanceTestCase):
    """UnifiedDownloader 性能测试"""

    def test_downloader_initialization_performance(self):
        """测试下载器初始化性能"""
        save_dir = self.test_env.create_temp_dir()
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False),
        )

        self.start_performance_monitoring()

        # 创建多个下载器实例
        downloaders = []
        config = {
            "save_dir": str(save_dir), 
            "files": {"mapping_file": str(mapping_file)}, 
            "skip_browser_init": True
        }
        
        for _ in range(50):
            downloader = UnifiedDownloader(config=config)
            downloaders.append(downloader)

        stats = self.end_performance_monitoring("创建50个下载器实例")

        # 性能断言
        self.assertLess(stats["elapsed_time"], 1.5, "创建50个实例应在1.5秒内完成")
        self.assertLess(stats["memory_diff"], 50, "内存增长应小于50MB")

    def test_filename_cleaning_performance(self):
        """测试文件名清理性能"""
        save_dir = self.test_env.create_temp_dir()
        config = {"save_dir": str(save_dir), "skip_browser_init": True}
        downloader = UnifiedDownloader(config=config)

        # 准备测试数据
        test_filenames = [f'测试文件名{i}/\\:*?""<>|.pdf' for i in range(10000)]

        self.start_performance_monitoring()

        # 执行大量文件名清理
        cleaned_names = []
        for filename in test_filenames:
            cleaned = downloader.file_service.clean_filename(filename)
            cleaned_names.append(cleaned)

        stats = self.end_performance_monitoring("清理10000个文件名")

        # 验证结果
        self.assertEqual(len(cleaned_names), 10000)
        for name in cleaned_names:
            self.assertNotIn("/", name)
            self.assertNotIn("\\", name)
            self.assertNotIn(":", name)

        # 性能断言
        self.assertLess(stats["elapsed_time"], 1.0, "清理10000个文件名应在1秒内完成")

    @patch("src.web.browser_strategy.BrowserStrategyFactory.create_strategy")
    def test_webdriver_setup_performance(self, mock_create):
        """测试WebDriver设置性能"""
        mock_strategy = MagicMock()
        mock_create.return_value = mock_strategy

        save_dir = self.test_env.create_temp_dir()
        # Initial config skips init
        config = {"save_dir": str(save_dir), "skip_browser_init": True}
        downloader = UnifiedDownloader(config=config)

        self.start_performance_monitoring()

        # 执行多次WebDriver设置
        for _ in range(10):
            # Manually trigger init
            downloader._init_browser_strategy(force=True)
            self.assertIsNotNone(downloader.browser_strategy)
            # Simulate close logic if needed, but UnifiedDownloader handles it
            
        stats = self.end_performance_monitoring("WebDriver设置(10次)")

        # 性能断言
        self.assertLess(stats["elapsed_time"], 2.0, "10次WebDriver设置应在2秒内完成")


class TestConcurrencyPerformance(PerformanceTestCase):
    """并发性能测试"""

    def test_concurrent_downloader_creation(self):
        """测试并发创建下载器的性能"""
        save_dir = self.test_env.create_temp_dir()
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False),
        )

        downloaders = []
        errors = []
        
        config = {
            "save_dir": str(save_dir), 
            "files": {"mapping_file": str(mapping_file)}, 
            "skip_browser_init": True
        }

        def create_downloader():
            """创建下载器的工作函数"""
            try:
                downloader = UnifiedDownloader(config=config)
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

    def test_downloader_cleanup_effectiveness(self):
        """测试下载器清理的有效性"""
        save_dir = self.test_env.create_temp_dir()
        mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(create_test_mapping(), ensure_ascii=False),
        )

        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        config = {
            "save_dir": str(save_dir), 
            "files": {"mapping_file": str(mapping_file)}, 
            "skip_browser_init": True
        }

        # 创建和销毁多个下载器
        for i in range(20):
            downloader = UnifiedDownloader(config=config)

            # 模拟一些操作
            for stock_code in list(TEST_ORG_IDS.keys())[:3]:
                # UnifiedDownloader doesn't have get_org_id directly exposed usually, uses internal mapping
                # But we can access file service
                cleaned_name = downloader.file_service.clean_filename(f"测试文件{i}.pdf")

            # 显式清理
            downloader.cleanup()
            # 显式删除引用
            del downloader

            # 每5次检查一次内存
            if (i + 1) % 5 == 0:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                print(
                    f"创建{i + 1}个下载器后: 内存使用 {current_memory:.2f} MB (+{memory_growth:.2f} MB)"
                )

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory

        # 总内存增长应该在合理范围内
        self.assertLess(total_growth, 50, "创建20个下载器后内存增长应小于50MB")


if __name__ == "__main__":
    # 运行性能测试
    unittest.main(verbosity=2)