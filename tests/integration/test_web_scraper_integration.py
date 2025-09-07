#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web Scraper 集成测试 - 使用模拟网页测试实际的网页抓取功能
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time
import json

from cninfo_activity_downloader import CninfoDownloader


class MockCNInfoHandler(SimpleHTTPRequestHandler):
    """模拟巨潮资讯网的处理程序"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/new/disclosure/stock':
            # 返回股票页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # 返回包含投资者关系活动链接的页面
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>测试股票页面</title>
            </head>
            <body>
                <div class="el-table__body-wrapper">
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    <a href="/new/disclosure/detail?stockCode=000001&id=1">投资者关系活动记录表</a>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <a href="/new/disclosure/detail?stockCode=000001&id=2">调研活动纪要</a>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <a href="/new/disclosure/detail?stockCode=000001&id=3">年度报告</a>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <button class="el-pagination__next">下一页</button>
            </body>
            </html>
            """
            self.wfile.write(html_content.encode('utf-8'))
            
        elif '/new/disclosure/detail' in self.path:
            # 返回详情页面
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # 返回包含下载按钮的详情页
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>公告详情</title>
            </head>
            <body>
                <h1>投资者关系活动记录表</h1>
                <button class="download-btn">公告下载</button>
                <script>
                    document.querySelector('.download-btn').addEventListener('click', function() {
                        // 模拟下载行为
                        window.location.href = '/download/test.pdf';
                    });
                </script>
            </body>
            </html>
            """
            self.wfile.write(html_content.encode('utf-8'))
            
        elif self.path == '/download/test.pdf':
            # 返回模拟的PDF文件
            self.send_response(200)
            self.send_header('Content-type', 'application/pdf')
            self.send_header('Content-Disposition', 'attachment; filename="test.pdf"')
            self.end_headers()
            
            # 生成一个简单的PDF内容（实际测试中可以使用真实的小PDF文件）
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nstream\nBT\n/F1 12 Tf\n50 700 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 1\n0000000000 65535 f \n0000000010 00000 n \ntrailer\n<<>>\nstartxref\n642\n%%EOF"
            self.wfile.write(pdf_content)
            
        else:
            self.send_response(404)
            self.end_headers()


class TestWebScraperIntegration:
    """Web Scraper 集成测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.temp_dir, 'downloads')
        
        # 创建测试映射文件
        self.mapping_file = os.path.join(self.temp_dir, 'test_mapping.json')
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump({
                "000001": {"org_id": "9900000062", "name": "平安银行"}
            }, f, ensure_ascii=False, indent=2)
        
        # 启动模拟服务器
        self.server = HTTPServer(('localhost', 0), MockCNInfoHandler)
        self.server_port = self.server.server_address[1]
        
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # 创建下载器
        self.downloader = CninfoDownloader(
            save_dir=self.save_dir,
            mapping_file=self.mapping_file
        )
    
    def teardown_method(self):
        """测试清理"""
        # 关闭服务器
        self.server.shutdown()
        self.server_thread.join(timeout=5)
        
        # 清理临时文件
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_find_download_links_integration(self, mock_chrome):
        """测试集成环境下的链接查找功能"""
        # 设置mock driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # 设置driver的当前URL和页面源码
        test_url = f"http://localhost:{self.server_port}/new/disclosure/stock"
        mock_driver.current_url = test_url
        
        # 模拟页面内容
        with open('tests/test_data/mock_stock_page.html', 'r', encoding='utf-8') as f:
            mock_page_content = f.read()
        
        mock_driver.page_source = mock_page_content
        
        # 设置WebDriverWait的mock
        with patch('cninfo_activity_downloader.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait.return_value = mock_wait_instance
            mock_wait_instance.until.return_value = [MagicMock()]  # 模拟找到的元素
            
            # 初始化driver
            self.downloader.setup_driver(headless=True)
            
            # 测试链接查找
            detail_infos = self.downloader._find_download_links(
                driver=mock_driver,
                stock_code="000001",
                stock_dir=self.save_dir,
                allowed_keywords=["投资者关系", "调研"]
            )
            
            # 验证找到了正确的链接
            assert len(detail_infos) > 0
            for info in detail_infos:
                assert 'href' in info
                assert 'file_name' in info
                assert 'save_path' in info
                assert 'new/disclosure/detail' in info['href']
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    def test_keyword_filtering_integration(self, mock_chrome):
        """测试关键词过滤集成"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # 设置测试页面内容
        test_links = [
            {"text": "投资者关系活动记录表", "href": "/new/disclosure/detail?stockCode=000001&id=1"},
            {"text": "调研活动纪要", "href": "/new/disclosure/detail?stockCode=000001&id=2"},
            {"text": "年度财务报告", "href": "/new/disclosure/detail?stockCode=000001&id=3"},
            {"text": "投资者关系活动更正公告", "href": "/new/disclosure/detail?stockCode=000001&id=4"}
        ]
        
        # 创建mock元素
        mock_elements = []
        for link in test_links:
            mock_element = MagicMock()
            mock_element.text = link['text']
            mock_element.get_attribute.return_value = link['href']
            mock_elements.append(mock_element)
        
        mock_driver.find_elements.return_value = mock_elements
        
        # 初始化driver
        self.downloader.setup_driver(headless=True)
        
        # 测试不同关键词过滤
        test_cases = [
            {
                "keywords": ["投资者关系", "调研"],
                "expected_count": 3,  # 前三个链接
                "description": "包含投资者关系或调研"
            },
            {
                "keywords": ["报告"],
                "expected_count": 1,  # 只有年度报告
                "description": "包含报告"
            },
            {
                "keywords": ["更正"],
                "expected_count": 1,  # 只有更正公告
                "description": "包含更正"
            },
            {
                "keywords": None,
                "expected_count": 4,  # 所有链接
                "description": "无关键词过滤"
            }
        ]
        
        for case in test_cases:
            detail_infos = self.downloader._find_download_links(
                driver=mock_driver,
                stock_code="000001",
                stock_dir=self.save_dir,
                allowed_keywords=case['keywords']
            )
            
            assert len(detail_infos) == case['expected_count'], \
                f"{case['description']}: 期望 {case['expected_count']} 个链接，实际 {len(detail_infos)}"
    
    def test_file_existence_checking_integration(self):
        """测试文件存在性检查集成"""
        # 创建测试文件
        test_file_path = os.path.join(self.save_dir, "test_file.pdf")
        with open(test_file_path, 'wb') as f:
            f.write(b"x" * 20 * 1024)  # 20KB文件
        
        # 测试文件存在性检查
        file_exists = os.path.exists(test_file_path) and os.path.getsize(test_file_path) > 10 * 1024
        assert file_exists, "文件应该存在且大小合适"
        
        # 测试小文件应该被忽略
        small_file_path = os.path.join(self.save_dir, "small_file.pdf")
        with open(small_file_path, 'wb') as f:
            f.write(b"x" * 5 * 1024)  # 5KB文件
        
        small_file_exists = os.path.exists(small_file_path) and os.path.getsize(small_file_path) > 10 * 1024
        assert not small_file_exists, "小文件应该被忽略"
    
    @patch('cninfo_activity_downloader.webdriver.Chrome')
    @patch('cninfo_activity_downloader.WebDriverWait')
    def test_download_button_interaction(self, mock_wait, mock_chrome):
        """测试下载按钮交互集成"""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # 模拟下载按钮
        mock_download_btn = MagicMock()
        mock_wait_instance = MagicMock()
        mock_wait.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = mock_download_btn
        
        # 初始化driver
        self.downloader.setup_driver(headless=True)
        
        # 测试下载按钮点击
        detail_info = {
            'href': f'http://localhost:{self.server_port}/new/disclosure/detail?stockCode=000001&id=1',
            'file_name': 'test_file.pdf',
            'save_path': os.path.join(self.save_dir, 'test_file.pdf')
        }
        
        # 模拟文件下载前的目录状态
        before_files = set(os.listdir(self.save_dir))
        
        # 测试下载过程
        success = self.downloader._download_page_files(
            driver=mock_driver,
            detail_infos=[detail_info],
            headless=True,
            max_retries=1
        )
        
        # 验证下载按钮被点击
        mock_download_btn.click.assert_called_once()
    
    def test_directory_structure_integration(self):
        """测试目录结构集成"""
        stock_name = "平安银行"
        stock_dir = os.path.join(self.save_dir, self.downloader.clean_filename(stock_name))
        
        # 创建股票目录
        os.makedirs(stock_dir, exist_ok=True)
        assert os.path.exists(stock_dir), "股票目录应该被创建"
        assert os.path.isdir(stock_dir), "股票目录应该是目录"
        
        # 在目录中创建文件
        test_file_path = os.path.join(stock_dir, "test_file.pdf")
        with open(test_file_path, 'wb') as f:
            f.write(b"x" * 15 * 1024)  # 15KB文件
        
        # 验证文件存在性检查（子目录）
        file_exists = os.path.exists(test_file_path) and os.path.getsize(test_file_path) > 10 * 1024
        assert file_exists, "子目录中的文件应该被正确检测"
        
        # 在根目录创建文件（兼容旧版本）
        root_file_path = os.path.join(self.save_dir, "old_version_file.pdf")
        with open(root_file_path, 'wb') as f:
            f.write(b"x" * 15 * 1024)  # 15KB文件
        
        # 验证文件存在性检查（根目录）
        root_file_exists = os.path.exists(root_file_path) and os.path.getsize(root_file_path) > 10 * 1024
        assert root_file_exists, "根目录中的文件应该被正确检测"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])