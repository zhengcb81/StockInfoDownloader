#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试下载功能 - 专门测试文件下载机制
"""

import os
import sys
import time
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def log(message):
    """简单的日志输出"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def test_download_mechanism():
    """测试下载机制"""
    log("开始测试下载机制...")
    
    # 测试Selenium策略
    log("\n=== 测试Selenium策略 ===")
    try:
        from src.web.selenium_strategy import SeleniumStrategy
        
        # 创建Selenium策略实例
        selenium_strategy = SeleniumStrategy(
            headless=True,
            download_dir="end2end_test/test_results"
        )
        
        # 创建浏览器
        selenium_strategy.create_driver()
        log("Selenium浏览器创建成功")
        
        # 测试导航到页面
        test_url = "https://www.cninfo.com.cn/new/disclosure/detail?plate=szse&orgId=9900056250&stockCode=301611&announcementId=1224316725&announcementTime=2025-07-28%2009:18"
        if selenium_strategy.navigate(test_url):
            log(f"成功导航到: {test_url}")
            
            # 获取页面标题
            title = selenium_strategy.get_page_title()
            log(f"页面标题: {title}")
            
            # 测试下载文件
            save_path = "end2end_test/test_results/珂玛科技/test_download.pdf"
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            success = selenium_strategy.download_file(test_url, save_path, timeout=30)
            if success:
                log(f"文件下载成功: {save_path}")
                # 检查文件大小
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    log(f"文件大小: {file_size} bytes")
                    if file_size > 10 * 1024:  # 大于10KB
                        log("✅ 文件大小正常")
                    else:
                        log("❌ 文件太小，可能下载失败")
                else:
                    log("❌ 文件不存在")
            else:
                log("❌ 文件下载失败")
        else:
            log("❌ 导航失败")
            
        selenium_strategy.close()
        
    except Exception as e:
        log(f"Selenium测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试Playwright策略
    log("\n=== 测试Playwright策略 ===")
    try:
        from src.web.playwright_strategy import PlaywrightStrategy
        
        # 创建Playwright策略实例
        playwright_strategy = PlaywrightStrategy(
            headless=True,
            download_dir="end2end_test/test_results"
        )
        
        # 创建浏览器
        playwright_strategy.create_driver()
        log("Playwright浏览器创建成功")
        
        # 测试导航到页面
        test_url = "https://www.cninfo.com.cn/new/disclosure/detail?plate=szse&orgId=9900056250&stockCode=301611&announcementId=1224316725&announcementTime=2025-07-28%2009:18"
        if playwright_strategy.navigate(test_url):
            log(f"成功导航到: {test_url}")
            
            # 获取页面标题
            title = playwright_strategy.get_page_title()
            log(f"页面标题: {title}")
            
            # 测试下载文件
            save_path = "end2end_test/test_results/珂玛科技/test_download_playwright.pdf"
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            success = playwright_strategy.download_file(test_url, save_path, timeout=30)
            if success:
                log(f"文件下载成功: {save_path}")
                # 检查文件大小
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    log(f"文件大小: {file_size} bytes")
                    if file_size > 10 * 1024:  # 大于10KB
                        log("✅ 文件大小正常")
                    else:
                        log("❌ 文件太小，可能下载失败")
                else:
                    log("❌ 文件不存在")
            else:
                log("❌ 文件下载失败")
        else:
            log("❌ 导航失败")
            
        playwright_strategy.close()
        
    except Exception as e:
        log(f"Playwright测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_download_mechanism()