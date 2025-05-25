#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cninfo_activity_downloader 模块单元测试
"""

import unittest
import tempfile
import os
import sys
import json
import time
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cninfo_activity_downloader import CninfoDownloader
from tests.test_config import TestEnvironment, TEST_STOCK_CODES, TEST_ORG_IDS, create_test_config

class TestCninfoDownloader(unittest.TestCase):
    """CninfoDownloader 类单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_save_dir = self.test_env.create_temp_dir("test_downloads_")
        self.test_mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps({
                code: {"org_id": org_id, "name": f"测试股票{code}"}
                for code, org_id in TEST_ORG_IDS.items()
            }, ensure_ascii=False, indent=2)
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
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.downloader.save_dir, self.test_save_dir)
        self.assertEqual(self.downloader.mapping_file, self.test_mapping_file)
        self.assertEqual(self.downloader.download_count, 0)
        self.assertEqual(self.downloader.max_downloads_per_session, 5)
        self.assertIsNone(self.downloader.driver)
        
        # 验证保存目录已创建
        self.assertTrue(os.path.exists(self.test_save_dir))
    
    def test_clean_filename(self):
        """测试文件名清理函数"""
        test_cases = [
            ("正常文件名.pdf", "正常文件名.pdf"),
            ("包含/非法\\字符:的*文件?名<>.pdf", "包含_非法_字符_的_文件_名__.pdf"),
            ("包含|管道\"引号的文件名.pdf", "包含_管道_引号的文件名.pdf"),
            ("", ""),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.downloader.clean_filename(input_name)
                self.assertEqual(result, expected)
    
    def test_get_org_id(self):
        """测试获取组织ID"""
        for stock_code, expected_org_id in TEST_ORG_IDS.items():
            with self.subTest(stock_code=stock_code):
                org_id = self.downloader.get_org_id(stock_code)
                self.assertEqual(org_id, expected_org_id)
    
    def test_get_org_id_invalid_code(self):
        """测试获取无效股票代码的组织ID"""
        invalid_code = "999999"
        org_id = self.downloader.get_org_id(invalid_code)
        self.assertIsNone(org_id)
    
    def test_is_driver_healthy_no_driver(self):
        """测试driver健康检查 - 无driver"""
        self.assertFalse(self.downloader._is_driver_healthy())
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_setup_driver_success(self, mock_chrome):
        """测试WebDriver设置成功"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        result = self.downloader.setup_driver(headless=True)
        
        self.assertTrue(result)
        self.assertEqual(self.downloader.driver, mock_driver)
        mock_driver.set_page_load_timeout.assert_called_once_with(30)
        mock_driver.implicitly_wait.assert_called_once_with(10)
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_setup_driver_failure(self, mock_chrome):
        """测试WebDriver设置失败"""
        mock_chrome.side_effect = Exception("WebDriver初始化失败")
        
        result = self.downloader.setup_driver(headless=True)
        
        self.assertFalse(result)
        self.assertIsNone(self.downloader.driver)
    
    def test_close_driver_no_driver(self):
        """测试关闭driver - 无driver"""
        # 应该不会抛出异常
        self.downloader.close_driver()
        self.assertIsNone(self.downloader.driver)
    
    def test_close_driver_with_driver(self):
        """测试关闭driver - 有driver"""
        mock_driver = MagicMock()
        self.downloader.driver = mock_driver
        
        self.downloader.close_driver()
        
        mock_driver.close.assert_called_once()
        mock_driver.quit.assert_called_once()
        self.assertIsNone(self.downloader.driver)
    
    @patch.object(CninfoDownloader, 'setup_driver')
    @patch.object(CninfoDownloader, 'close_driver')
    def test_restart_driver_success(self, mock_close, mock_setup):
        """测试WebDriver重启成功"""
        mock_setup.return_value = True
        
        result = self.downloader.restart_driver(headless=True)
        
        self.assertTrue(result)
        mock_close.assert_called_once()
        mock_setup.assert_called_once_with(True)
    
    @patch.object(CninfoDownloader, 'setup_driver')
    @patch.object(CninfoDownloader, 'close_driver')
    def test_restart_driver_failure(self, mock_close, mock_setup):
        """测试WebDriver重启失败"""
        mock_setup.return_value = False
        
        result = self.downloader.restart_driver(headless=True)
        
        self.assertFalse(result)
        mock_close.assert_called_once()
        # setup_driver会被调用多次（重试机制）
        self.assertGreater(mock_setup.call_count, 0)
    
    def test_random_delay(self):
        """测试随机延迟函数"""
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
    
    def test_cleanup_pdf_txt(self):
        """测试清理pdf.txt文件"""
        # 创建一个pdf.txt文件
        pdf_txt_path = os.path.join(self.test_save_dir, "pdf.txt")
        with open(pdf_txt_path, 'w') as f:
            f.write("test content")
        
        self.assertTrue(os.path.exists(pdf_txt_path))
        
        self.downloader._cleanup_pdf_txt()
        
        self.assertFalse(os.path.exists(pdf_txt_path))

class TestCninfoDownloaderIntegration(unittest.TestCase):
    """CninfoDownloader 集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_save_dir = self.test_env.create_temp_dir("test_downloads_")
        self.test_mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps({
                "000001": {"org_id": "9900000062", "name": "平安银行"}
            }, ensure_ascii=False, indent=2)
        )
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_downloader_lifecycle(self):
        """测试下载器完整生命周期"""
        downloader = CninfoDownloader(
            save_dir=self.test_save_dir,
            mapping_file=self.test_mapping_file
        )
        
        # 验证初始化
        self.assertIsNotNone(downloader)
        self.assertEqual(downloader.save_dir, self.test_save_dir)
        
        # 验证获取组织ID
        org_id = downloader.get_org_id("000001")
        self.assertEqual(org_id, "9900000062")
        
        # 验证文件名清理
        clean_name = downloader.clean_filename("测试文件/名*.pdf")
        self.assertEqual(clean_name, "测试文件_名_.pdf")

