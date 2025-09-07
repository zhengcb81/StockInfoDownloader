#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基础功能测试

测试核心功能，不依赖网络连接
"""

import unittest
import tempfile
import json
import os
import sys
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cninfo_activity_downloader import CninfoDownloader
from tests.test_config import TestEnvironment

class TestBasicFunctionality(unittest.TestCase):
    """基础功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_save_dir = self.test_env.create_temp_dir("test_downloads_")
        
        # 创建简单的测试映射文件
        self.test_mapping = {
            "000001": {"orgId": "9900000001", "name": "平安银行"},
            "002415": {"orgId": "9900012688", "name": "海康威视"}
        }
        self.test_mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps(self.test_mapping, ensure_ascii=False, indent=2)
        )
        
        self.downloader = CninfoDownloader(
            save_dir=self.test_save_dir,
            mapping_file=self.test_mapping_file
        )
    
    def tearDown(self):
        """测试后清理"""
        if hasattr(self.downloader, 'driver') and self.downloader.driver:
            try:
                self.downloader.close_driver()
            except Exception:
                pass
        self.test_env.cleanup()
    
    def test_downloader_initialization(self):
        """测试下载器初始化"""
        self.assertIsNotNone(self.downloader)
        self.assertEqual(self.downloader.save_dir, self.test_save_dir)
        self.assertEqual(self.downloader.mapping_file, self.test_mapping_file)
        self.assertEqual(self.downloader.download_count, 0)
        self.assertTrue(os.path.exists(self.test_save_dir))
    
    def test_clean_filename(self):
        """测试文件名清理功能"""
        test_cases = [
            ("正常文件名.pdf", "正常文件名.pdf"),
            ("包含/非法\\字符:的*文件?名<>.pdf", "包含_非法_字符_的_文件_名__.pdf"),
            ("包含|管道\"引号的文件名.pdf", "包含_管道_引号的文件名.pdf"),
            ("", ""),
            ("测试文件名.pdf", "测试文件名.pdf"),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.downloader.clean_filename(input_name)
                self.assertEqual(result, expected)
    
    def test_get_org_id_from_mapping(self):
        """测试从映射文件获取组织ID"""
        # 测试存在的股票代码
        org_id = self.downloader.get_org_id("000001")
        self.assertEqual(org_id, "9900000001")
        
        org_id = self.downloader.get_org_id("002415")
        self.assertEqual(org_id, "9900012688")
    
    def test_get_org_id_not_found(self):
        """测试获取不存在的股票代码"""
        org_id = self.downloader.get_org_id("999999")
        self.assertIsNone(org_id)
    
    def test_driver_health_check_no_driver(self):
        """测试driver健康检查 - 无driver"""
        self.assertFalse(self.downloader._is_driver_healthy())
    
    def test_driver_health_check_with_mock_driver(self):
        """测试driver健康检查 - 有mock driver"""
        mock_driver = MagicMock()
        mock_driver.current_url = "http://test.com"
        self.downloader.driver = mock_driver
        
        self.assertTrue(self.downloader._is_driver_healthy())
    
    def test_driver_health_check_with_broken_driver(self):
        """测试driver健康检查 - 损坏的driver"""
        mock_driver = MagicMock()
        mock_driver.current_url.side_effect = Exception("Driver error")
        self.downloader.driver = mock_driver
        
        self.assertFalse(self.downloader._is_driver_healthy())
    
    def test_cleanup_pdf_txt(self):
        """测试清理pdf.txt文件"""
        # 创建一个pdf.txt文件
        pdf_txt_path = os.path.join(self.test_save_dir, "pdf.txt")
        with open(pdf_txt_path, 'w') as f:
            f.write("test content")
        
        self.assertTrue(os.path.exists(pdf_txt_path))
        
        self.downloader._cleanup_pdf_txt()
        
        self.assertFalse(os.path.exists(pdf_txt_path))
    
    def test_cleanup_pdf_txt_no_file(self):
        """测试清理pdf.txt文件 - 文件不存在"""
        # 应该不会抛出异常
        self.downloader._cleanup_pdf_txt()
    
    def test_random_delay(self):
        """测试随机延迟功能"""
        import time
        
        start_time = time.time()
        self.downloader.random_delay(0.1, 0.2)
        end_time = time.time()
        
        elapsed = end_time - start_time
        self.assertGreaterEqual(elapsed, 0.1)
        self.assertLessEqual(elapsed, 0.5)  # 给一些容差
    
    def test_simulate_human_behavior_no_driver(self):
        """测试模拟人类行为 - 无driver"""
        # 应该不会抛出异常
        self.downloader.simulate_human_behavior()
    
    def test_simulate_human_behavior_with_mock_driver(self):
        """测试模拟人类行为 - 有mock driver"""
        mock_driver = MagicMock()
        self.downloader.driver = mock_driver
        
        # 应该不会抛出异常
        self.downloader.simulate_human_behavior()
        
        # 验证调用了相关方法
        mock_driver.execute_script.assert_called()

class TestFileOperations(unittest.TestCase):
    """文件操作测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_create_save_directory(self):
        """测试创建保存目录"""
        test_dir = self.test_env.create_temp_dir("test_save_")
        downloader = CninfoDownloader(save_dir=test_dir)
        
        self.assertTrue(os.path.exists(test_dir))
        self.assertEqual(downloader.save_dir, test_dir)
    
    def test_create_nested_directory(self):
        """测试创建嵌套目录"""
        base_dir = self.test_env.create_temp_dir("test_base_")
        nested_dir = os.path.join(base_dir, "nested", "deep")
        
        downloader = CninfoDownloader(save_dir=nested_dir)
        
        self.assertTrue(os.path.exists(nested_dir))
        self.assertEqual(downloader.save_dir, nested_dir)

class TestConfigurationHandling(unittest.TestCase):
    """配置处理测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_default_configuration(self):
        """测试默认配置"""
        downloader = CninfoDownloader()
        
        self.assertEqual(downloader.save_dir, 'downloads')
        self.assertEqual(downloader.mapping_file, 'stock_orgid_mapping.json')
        self.assertEqual(downloader.download_count, 0)
        self.assertEqual(downloader.max_downloads_per_session, 5)
    
    def test_custom_configuration(self):
        """测试自定义配置"""
        test_dir = self.test_env.create_temp_dir("custom_")
        test_mapping = self.test_env.create_temp_file(suffix=".json")
        
        downloader = CninfoDownloader(
            save_dir=test_dir,
            mapping_file=test_mapping
        )
        
        self.assertEqual(downloader.save_dir, test_dir)
        self.assertEqual(downloader.mapping_file, test_mapping)
    
    def test_user_agent_pool(self):
        """测试User-Agent池"""
        downloader = CninfoDownloader()
        
        self.assertIsInstance(downloader.user_agents, list)
        self.assertGreater(len(downloader.user_agents), 0)
        
        # 验证所有User-Agent都包含必要的信息
        for ua in downloader.user_agents:
            self.assertIn('Mozilla', ua)
            self.assertIn('Chrome', ua)

if __name__ == "__main__":
    unittest.main() 