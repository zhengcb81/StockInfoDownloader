#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试配置文件

包含测试用的常量、配置和工具函数
"""

import os
import tempfile
import shutil
from pathlib import Path

# 测试用股票代码
TEST_STOCK_CODES = [
    "000001",  # 平安银行
    "000002",  # 万科A
    "002415",  # 海康威视
    "600036",  # 招商银行
    "600519",  # 贵州茅台
]

# 测试用组织ID（使用真实数据）
TEST_ORG_IDS = {
    "000001": "9900000001",  # 平安银行
    "000002": "9900000002",  # 万科A
    "002415": "9900012688",  # 海康威视（真实爬取的ID）
    "600036": "9900010036",  # 招商银行
    "600519": "9900010519",  # 贵州茅台
}

# 测试用URL
TEST_URLS = {
    "cninfo_base": "https://www.cninfo.com.cn",
    "detail_page": "https://www.cninfo.com.cn/new/disclosure/detail",
    "stock_page": "https://www.cninfo.com.cn/new/disclosure/stock",
}

# 测试文件路径
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DOWNLOADS_DIR = Path(__file__).parent / "test_downloads"
TEST_LOGS_DIR = Path(__file__).parent / "test_logs"

# 测试超时设置
TIMEOUTS = {
    "short": 5,      # 短超时（秒）
    "medium": 15,    # 中等超时（秒）
    "long": 60,      # 长超时（秒）
    "download": 120, # 下载超时（秒）
}

# WebDriver测试配置
WEBDRIVER_CONFIG = {
    "headless": True,
    "window_size": "1920,1080",
    "page_load_timeout": 30,
    "implicit_wait": 10,
}

class TestEnvironment:
    """测试环境管理器"""
    
    def __init__(self):
        self.temp_dirs = []
        self.temp_files = []
    
    def create_temp_dir(self, prefix="test_"):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_temp_file(self, suffix=".tmp", content=""):
        """创建临时文件"""
        fd, temp_file = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        
        if content:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        self.temp_files.append(temp_file)
        return temp_file
    
    def cleanup(self):
        """清理临时文件和目录"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception:
                pass
        
        self.temp_dirs.clear()
        self.temp_files.clear()

def create_test_config(stock_code="000001", save_dir=None):
    """创建测试用配置"""
    if save_dir is None:
        save_dir = tempfile.mkdtemp(prefix="test_downloads_")
    
    return {
        "stock_code": stock_code,
        "save_dir": save_dir,
        "headless": True,
        "max_retries": 2,
        "timeout": TIMEOUTS["medium"]
    }

def create_test_mapping():
    """创建测试用股票映射"""
    return {
        code: {
            "orgId": org_id,
            "name": f"测试股票{code}",
            "market": "深圳" if code.startswith(("000", "002")) else "上海"
        }
        for code, org_id in TEST_ORG_IDS.items()
    } 