class TestCninfoDownloaderMocked(unittest.TestCase):
    """使用Mock的CninfoDownloader测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_save_dir = self.test_env.create_temp_dir("test_downloads_")
        self.test_mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps({
                "000001": {"org_id": "9900000062", "name": "平安银行"}
            }, ensure_ascii=False, indent=2)
        )
        
        self.downloader = CninfoDownloader(
            save_dir=self.test_save_dir,
            mapping_file=self.test_mapping_file
        )
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    @patch('cninfo_activity_downloader.subprocess.run')
    def test_cleanup_chrome_processes_windows(self, mock_run):
        """测试Windows下清理Chrome进程"""
        with patch('cninfo_activity_downloader.platform.system', return_value="Windows"):
            self.downloader._cleanup_chrome_processes()
            
            # 验证调用了正确的命令
            self.assertEqual(mock_run.call_count, 2)
            calls = mock_run.call_args_list
            
            # 检查第一个调用（清理chrome.exe）
            self.assertIn('chrome.exe', calls[0][0][0])
            # 检查第二个调用（清理chromedriver.exe）
            self.assertIn('chromedriver.exe', calls[1][0][0])
    
    @patch('cninfo_activity_downloader.subprocess.run')
    def test_cleanup_chrome_processes_linux(self, mock_run):
        """测试Linux下清理Chrome进程"""
        with patch('cninfo_activity_downloader.platform.system', return_value="Linux"):
            self.downloader._cleanup_chrome_processes()
            
            # 验证调用了正确的命令
            self.assertEqual(mock_run.call_count, 2)
            calls = mock_run.call_args_list
            
            # 检查调用了pkill命令
            self.assertEqual(calls[0][0][0][0], 'pkill')
            self.assertEqual(calls[1][0][0][0], 'pkill')

if __name__ == "__main__":
    unittest.main() 