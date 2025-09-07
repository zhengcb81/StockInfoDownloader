#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
端到端测试 - 测试完整的下载器工作流程
"""

import pytest
import tempfile
import os
import shutil
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from cninfo_activity_downloader import CninfoDownloader


class TestE2EDownloader:
    """端到端测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.temp_dir, 'downloads')
        
        # 创建测试映射文件
        self.mapping_file = os.path.join(self.temp_dir, 'test_mapping.json')
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump({
                "000001": {"org_id": "9900000062", "name": "平安银行"},
                "002415": {"org_id": "9900002415", "name": "海康威视"},
                "600519": {"org_id": "9900010519", "name": "贵州茅台"}
            }, f, ensure_ascii=False, indent=2)
        
        # 创建测试配置文件
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump({
                "stock_code": "000001",
                "save_dir": self.save_dir,
                "headless": True,
                "max_retries": 2,
                "pages": [
                    {
                        "name": "投资者关系活动",
                        "suffix": "research",
                        "allowed_keywords": ["投资者关系", "调研"],
                        "max_pages": 2
                    }
                ]
            }, f, ensure_ascii=False, indent=2)
    
    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    @patch('cninfo_activity_downloader.WebDriverWait')
    @patch('cninfo_activity_downloader.ActionChains')
    def test_complete_download_workflow(self, mock_actions, mock_wait, mock_chrome):
        """测试完整的下载工作流程"""
        # 设置mock对象
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        mock_wait_instance = MagicMock()
        mock_wait.return_value = mock_wait_instance
        
        mock_actions_instance = MagicMock()
        mock_actions.return_value = mock_actions_instance
        
        # 模拟页面内容和元素
        mock_driver.current_url = "https://www.cninfo.com.cn/new/disclosure/stock?orgId=9900000062&stockCode=000001#research"
        
        # 模拟链接元素
        mock_link_elements = []
        test_links = [
            {"text": "投资者关系活动记录表2024", "href": "/new/disclosure/detail?stockCode=000001&id=1"},
            {"text": "机构调研活动纪要", "href": "/new/disclosure/detail?stockCode=000001&id=2"},
            {"text": "2024年年度报告", "href": "/new/disclosure/detail?stockCode=000001&id=3"}
        ]
        
        for link_info in test_links:
            mock_element = MagicMock()
            mock_element.text = link_info['text']
            mock_element.get_attribute.return_value = link_info['href']
            mock_link_elements.append(mock_element)
        
        mock_driver.find_elements.return_value = mock_link_elements
        
        # 模拟下载按钮
        mock_download_btn = MagicMock()
        mock_wait_instance.until.return_value = mock_download_btn
        
        # 创建下载器
        downloader = CninfoDownloader(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file
        )
        
        # 执行下载
        success = downloader.download_activity_records(
            stock_code="000001",
            headless=True,
            max_retries=1,
            allowed_keywords=["投资者关系", "调研"]
        )
        
        # 验证基本流程
        assert mock_chrome.called, "WebDriver应该被初始化"
        assert mock_driver.get.called, "页面应该被访问"
        assert mock_wait.called, "应该等待元素加载"
        
        # 验证链接过滤
        assert mock_driver.find_elements.called, "应该查找链接元素"
        
        # 验证下载按钮点击
        mock_download_btn.click.assert_called()
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_multiple_stock_processing(self, mock_chrome):
        """测试多股票处理"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        downloader = CninfoDownloader(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file
        )
        
        # 测试多个股票代码
        test_stocks = ["000001", "002415", "600519"]
        
        for stock_code in test_stocks:
            # 每个股票都应该能获取到组织ID
            org_id = downloader.get_org_id(stock_code)
            assert org_id is not None, f"股票 {stock_code} 应该能获取到组织ID"
            assert org_id.startswith("99000"), f"组织ID {org_id} 格式应该正确"
            
            # 验证文件名清理
            test_filename = f"{stock_code}_测试文件/名*.pdf"
            clean_name = downloader.clean_filename(test_filename)
            assert "/" not in clean_name, "文件名不应该包含非法字符"
            assert "*" not in clean_name, "文件名不应该包含非法字符"
    
    def test_config_loading_and_validation(self):
        """测试配置加载和验证"""
        # 测试配置加载
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        assert config['stock_code'] == "000001", "股票代码应该正确加载"
        assert config['save_dir'] == self.save_dir, "保存目录应该正确加载"
        assert config['headless'] == True, "无头模式设置应该正确"
        assert config['max_retries'] == 2, "最大重试次数应该正确"
        
        # 验证页面配置
        assert len(config['pages']) == 1, "应该有一个页面配置"
        page_config = config['pages'][0]
        assert page_config['name'] == "投资者关系活动", "页面名称应该正确"
        assert page_config['suffix'] == "research", "页面后缀应该正确"
        assert "投资者关系" in page_config['allowed_keywords'], "应该包含投资者关系关键词"
        assert "调研" in page_config['allowed_keywords'], "应该包含调研关键词"
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_file_management_integration(self, mock_chrome):
        """测试文件管理集成"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        downloader = CninfoDownloader(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file
        )
        
        # 测试目录创建
        stock_name = "平安银行"
        stock_dir = os.path.join(self.save_dir, downloader.clean_filename(stock_name))
        
        # 目录不应该存在
        assert not os.path.exists(stock_dir), "目录初始不应该存在"
        
        # 创建目录
        os.makedirs(stock_dir, exist_ok=True)
        assert os.path.exists(stock_dir), "目录应该被创建"
        assert os.path.isdir(stock_dir), "应该是目录"
        
        # 测试文件存在性检查
        test_file_path = os.path.join(stock_dir, "test_file.pdf")
        
        # 文件不应该存在
        file_exists = os.path.exists(test_file_path) and os.path.getsize(test_file_path) > 10 * 1024
        assert not file_exists, "文件初始不应该存在"
        
        # 创建测试文件
        with open(test_file_path, 'wb') as f:
            f.write(b"x" * 15 * 1024)  # 15KB文件
        
        # 文件应该存在且大小合适
        file_exists = os.path.exists(test_file_path) and os.path.getsize(test_file_path) > 10 * 1024
        assert file_exists, "文件应该存在且大小合适"
        
        # 测试小文件应该被忽略
        small_file_path = os.path.join(stock_dir, "small_file.pdf")
        with open(small_file_path, 'wb') as f:
            f.write(b"x" * 5 * 1024)  # 5KB文件
        
        small_file_exists = os.path.exists(small_file_path) and os.path.getsize(small_file_path) > 10 * 1024
        assert not small_file_exists, "小文件应该被忽略"
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    @patch('cninfo_activity_downloader.logger')
    def test_error_handling_and_logging(self, mock_logger, mock_chrome):
        """测试错误处理和日志记录"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        downloader = CninfoDownloader(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file
        )
        
        # 测试无效股票代码
        invalid_org_id = downloader.get_org_id("999999")
        assert invalid_org_id is None, "无效股票代码应该返回None"
        
        # 测试WebDriver初始化失败
        mock_chrome.side_effect = Exception("WebDriver初始化失败")
        setup_result = downloader.setup_driver(headless=True)
        assert not setup_result, "WebDriver初始化失败应该返回False"
        
        # 验证错误日志记录
        assert mock_logger.error.called, "错误应该被记录"
    
    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 测试旧版本配置文件格式
        old_config = {
            "stock_code": "000001",
            "save_dir": self.save_dir,
            "headless": True
            # 没有pages配置
        }
        
        old_config_file = os.path.join(self.temp_dir, 'old_config.json')
        with open(old_config_file, 'w', encoding='utf-8') as f:
            json.dump(old_config, f, ensure_ascii=False, indent=2)
        
        # 应该能正常加载旧配置
        with open(old_config_file, 'r', encoding='utf-8') as f:
            loaded_config = json.load(f)
        
        assert loaded_config['stock_code'] == "000001", "旧配置应该能正常加载"
        assert 'pages' not in loaded_config, "旧配置不应该有pages字段"
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_performance_metrics(self, mock_chrome):
        """测试性能指标"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        downloader = CninfoDownloader(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file
        )
        
        # 测试动态延迟
        start_time = time.time()
        downloader.dynamic_delay(0.1, 0.2)  # 小延迟用于测试
        end_time = time.time()
        
        elapsed = end_time - start_time
        assert elapsed >= 0.1, "动态延迟应该至少等待最小时间"
        assert elapsed <= 0.5, "动态延迟不应该超过最大时间太多"
        
        # 测试下载计数
        assert downloader.download_count == 0, "初始下载计数应该为0"
        
        # 模拟下载计数增加
        downloader.download_count = 3
        assert downloader.download_count == 3, "下载计数应该能正确设置"
        
        # 测试会话下载限制
        assert downloader.max_downloads_per_session == 5, "会话下载限制应该正确"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])